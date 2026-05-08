"""Code Review Agent - scans code for bugs, style issues, and security vulnerabilities."""

from __future__ import annotations

from agents.base import BaseAgent
from core.llm_client import LLMConfig
from core.tools import FileReadTool, CodeSearchTool


class CodeReviewAgent(BaseAgent):
    """Agent specialized in automated code review."""

    REVIEW_PROMPT = """You are a Code Review Agent. Analyze the provided code and identify:

1. **Bugs**: Logic errors, null/undefined references, race conditions
2. **Security Issues**: SQL injection, XSS, hardcoded secrets, improper input validation
3. **Code Quality**: Code smells, duplicated code, overly complex functions
4. **Best Practices**: Missing error handling, improper resource cleanup, naming conventions
5. **Performance**: Unnecessary loops, memory leaks, N+1 queries

For each issue found, provide:
- File and approximate location
- Severity (Critical/Warning/Info)
- Description of the issue
- Suggested fix with code example

Format your report in Markdown with clear sections."""

    def __init__(self, config: LLMConfig | None = None, **kwargs):
        super().__init__(config=config, **kwargs)
        self.setup_tools()

    def setup_tools(self) -> None:
        """Register code review tools."""
        self.register_tool("file_read", FileReadTool(max_lines=1000))
        self.register_tool("code_search", CodeSearchTool())

    def review(self, path: str, output_file: str | None = None) -> str:
        """Review a codebase and optionally write the report to a file."""
        result = self.run(
            f"Perform a comprehensive code review of the project at {path}. "
            f"Scan for bugs, security issues, code quality problems, and performance concerns. "
            f"Provide a structured report with severity levels and fix suggestions."
        )

        if output_file and result:
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result)

        return result

    def review_file(self, filepath: str) -> str:
        """Review a single file."""
        result = self.run(
            f"Review the code file at {filepath}. Identify bugs, security issues, "
            f"and code quality problems. Provide specific line references and fix suggestions."
        )
        return result
