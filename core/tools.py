"""Built-in tools for agents: shell execution, file operations, and code search."""

from __future__ import annotations

import os
import subprocess
import fnmatch
from dataclasses import dataclass


@dataclass
class ToolResult:
    success: bool
    output: str
    error: str = ""


class ShellTool:
    """Execute shell commands safely."""

    def __init__(self, timeout: int = 30, cwd: str | None = None):
        self.timeout = timeout
        self.cwd = cwd

    def run(self, command: str) -> ToolResult:
        """Execute a shell command and return the result."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=self.cwd,
            )
            return ToolResult(
                success=result.returncode == 0,
                output=result.stdout[:5000],  # Truncate large outputs
                error=result.stderr[:2000],
            )
        except subprocess.TimeoutExpired:
            return ToolResult(success=False, output="", error=f"Command timed out after {self.timeout}s")
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    @property
    def schema(self) -> dict:
        return {
            "name": "shell",
            "description": "Execute a shell command and return stdout/stderr. Use for system diagnostics, running scripts, or checking configurations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to execute",
                    }
                },
                "required": ["command"],
            },
        }


class FileReadTool:
    """Read file contents."""

    def __init__(self, max_lines: int = 500):
        self.max_lines = max_lines

    def read(self, path: str) -> ToolResult:
        """Read a file and return its contents."""
        try:
            if not os.path.isfile(path):
                return ToolResult(success=False, output="", error=f"File not found: {path}")

            with open(path, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()

            if len(lines) > self.max_lines:
                content = "".join(lines[: self.max_lines])
                content += f"\n... (truncated, showing first {self.max_lines} of {len(lines)} lines)"
            else:
                content = "".join(lines)

            return ToolResult(success=True, output=content)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    @property
    def schema(self) -> dict:
        return {
            "name": "file_read",
            "description": "Read the contents of a file. Returns up to 500 lines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Absolute or relative path to the file",
                    }
                },
                "required": ["path"],
            },
        }


class CodeSearchTool:
    """Search for patterns in code files."""

    def __init__(self, directory: str = "."):
        self.directory = directory

    def search(self, pattern: str, file_pattern: str = "*") -> ToolResult:
        """Search for a text pattern in files matching the given glob."""
        matches = []
        try:
            for root, dirs, files in os.walk(self.directory):
                # Skip common non-source directories
                dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "__pycache__", ".venv"}]

                for filename in files:
                    if not fnmatch.fnmatch(filename, file_pattern):
                        continue

                    filepath = os.path.join(root, filename)
                    try:
                        with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                            for i, line in enumerate(f, 1):
                                if pattern.lower() in line.lower():
                                    matches.append(f"{filepath}:{i}: {line.strip()}")
                                    if len(matches) >= 50:
                                        break
                    except (PermissionError, OSError):
                        continue

                if len(matches) >= 50:
                    break

            if not matches:
                return ToolResult(success=True, output=f"No matches found for '{pattern}'")

            output = "\n".join(matches)
            if len(matches) >= 50:
                output += f"\n... (truncated, showing first 50 of {len(matches)}+ matches)"

            return ToolResult(success=True, output=output)
        except Exception as e:
            return ToolResult(success=False, output="", error=str(e))

    @property
    def schema(self) -> dict:
        return {
            "name": "code_search",
            "description": "Search for a text pattern across code files in a directory. Skips .git, node_modules, and __pycache__.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {
                        "type": "string",
                        "description": "Text pattern to search for",
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "Glob pattern for files to search (default: *)",
                    },
                },
                "required": ["pattern"],
            },
        }


class NetworkDiagTool:
    """Network diagnostic tools."""

    def ping(self, host: str, count: int = 4) -> ToolResult:
        """Ping a host to check connectivity."""
        return ShellTool(timeout=15).run(f"ping -n {count} {host}")

    def check_port(self, host: str, port: int) -> ToolResult:
        """Check if a port is open on a host."""
        return ShellTool(timeout=10).run(
            f"powershell -Command \"Test-NetConnection -ComputerName {host} -Port {port}\""
        )

    def check_dns(self, hostname: str) -> ToolResult:
        """Check DNS resolution for a hostname."""
        return ShellTool(timeout=10).run(f"nslookup {hostname}")

    @property
    def schema(self) -> dict:
        return {
            "name": "network_diag",
            "description": "Run network diagnostics: ping, port check, or DNS resolution.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["ping", "check_port", "check_dns"],
                        "description": "Type of diagnostic to run",
                    },
                    "target": {
                        "type": "string",
                        "description": "Hostname or IP address",
                    },
                    "port": {
                        "type": "integer",
                        "description": "Port number (for check_port action)",
                    },
                },
                "required": ["action", "target"],
            },
        }
