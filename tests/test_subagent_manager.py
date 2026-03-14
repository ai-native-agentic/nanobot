"""Tests for SubagentManager."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from nanobot.agent.subagent import SubagentManager
from nanobot.bus.queue import MessageBus


class TestSubagentManager:
    """Test SubagentManager functionality."""

    @pytest.fixture
    def mock_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.get_default_model = MagicMock(return_value="test-model")
        return provider

    @pytest.fixture
    def mock_bus(self):
        """Create a mock message bus."""
        bus = MagicMock(spec=MessageBus)
        bus.publish_inbound = AsyncMock()
        return bus

    @pytest.fixture
    def subagent_manager(self, mock_provider, mock_bus, tmp_path):
        """Create a SubagentManager instance."""
        return SubagentManager(
            provider=mock_provider,
            workspace=tmp_path,
            bus=mock_bus,
            model="test-model",
        )

    def test_init(self, subagent_manager):
        """Test SubagentManager initialization."""
        assert subagent_manager.model == "test-model"
        assert subagent_manager.temperature == 0.7
        assert subagent_manager.max_tokens == 4096
        assert subagent_manager.get_running_count() == 0

    def test_get_running_count_empty(self, subagent_manager):
        """Test running count with no tasks."""
        assert subagent_manager.get_running_count() == 0

    @pytest.mark.asyncio
    async def test_cancel_by_session_no_tasks(self, subagent_manager):
        """Test cancel_by_session with no running tasks."""
        cancelled = await subagent_manager.cancel_by_session("test_session")
        assert cancelled == 0

    @pytest.mark.asyncio
    async def test_cancel_by_session_with_tasks(self, subagent_manager):
        """Test cancel_by_session with running tasks."""
        session_key = "test_session"

        async def dummy_task():
            await asyncio.sleep(10)

        task_id = "test123"
        task = asyncio.create_task(dummy_task())
        subagent_manager._running_tasks[task_id] = task
        subagent_manager._session_tasks[session_key] = {task_id}

        assert subagent_manager.get_running_count() == 1

        cancelled = await subagent_manager.cancel_by_session(session_key)

        assert cancelled == 1
        assert task.done()
        # Note: cleanup callback runs after task is done, removing from _running_tasks
        # Give callback time to run
        await asyncio.sleep(0.01)
        assert task_id not in subagent_manager._running_tasks

    @pytest.mark.asyncio
    async def test_cancel_by_session_multiple_sessions(self, subagent_manager):
        """Test cancel_by_session only cancels tasks for specified session."""
        session1 = "session1"
        session2 = "session2"

        async def dummy_task():
            await asyncio.sleep(10)

        task1_id = "task1"
        task2_id = "task2"

        task1 = asyncio.create_task(dummy_task())
        task2 = asyncio.create_task(dummy_task())

        subagent_manager._running_tasks[task1_id] = task1
        subagent_manager._running_tasks[task2_id] = task2
        subagent_manager._session_tasks[session1] = {task1_id}
        subagent_manager._session_tasks[session2] = {task2_id}

        cancelled = await subagent_manager.cancel_by_session(session1)

        assert cancelled == 1
        assert task1.done()
        # task2 should still be running
        assert not task2.done()

        # Cleanup callback removes task1 from _running_tasks
        await asyncio.sleep(0.01)
        assert task1_id not in subagent_manager._running_tasks
        assert task2_id in subagent_manager._running_tasks

        task2.cancel()

    @pytest.mark.asyncio
    async def test_cancel_by_session_done_task(self, subagent_manager):
        """Test cancel_by_session skips already done tasks."""
        session_key = "test_session"

        async def quick_task():
            return "done"

        task_id = "done_task"
        task = asyncio.create_task(quick_task())
        await task

        subagent_manager._running_tasks[task_id] = task
        subagent_manager._session_tasks[session_key] = {task_id}

        cancelled = await subagent_manager.cancel_by_session(session_key)

        assert cancelled == 0
