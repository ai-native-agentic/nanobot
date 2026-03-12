"""SeedbotChannel — subprocess stdin/stdout bridge to seedbot."""

from __future__ import annotations

import asyncio

from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import SeedbotConfig

RESPONSE_END_MARKER = "<<<SEEDBOT_DONE>>>"


class SeedbotChannel(BaseChannel):
    """
    Bridge channel that spawns a seedbot subprocess and communicates
    via stdin (outbound) and stdout (inbound).

    Seedbot writes lines to stdout. A complete response is terminated
    by a line containing only ``<<<SEEDBOT_DONE>>>``.
    """

    name = "seedbot"

    def __init__(self, config: SeedbotConfig, bus: MessageBus) -> None:
        super().__init__(config, bus)
        self.config: SeedbotConfig = config
        self._process: asyncio.subprocess.Process | None = None
        self._read_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Spawn the seedbot subprocess and begin reading stdout."""
        self._process = await asyncio.create_subprocess_exec(
            "bash",
            self.config.script_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=self.config.working_dir or None,
        )
        self._running = True
        self._read_task = asyncio.create_task(self._read_loop())
        logger.info("SeedbotChannel started (pid={})", self._process.pid)

    async def stop(self) -> None:
        """Terminate the subprocess and cancel the reader task."""
        self._running = False
        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass
        if self._process:
            self._process.terminate()
            try:
                await asyncio.wait_for(self._process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self._process.kill()
        logger.info("SeedbotChannel stopped")

    # ------------------------------------------------------------------
    # Outbound  (nanobot → seedbot subprocess)
    # ------------------------------------------------------------------

    async def send(self, msg: OutboundMessage) -> None:
        """Write the outbound message content to the subprocess stdin."""
        if not self._process or not self._process.stdin:
            logger.warning("SeedbotChannel: process not running, cannot send")
            return
        payload = (msg.content + "\n").encode()
        self._process.stdin.write(payload)
        await self._process.stdin.drain()

    # ------------------------------------------------------------------
    # Inbound  (seedbot subprocess → nanobot)
    # ------------------------------------------------------------------

    async def _read_loop(self) -> None:
        """Read lines from subprocess stdout, delimited by RESPONSE_END_MARKER."""
        assert self._process and self._process.stdout
        buffer: list[str] = []
        try:
            async for raw_line in self._process.stdout:
                text = raw_line.decode().rstrip("\n")
                if text == RESPONSE_END_MARKER:
                    if buffer:
                        await self._handle_message(
                            sender_id="seedbot",
                            chat_id="seedbot",
                            content="\n".join(buffer),
                        )
                        buffer = []
                else:
                    buffer.append(text)
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("SeedbotChannel reader crashed: {}", exc)
