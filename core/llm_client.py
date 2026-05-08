"""Unified LLM API client supporting OpenAI, Claude, and custom endpoints."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Protocol


class LLMProvider(Protocol):
    """Interface for LLM providers."""

    def chat(self, messages: list[dict], **kwargs) -> str:
        ...


@dataclass
class Message:
    role: str
    content: str


@dataclass
class LLMConfig:
    provider: str = "openai"
    api_key: str = ""
    model: str = "gpt-4o"
    base_url: str = "https://api.openai.com/v1"
    temperature: float = 0.3
    max_tokens: int = 4096


class LLMClient:
    """Unified client for multiple LLM providers."""

    def __init__(self, config: LLMConfig | None = None):
        self.config = config or LLMConfig()
        self._messages: list[Message] = []

    def add_message(self, role: str, content: str) -> None:
        self._messages.append(Message(role=role, content=content))

    def clear_messages(self) -> None:
        self._messages.clear()

    def chat(self, prompt: str, system_prompt: str | None = None) -> str:
        """Send a chat completion request."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.extend({"role": m.role, "content": m.content} for m in self._messages)
        messages.append({"role": "user", "content": prompt})

        self.add_message("user", prompt)

        response = self._call_api(messages)
        self.add_message("assistant", response)

        return response

    def chat_with_tools(self, prompt: str, tools: list[dict],
                        system_prompt: str | None = None) -> tuple[str, list[dict]]:
        """Send a chat completion request with tool definitions. Returns response and tool calls."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.extend({"role": m.role, "content": m.content} for m in self._messages)
        messages.append({"role": "user", "content": prompt})

        response_text, tool_calls = self._call_api_with_tools(messages, tools)

        self.add_message("user", prompt)
        if response_text:
            self.add_message("assistant", response_text)

        return response_text, tool_calls

    def _call_api(self, messages: list[dict]) -> str:
        """Call the LLM API and return the response text."""
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("Please install openai: pip install openai")

        client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        return response.choices[0].message.content or ""

    def _call_api_with_tools(self, messages: list[dict], tools: list[dict]) -> tuple[str, list[dict]]:
        """Call the LLM API with tool definitions."""
        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("Please install openai: pip install openai")

        client = OpenAI(
            api_key=self.config.api_key,
            base_url=self.config.base_url,
        )

        # Convert tools to OpenAI format
        openai_tools = []
        for tool in tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("parameters", {"type": "object", "properties": {}}),
                },
            })

        response = client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            tools=openai_tools if openai_tools else None,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        choice = response.choices[0]
        text = choice.message.content or ""
        tool_calls_raw = choice.message.tool_calls or []

        tool_calls = []
        for tc in tool_calls_raw:
            tool_calls.append({
                "id": tc.id,
                "name": tc.function.name,
                "arguments": json.loads(tc.function.arguments),
            })

        return text, tool_calls
