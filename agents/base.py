"""Base Agent class implementing the ReAct (Reasoning + Acting) loop."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from typing import Any

from rich.console import Console
from rich.panel import Panel

from core.llm_client import LLMClient, LLMConfig
from core.memory import ConversationMemory

console = Console()
logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI Agent powered by the ReAct (Reasoning + Acting) framework.

For each step, you must:
1. **Think**: Analyze the current situation and decide what to do next
2. **Act**: Use one of the available tools to gather information or take action
3. **Observe**: Process the tool's output
4. **Repeat**: Continue until you have enough information to provide a final answer

When you have gathered enough information, provide your final analysis and recommendations.

Format your responses clearly. When using tools, output the tool name and arguments as JSON."""


class BaseAgent(ABC):
    """Base class for all agents using the ReAct loop."""

    def __init__(
        self,
        config: LLMConfig | None = None,
        max_iterations: int = 20,
        verbose: bool = True,
    ):
        self.llm = LLMClient(config)
        self.memory = ConversationMemory(max_entries=100)
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.tools: dict[str, Any] = {}
        self._tool_schemas: list[dict] = []

    def register_tool(self, name: str, tool: Any) -> None:
        """Register a tool with the agent."""
        self.tools[name] = tool
        if hasattr(tool, "schema"):
            self._tool_schemas.append(tool.schema)

    def _execute_tool(self, name: str, arguments: dict) -> str:
        """Execute a registered tool by name."""
        if name not in self.tools:
            return f"Error: Unknown tool '{name}'. Available tools: {list(self.tools.keys())}"

        tool = self.tools[name]
        try:
            if name == "shell":
                result = tool.run(arguments.get("command", ""))
                return result.output if result.success else f"Error: {result.error}"
            elif name == "file_read":
                result = tool.read(arguments.get("path", ""))
                return result.output if result.success else f"Error: {result.error}"
            elif name == "code_search":
                result = tool.search(
                    arguments.get("pattern", ""),
                    arguments.get("file_pattern", "*"),
                )
                return result.output if result.success else f"Error: {result.error}"
            elif name == "network_diag":
                action = arguments.get("action", "ping")
                target = arguments.get("target", "")
                port = arguments.get("port", 80)
                if action == "ping":
                    result = tool.ping(target)
                elif action == "check_port":
                    result = tool.check_port(target, port)
                elif action == "check_dns":
                    result = tool.check_dns(target)
                else:
                    return f"Error: Unknown action '{action}'"
                return result.output if result.success else f"Error: {result.error}"
            else:
                # Generic tool execution
                method = arguments.get("action", "__call__")
                if hasattr(tool, method):
                    return getattr(tool, method)(**{k: v for k, v in arguments.items() if k != "action"})
                return str(tool)
        except Exception as e:
            return f"Error executing tool '{name}': {e}"

    def _parse_tool_call(self, response: str) -> tuple[str | None, dict | None]:
        """Try to parse a tool call from the LLM response."""
        # Try to find JSON block with tool info
        import re

        # Look for patterns like: tool_name({"param": "value"}) or Tool: tool_name, args: {...}
        patterns = [
            r"```json\s*(\{.*?\})\s*```",
            r"Tool:\s*(\w+).*?(?:args|arguments):\s*(\{[^}]+\})",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, response, re.DOTALL)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        tool_name, args_str = match
                        try:
                            args = json.loads(args_str) if isinstance(args_str, str) else args_str
                            return tool_name, args
                        except json.JSONDecodeError:
                            continue
                    else:
                        try:
                            data = json.loads(match)
                            if "tool" in data and "arguments" in data:
                                return data["tool"], data["arguments"]
                        except json.JSONDecodeError:
                            continue

        return None, None

    def run(self, task: str) -> str:
        """Execute the agent's main loop."""
        if self.verbose:
            console.print(Panel(f"[bold blue]Task:[/bold blue] {task}", title="AI Agent"))

        self.memory.clear()
        self.memory.add("user", task)

        for iteration in range(self.max_iterations):
            if self.verbose:
                console.print(f"\n[dim]--- Iteration {iteration + 1}/{self.max_iterations} ---[/dim]")

            # Build prompt with context
            context = self._build_context()

            # Get LLM response
            try:
                response = self.llm.chat_with_tools(
                    prompt=task if iteration == 0 else f"Based on the context above, continue your analysis.\n\nOriginal task: {task}",
                    tools=self._tool_schemas,
                    system_prompt=SYSTEM_PROMPT + "\n\nCurrent context:\n" + context if context else SYSTEM_PROMPT,
                )
            except Exception as e:
                logger.error(f"LLM call failed: {e}")
                break

            response_text, tool_calls = response

            if self.verbose and response_text:
                console.print(f"[green]Agent:[/green] {response_text[:500]}")

            # Execute tool calls
            if tool_calls:
                for tc in tool_calls:
                    tool_name = tc["name"]
                    tool_args = tc["arguments"]

                    if self.verbose:
                        console.print(f"[yellow]Tool:[/yellow] {tool_name}({json.dumps(tool_args, ensure_ascii=False)[:200]})")

                    result = self._execute_tool(tool_name, tool_args)
                    self.memory.add_tool_result(tool_name, result)

                    if self.verbose:
                        console.print(f"[dim]Result:[/dim] {result[:300]}")
            elif "final" in response_text.lower() or "conclusion" in response_text.lower() or "summary" in response_text.lower():
                # Agent has reached a conclusion
                self.memory.add("assistant", response_text)
                return response_text
            else:
                self.memory.add("assistant", response_text)

        # Return the last response as the final answer
        final = self.memory.get_messages()
        return final[-1]["content"] if final else "Agent did not produce a result."

    def _build_context(self) -> str:
        """Build context from recent memory for the agent."""
        messages = self.memory.get_context_window()
        if len(messages) <= 1:
            return ""

        context_parts = []
        for msg in messages[1:]:  # Skip the original user task
            role = msg["role"].capitalize()
            content = msg["content"][:300]
            context_parts.append(f"[{role}]: {content}")

        return "\n".join(context_parts[-10:])  # Last 10 messages

    @abstractmethod
    def setup_tools(self) -> None:
        """Set up the tools available to this agent. Must be implemented by subclasses."""
        ...
