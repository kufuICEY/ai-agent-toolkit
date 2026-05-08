"""Conversation memory management with sliding window support."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field


@dataclass
class MemoryEntry:
    role: str
    content: str
    metadata: dict = field(default_factory=dict)


class ConversationMemory:
    """Manages conversation history with configurable window size."""

    def __init__(self, max_entries: int = 50, max_tokens: int | None = None):
        self.max_entries = max_entries
        self.max_tokens = max_tokens
        self._history: deque[MemoryEntry] = deque(maxlen=max_entries)

    def add(self, role: str, content: str, **metadata) -> None:
        self._history.append(MemoryEntry(role=role, content=content, metadata=metadata))

    def get_messages(self) -> list[dict]:
        """Return history as a list of message dicts for LLM API."""
        return [{"role": e.role, "content": e.content} for e in self._history]

    def get_context_window(self) -> list[dict]:
        """Return messages within the configured window."""
        messages = self.get_messages()
        if self.max_tokens is None:
            return messages

        # Rough token estimation: ~1.5 tokens per character for English/Chinese mix
        total_chars = 0
        result = []
        for msg in reversed(messages):
            msg_chars = len(msg["content"])
            if total_chars + msg_chars > self.max_tokens * 1.5:
                break
            result.insert(0, msg)
            total_chars += msg_chars

        return result

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """Add a tool execution result as a system message."""
        self.add("system", f"[Tool: {tool_name}] {result}")

    def clear(self) -> None:
        self._history.clear()

    @property
    def entry_count(self) -> int:
        return len(self._history)

    def summary(self) -> str:
        """Return a brief summary of conversation state."""
        if not self._history:
            return "Empty conversation"
        user_msgs = sum(1 for e in self._history if e.role == "user")
        assist_msgs = sum(1 for e in self._history if e.role == "assistant")
        tool_msgs = sum(1 for e in self._history if e.role == "system" and "Tool:" in e.content)
        return f"{self.entry_count} entries ({user_msgs} user, {assist_msgs} assistant, {tool_msgs} tool calls)"
