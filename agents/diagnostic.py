"""Diagnostics Agent - automatically analyzes system issues and generates fix suggestions."""

from __future__ import annotations

from agents.base import BaseAgent
from core.llm_client import LLMConfig
from core.tools import ShellTool, FileReadTool, NetworkDiagTool


class DiagnosticsAgent(BaseAgent):
    """Agent specialized in system diagnostics and troubleshooting."""

    DIAG_SYSTEM_PROMPT = """You are a Diagnostics Agent specialized in analyzing system issues.

Your workflow:
1. Gather system information (OS, network config, running processes)
2. Identify potential issues based on symptoms
3. Run targeted diagnostic commands
4. Analyze results and pinpoint root causes
5. Generate step-by-step fix instructions

Focus areas:
- Network connectivity (DNS, firewall, routing, virtual network adapters)
- Application compatibility (dependencies, configurations, permissions)
- System performance (resource usage, conflicts, bottlenecks)

Always provide actionable fix steps with specific commands or settings to change."""

    def __init__(self, config: LLMConfig | None = None, **kwargs):
        super().__init__(config=config, **kwargs)
        self.setup_tools()

    def setup_tools(self) -> None:
        """Register diagnostic tools."""
        self.register_tool("shell", ShellTool(timeout=30))
        self.register_tool("file_read", FileReadTool())
        self.register_tool("network_diag", NetworkDiagTool())

    def diagnose_network(self, host: str = "8.8.8.8") -> str:
        """Run a quick network diagnostic."""
        result = self.run(
            f"Diagnose network connectivity issues. Check DNS resolution, ping {host}, "
            f"and identify any firewall or routing problems. Provide a summary of findings."
        )
        return result

    def diagnose_application(self, app_path: str, symptoms: str) -> str:
        """Diagnose application-specific issues."""
        result = self.run(
            f"Analyze the application at {app_path} which is experiencing the following issue: {symptoms}. "
            f"Check the application's configuration, dependencies, and system compatibility. "
            f"Provide specific fix steps."
        )
        return result
