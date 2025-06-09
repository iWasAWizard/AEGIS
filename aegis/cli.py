# aegis/cli.py
"""
Command-line interface (CLI) for the AEGIS framework.

This module provides a set of commands for interacting with the AEGIS agent
from the terminal, such as running tasks, listing tools, and inspecting
configuration. It uses the Typer library to create a clean and user-friendly
CLI experience.
"""

import asyncio
import uuid
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState
from aegis.registry import TOOL_REGISTRY, log_registry_contents
from aegis.schemas.agent import AgentConfig, AgentGraphConfig
from aegis.schemas.launch import LaunchRequest
from aegis.utils.config_loader import load_agent_config
from aegis.utils.log_sinks import task_id_context
from aegis.utils.logger import setup_logger
from aegis.utils.tool_loader import import_all_tools

# Initialize Typer app, Rich console, and logger
app = typer.Typer(
    name="aegis",
    help="A modular, autonomous agent framework for planning and execution.",
    add_completion=False,
)
console = Console()
logger = setup_logger(__name__)


@app.callback()
def main() -> None:
    """AEGIS command-line interface."""
    # This function runs before any command.
    # We ensure tools are loaded once for the CLI session.
    if not TOOL_REGISTRY:
        import_all_tools()


@app.command(name="run-task")
def run_task(
    task_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            help="Path to the YAML file containing the task request.",
        ),
    ],
) -> None:
    """
    Runs a single agent task from a specified YAML file.
    """
    console.print(f"📄 Loading task from: [bold cyan]{task_file}[/bold cyan]")
    try:
        with task_file.open("r") as f:
            data = yaml.safe_load(f)

        # We use the LaunchRequest schema to parse the file for consistency with the API.
        launch_payload = LaunchRequest.model_validate(data)

    except (yaml.YAMLError, ValueError) as e:
        console.print(
            f"[bold red]Error:[/bold red] Failed to parse or validate task file: {e}"
        )
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(
            f"[bold red]Error:[/bold red] An unexpected error occurred while loading the task: {e}"
        )
        raise typer.Exit(code=1)

    console.print(
        f"🚀 Launching task: [bold magenta]'{launch_payload.task.prompt}'[/bold magenta]"
    )

    # Run the main async task execution logic.
    try:
        asyncio.run(execute_graph(launch_payload))
    except Exception as e:
        console.print(
            f"\n[bold red]FATAL ERROR:[/bold red] Agent execution failed: {e}"
        )
        raise typer.Exit(code=1)


async def execute_graph(payload: LaunchRequest) -> None:
    """The core asynchronous logic for running the agent graph."""
    task_id = payload.task.task_id or str(uuid.uuid4())
    task_id_context.set(task_id)

    preset_config: AgentConfig = load_agent_config(
        profile=payload.config if isinstance(payload.config, str) else "default"
    )

    runtime_config = preset_config.runtime
    if payload.iterations is not None:
        runtime_config.iterations = payload.iterations

    initial_state = TaskState(
        task_id=task_id, task_prompt=payload.task.prompt, runtime=runtime_config
    )

    graph_structure = AgentGraphConfig(**preset_config.model_dump())
    agent_graph = AgentGraph(graph_structure).build_graph()

    console.print("\n[yellow]--- Agent Execution Starting ---[/yellow]")
    final_state_dict = await agent_graph.ainvoke(initial_state)
    console.print("\n[green]--- Agent Execution Complete ---[/green]")

    final_state = TaskState(**final_state_dict)

    console.print("\n[bold]Final Summary:[/bold]")
    console.print(final_state.final_summary or "[No summary was generated]")


@app.command(name="list-tools")
def list_tools() -> None:
    """
    Lists all registered tools available to the agent.
    """
    log_registry_contents()  # Use the existing detailed logger for now.

    # A more user-friendly table format:
    table = Table(title="🛠️  AEGIS Registered Tools")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Category", style="magenta")
    table.add_column("Description", style="white")
    table.add_column("Safe Mode", style="yellow")

    if not TOOL_REGISTRY:
        console.print("[yellow]No tools are registered.[/yellow]")
        return

    for name, tool in sorted(TOOL_REGISTRY.items()):
        safe_str = "✅" if tool.safe_mode else "❌"
        table.add_row(name, tool.category or "N/A", tool.description, safe_str)

    console.print(table)


if __name__ == "__main__":
    app()
