"""Tests for AgentLoop helper methods."""

import pytest
from nanobot.agent.loop import AgentLoop


class TestAgentLoopHelpers:
    """Test helper methods in AgentLoop."""

    def test_strip_think_removes_blocks(self):
        """Test that <think>...</think> blocks are removed."""
        text = "Some text <think>thinking here</think> more text"
        result = AgentLoop._strip_think(text)
        # Note: leaves double space, which is fine
        assert "thinking" not in result
        assert "Some text" in result
        assert "more text" in result

    def test_strip_think_removes_multiline(self):
        """Test multiline thinking blocks are removed."""
        text = "Start <think>\nline1\nline2\n</think> end"
        result = AgentLoop._strip_think(text)
        assert "line1" not in result
        assert "Start" in result
        assert "end" in result

    def test_strip_think_empty_input(self):
        """Test None and empty string inputs."""
        assert AgentLoop._strip_think(None) is None
        assert AgentLoop._strip_think("") is None  # Empty string returns None after strip

    def test_strip_think_only_think(self):
        """Test when only thinking block exists."""
        text = "<think>just thinking</think>"
        result = AgentLoop._strip_think(text)
        assert result is None

    def test_tool_hint_single_call(self):
        """Test tool hint with single tool call."""
        tool_calls = [
            type("obj", (object,), {"name": "web_search", "arguments": {"query": "hot deals"}})
        ]
        result = AgentLoop._tool_hint(tool_calls)
        assert "web_search" in result
        assert "hot deals" in result

    def test_tool_hint_multiple_calls(self):
        """Test tool hint with multiple tool calls."""
        tool_calls = [
            type("obj", (object,), {"name": "read_file", "arguments": {"path": "test.md"}}),
            type("obj", (object,), {"name": "exec", "arguments": {"command": "ls"}}),
        ]
        result = AgentLoop._tool_hint(tool_calls)
        assert "read_file" in result
        assert "exec" in result

    def test_tool_hint_long_value_truncated(self):
        """Test that long values are truncated in hint."""
        long_query = "a" * 100
        tool_calls = [
            type("obj", (object,), {"name": "web_search", "arguments": {"query": long_query}})
        ]
        result = AgentLoop._tool_hint(tool_calls)
        assert "…" in result or len(result) < 50
