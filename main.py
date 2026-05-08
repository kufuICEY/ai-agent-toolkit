"""AI Agent Toolkit - CLI entry point."""

from __future__ import annotations

import sys
import os
import yaml
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import click
from rich.console import Console
from rich.logging import RichHandler

from core.llm_client import LLMConfig
from agents.diagnostic import DiagnosticsAgent
from agents.code_review import CodeReviewAgent
from agents.orchestrator import Orchestrator

console = Console()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True)],
)
logger = logging.getLogger("ai-agent-toolkit")


def _load_config(config_path: str = "config.yaml") -> LLMConfig:
    """Load configuration from YAML file."""
    paths_to_try = [
        config_path,
        "config.example.yaml",
        os.path.expanduser("~/.ai-agent-toolkit/config.yaml"),
    ]

    for path in paths_to_try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                cfg = yaml.safe_load(f)
            llm_cfg = cfg.get("llm", {})
            return LLMConfig(
                provider=llm_cfg.get("provider", "openai"),
                api_key=llm_cfg.get("api_key", ""),
                model=llm_cfg.get("model", "gpt-4o"),
                base_url=llm_cfg.get("base_url", "https://api.openai.com/v1"),
                temperature=llm_cfg.get("temperature", 0.3),
            )

    console.print("[yellow]No config file found. Using default configuration.[/yellow]")
    console.print("[dim]Copy config.example.yaml to config.yaml and fill in your API key.[/dim]")
    return LLMConfig()


@click.group()
@click.option("--config", "-c", default="config.yaml", help="Path to config file")
@click.pass_context
def cli(ctx, config):
    """AI Agent Toolkit - Automated diagnostics, code review, and workflow orchestration."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = _load_config(config)


@cli.command()
@click.option("--task", "-t", required=True, help="Diagnostic task description")
@click.pass_context
def diagnostic(ctx, task):
    """Run the Diagnostics Agent to analyze system issues."""
    console.print("[bold blue]Starting Diagnostics Agent...[/bold blue]\n")

    agent = DiagnosticsAgent(config=ctx.obj["config"])
    result = agent.run(task)

    console.print("\n" + "=" * 60)
    console.print("[bold green]Diagnostic Result:[/bold green]")
    console.print("=" * 60)
    console.print(result)


@cli.command()
@click.option("--path", "-p", required=True, help="Path to the codebase to review")
@click.option("--report", "-r", default=None, help="Output report file path (e.g., output.md)")
@click.pass_context
def code_review(ctx, path, report):
    """Run the Code Review Agent on a codebase."""
    console.print(f"[bold blue]Starting Code Review for: {path}[/bold blue]\n")

    agent = CodeReviewAgent(config=ctx.obj["config"])
    result = agent.review(path, output_file=report)

    if report:
        console.print(f"\n[green]Report written to: {report}[/green]")

    console.print("\n" + "=" * 60)
    console.print("[bold green]Review Summary:[/bold green]")
    console.print("=" * 60)
    console.print(result[:2000])


@cli.command()
@click.option("--config_file", "-f", required=True, help="Path to workflow YAML file")
@click.pass_context
def orchestrator(ctx, config_file):
    """Run a multi-agent workflow from a YAML configuration."""
    if not os.path.isfile(config_file):
        console.print(f"[red]Workflow file not found: {config_file}[/red]")
        return

    console.print("[bold blue]Starting Workflow Orchestrator...[/bold blue]\n")

    orch = Orchestrator(config=ctx.obj["config"])
    orch.load_workflow(config_file)
    results = orch.run()

    console.print("\n[bold green]All workflows completed.[/bold green]")


@cli.command()
def version():
    """Show version information."""
    console.print("[bold]AI Agent Toolkit[/bold] v1.0.0")
    console.print("A lightweight AI Agent toolkit for automated diagnostics and code review.")


if __name__ == "__main__":
    cli()
