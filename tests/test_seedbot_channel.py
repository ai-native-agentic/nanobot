"""Unit tests for SeedbotChannel."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nanobot.channels.seedbot import RESPONSE_END_MARKER, SeedbotChannel
from nanobot.config.schema import SeedbotConfig


@pytest.fixture
def config():
    return SeedbotConfig(
        enabled=True,
        script_path="/fake/main.sh",
        working_dir="",
        allow_from=["*"],
    )


@pytest.fixture
def bus():
    b = MagicMock()
    b.publish_inbound = AsyncMock()
    return b


@pytest.fixture
def channel(config, bus):
    return SeedbotChannel(config, bus)


@pytest.mark.asyncio
async def test_send_writes_to_stdin(channel):
    """send() writes message content + newline to subprocess stdin."""
    mock_process = MagicMock()
    mock_process.stdin = MagicMock()
    mock_process.stdin.drain = AsyncMock()
    mock_process.pid = 12345
    channel._process = mock_process

    msg = MagicMock()
    msg.content = "hello seedbot"
    await channel.send(msg)

    mock_process.stdin.write.assert_called_once()
    written = mock_process.stdin.write.call_args[0][0]
    assert b"hello seedbot\n" == written


@pytest.mark.asyncio
async def test_send_noop_when_no_process(channel):
    """send() is a no-op when the subprocess is not running."""
    channel._process = None
    msg = MagicMock()
    msg.content = "hello"
    await channel.send(msg)  # should not raise


@pytest.mark.asyncio
async def test_stop_terminates_process(channel):
    """stop() terminates the subprocess and waits for exit."""
    mock_process = MagicMock()
    mock_process.terminate = MagicMock()
    mock_process.kill = MagicMock()
    mock_process.wait = AsyncMock(return_value=0)
    channel._process = mock_process
    channel._read_task = None

    await channel.stop()
    mock_process.terminate.assert_called_once()


@pytest.mark.asyncio
async def test_stop_kills_on_timeout(channel):
    """stop() force-kills the process if it doesn't exit within 5 seconds."""
    mock_process = MagicMock()
    mock_process.terminate = MagicMock()
    mock_process.kill = MagicMock()
    mock_process.wait = AsyncMock(side_effect=asyncio.TimeoutError)
    channel._process = mock_process
    channel._read_task = None

    await channel.stop()
    mock_process.terminate.assert_called_once()
    mock_process.kill.assert_called_once()


def test_response_end_marker():
    """Ensure the marker constant is the expected value."""
    assert RESPONSE_END_MARKER == "<<<SEEDBOT_DONE>>>"


def test_channel_name(channel):
    """Channel name is 'seedbot'."""
    assert channel.name == "seedbot"


def test_seedbot_config_defaults():
    """SeedbotConfig has sane defaults."""
    cfg = SeedbotConfig()
    assert cfg.enabled is False
    assert cfg.script_path == ""
    assert cfg.working_dir == ""
    assert cfg.allow_from == []
