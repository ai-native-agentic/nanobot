"""Tests for SessionManager - JSONL persistence and session management."""

import json
from datetime import datetime

import pytest

from nanobot.session.manager import Session, SessionManager


class TestSession:
    """Test Session class functionality."""

    def test_session_init(self):
        """Test Session initialization."""
        session = Session(key="test:123")
        assert session.key == "test:123"
        assert session.messages == []
        assert session.last_consolidated == 0
        assert isinstance(session.created_at, datetime)

    def test_add_message(self):
        """Test adding messages to session."""
        session = Session(key="test:123")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")

        assert len(session.messages) == 2
        assert session.messages[0]["role"] == "user"
        assert session.messages[0]["content"] == "Hello"
        assert "timestamp" in session.messages[0]

    def test_add_message_with_kwargs(self):
        """Test adding messages with extra fields."""
        session = Session(key="test:123")
        session.add_message(
            "assistant",
            None,
            tool_calls=[{"id": "call_1", "function": {"name": "test"}}]
        )

        assert len(session.messages) == 1
        assert session.messages[0]["tool_calls"] == [{"id": "call_1", "function": {"name": "test"}}]

    def test_get_history(self):
        """Test getting session history."""
        session = Session(key="test:123")
        for i in range(10):
            session.add_message("user", f"User message {i}")
            session.add_message("assistant", f"Assistant message {i}")

        history = session.get_history(max_messages=6)
        assert len(history) <= 6
        # Should start with a user message
        assert history[0]["role"] == "user"

    def test_get_history_respects_consolidation(self):
        """Test that get_history respects last_consolidated."""
        session = Session(key="test:123", last_consolidated=4)
        for i in range(6):
            session.add_message("user", f"User {i}")
            session.add_message("assistant", f"Assistant {i}")

        history = session.get_history(max_messages=100)
        # Should only return messages after last_consolidated (index 4 onwards)
        # Messages 4,5,6,7,8,9 = 6 pairs = 12 messages total, minus 4 = 8 messages
        assert len(history) == 8  # 8 messages after index 4

    def test_clear(self):
        """Test clearing session."""
        session = Session(key="test:123")
        session.add_message("user", "Hello")
        session.last_consolidated = 5

        session.clear()

        assert len(session.messages) == 0
        assert session.last_consolidated == 0


class TestSessionManager:
    """Test SessionManager functionality."""

    @pytest.fixture
    def session_manager(self, tmp_path):
        """Create a SessionManager with temp directory."""
        return SessionManager(workspace=tmp_path)

    def test_init_creates_sessions_dir(self, tmp_path):
        """Test that SessionManager creates sessions directory."""
        manager = SessionManager(workspace=tmp_path)
        assert manager.sessions_dir.exists()
        assert manager.sessions_dir.is_dir()

    def test_get_or_create_new_session(self, session_manager):
        """Test creating a new session."""
        session = session_manager.get_or_create("telegram:12345")
        assert session.key == "telegram:12345"
        assert len(session.messages) == 0

    def test_get_or_create_cached(self, session_manager):
        """Test that sessions are cached."""
        session1 = session_manager.get_or_create("telegram:12345")
        session2 = session_manager.get_or_create("telegram:12345")
        assert session1 is session2

    def test_save_and_load(self, session_manager):
        """Test saving and loading a session."""
        session = session_manager.get_or_create("telegram:12345")
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi!")
        session.metadata = {"test": "value"}
        session_manager.save(session)

        # Load in new manager
        manager2 = SessionManager(workspace=session_manager.workspace)
        loaded = manager2.get_or_create("telegram:12345")

        assert len(loaded.messages) == 2
        assert loaded.messages[0]["content"] == "Hello"
        assert loaded.metadata == {"test": "value"}

    def test_save_creates_jsonl_file(self, session_manager):
        """Test that save creates a valid JSONL file."""
        session = session_manager.get_or_create("telegram:12345")
        session.add_message("user", "Test")
        session_manager.save(session)

        path = session_manager._get_session_path("telegram:12345")
        assert path.exists()

        # Verify JSONL format
        with open(path) as f:
            lines = f.readlines()

        assert len(lines) == 2  # metadata + 1 message
        # First line should be metadata
        metadata = json.loads(lines[0])
        assert metadata["_type"] == "metadata"
        assert metadata["key"] == "telegram:12345"

    def test_list_sessions(self, session_manager):
        """Test listing sessions."""
        # Create multiple sessions
        for i in range(3):
            session = session_manager.get_or_create(f"telegram:{i}")
            session.add_message("user", f"Message {i}")
            session_manager.save(session)

        sessions = session_manager.list_sessions()
        assert len(sessions) == 3

        # Should be sorted by updated_at (descending)
        for session in sessions:
            assert "key" in session
            assert "created_at" in session
            assert "updated_at" in session
            assert "path" in session

    def test_invalidate_cache(self, session_manager):
        """Test invalidating session cache."""
        session = session_manager.get_or_create("telegram:12345")
        session.add_message("user", "Test")
        session_manager.save(session)  # Save to disk first
        session_manager.invalidate("telegram:12345")

        # Should create new session from disk
        session2 = session_manager.get_or_create("telegram:12345")
        assert session is not session2
        assert len(session2.messages) == 1  # Loaded from disk

    def test_special_characters_in_key(self, session_manager):
        """Test session keys with special characters."""
        session = session_manager.get_or_create("discord:123456789012345678@1234567890123456789")
        session.add_message("user", "Test")
        session_manager.save(session)

        # Should load correctly
        loaded = session_manager.get_or_create("discord:123456789012345678@1234567890123456789")
        assert len(loaded.messages) == 1

    def test_empty_session_save_load(self, session_manager):
        """Test saving and loading empty session."""
        session = session_manager.get_or_create("telegram:empty")
        session_manager.save(session)

        loaded = session_manager.get_or_create("telegram:empty")
        assert len(loaded.messages) == 0


class TestSessionManagerIntegration:
    """Integration tests for SessionManager."""

    def test_full_workflow(self, tmp_path):
        """Test complete session workflow."""
        manager = SessionManager(workspace=tmp_path)

        # Create session
        session = manager.get_or_create("telegram:999")
        session.add_message("user", "What's the weather?")
        session.add_message(
            "assistant",
            None,
            tool_calls=[{"id": "call_1", "function": {"name": "get_weather", "arguments": "{}"}}]
        )
        session.add_message("tool", "25°C and sunny", tool_call_id="call_1")
        session.add_message("assistant", "It's 25°C and sunny!")
        manager.save(session)

        # Simulate consolidation
        session.last_consolidated = 4
        session.add_message("user", "Thanks!")
        manager.save(session)

        # Load and verify
        loaded = manager.get_or_create("telegram:999")
        assert len(loaded.messages) == 5
        assert loaded.last_consolidated == 4

        # get_history should only return unconsolidated messages
        history = loaded.get_history(max_messages=100)
        assert len(history) == 1  # Only "Thanks!" message

    def test_multiple_sessions_isolation(self, tmp_path):
        """Test that sessions are properly isolated."""
        manager = SessionManager(workspace=tmp_path)

        session1 = manager.get_or_create("telegram:user1")
        session1.add_message("user", "User 1 message")
        manager.save(session1)

        session2 = manager.get_or_create("telegram:user2")
        session2.add_message("user", "User 2 message")
        manager.save(session2)

        # Reload session1 - should not have session2's messages
        reloaded1 = manager.get_or_create("telegram:user1")
        assert len(reloaded1.messages) == 1
        assert reloaded1.messages[0]["content"] == "User 1 message"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
