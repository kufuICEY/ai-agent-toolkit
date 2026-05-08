"""Multi-Agent Workflow Orchestrator - chains multiple agents into complex pipelines."""

from __future__ import annotations

import yaml
import logging
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console
from rich.table import Table

from agents.diagnostic import DiagnosticsAgent
from agents.code_review import CodeReviewAgent
from core.llm_client import LLMConfig

console = Console()
logger = logging.getLogger(__name__)


@dataclass
class AgentStep:
    id: str
    type: str
    task: str
    depends_on: list[str] = field(default_factory=list)
    result: str | None = None
    status: str = "pending"  # pending | running | completed | failed


class Orchestrator:
    """Orchestrates multiple agents in a defined workflow pipeline."""

    AGENT_REGISTRY = {
        "diagnostic": DiagnosticsAgent,
        "code_review": CodeReviewAgent,
    }

    def __init__(self, config: LLMConfig | None = None):
        self.config = config
        self.steps: list[AgentStep] = []

    def load_workflow(self, workflow_path: str) -> None:
        """Load a workflow definition from a YAML file."""
        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = yaml.safe_load(f)

        self.steps.clear()
        for agent_def in workflow.get("agents", []):
            step = AgentStep(
                id=agent_def["id"],
                type=agent_def["type"],
                task=agent_def["task"],
                depends_on=agent_def.get("depends_on", []),
            )
            self.steps.append(step)

        console.print(f"[green]Loaded workflow:[/green] {workflow.get('name', 'Untitled')}")
        console.print(f"[dim]Steps: {len(self.steps)}[/dim]")

    def add_step(self, step_id: str, agent_type: str, task: str,
                 depends_on: list[str] | None = None) -> None:
        """Manually add a step to the workflow."""
        self.steps.append(AgentStep(
            id=step_id,
            type=agent_type,
            task=task,
            depends_on=depends_on or [],
        ))

    def run(self) -> dict[str, str]:
        """Execute the workflow, respecting dependencies."""
        results = {}
        completed_ids = set()

        total = len(self.steps)
        if total == 0:
            console.print("[yellow]No steps in workflow.[/yellow]")
            return results

        while len(completed_ids) < total:
            progress_made = False

            for step in self.steps:
                if step.status != "pending":
                    continue

                # Check if all dependencies are satisfied
                if not all(dep in completed_ids for dep in step.depends_on):
                    continue

                # Execute this step
                step.status = "running"
                console.print(f"\n[bold cyan]Running step: {step.id}[/bold cyan]")
                console.print(f"[dim]Type: {step.type} | Task: {step.task[:100]}...[/dim]")

                try:
                    agent = self._create_agent(step.type)
                    # Inject context from dependency results
                    if step.depends_on:
                        context = "\n\n".join(
                            f"Results from {dep}:\n{results[dep]}" for dep in step.depends_on
                        )
                        enriched_task = f"{step.task}\n\nContext from previous steps:\n{context}"
                    else:
                        enriched_task = step.task

                    result = agent.run(enriched_task)
                    step.result = result
                    step.status = "completed"
                    results[step.id] = result
                    completed_ids.add(step.id)
                    progress_made = True

                    console.print(f"[green]Completed: {step.id}[/green]")

                except Exception as e:
                    step.status = "failed"
                    step.result = str(e)
                    logger.error(f"Step {step.id} failed: {e}")
                    console.print(f"[red]Failed: {step.id} - {e}[/red]")
                    progress_made = True

            if not progress_made:
                # Circular dependency or unresolved dependency
                pending = [s.id for s in self.steps if s.status == "pending"]
                console.print(f"[red]Deadlock detected. Pending steps: {pending}[/red]")
                break

        self._print_summary()
        return results

    def _create_agent(self, agent_type: str):
        """Create an agent instance based on type."""
        agent_class = self.AGENT_REGISTRY.get(agent_type)
        if not agent_class:
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(self.AGENT_REGISTRY.keys())}")

        return agent_class(config=self.config, verbose=True)

    def _print_summary(self) -> None:
        """Print a summary table of all steps."""
        table = Table(title="Workflow Summary")
        table.add_column("Step", style="cyan")
        table.add_column("Type")
        table.add_column("Status", style="bold")
        table.add_column("Result Preview")

        for step in self.steps:
            status_style = {
                "completed": "[green]Completed[/green]",
                "failed": "[red]Failed[/red]",
                "running": "[yellow]Running[/yellow]",
                "pending": "[dim]Pending[/dim]",
            }.get(step.status, step.status)

            preview = (step.result or "")[:100] + "..." if step.result and len(step.result) > 100 else (step.result or "-")

            table.add_row(step.id, step.type, status_style, preview)

        console.print(table)
