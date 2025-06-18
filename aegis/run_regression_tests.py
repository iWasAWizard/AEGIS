# run_regression_tests.py
"""
A simple regression test runner for the AEGIS framework.

This script discovers and runs all task-based regression tests defined in
the 'tests/regression/' directory. It uses the agent's own provenance
reporting to verify success or failure.
"""

import asyncio
import json
import os
import stat
import uuid
from pathlib import Path

import typer
import yaml
from rich.console import Console

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState
from aegis.exceptions import AegisError
from aegis.schemas.agent import AgentConfig, AgentGraphConfig
from aegis.schemas.launch import LaunchRequest
from aegis.utils.config_loader import load_agent_config
from aegis.utils.log_sinks import task_id_context
from aegis.utils.tool_loader import import_all_tools

app = typer.Typer()
console = Console()


async def run_single_test(test_path: Path) -> bool:
    """
    Loads and executes a single regression test file.

    :param test_path: The path to the test case's YAML file.
    :return: True if the test passed, False otherwise.
    """
    console.print(f"▶️  Running test: [cyan]{test_path.name}[/cyan]")
    task_id = f"test-{test_path.stem}-{uuid.uuid4().hex[:6]}"
    task_id_context.set(task_id)

    try:
        launch_payload = LaunchRequest.model_validate(
            yaml.safe_load(test_path.read_text())
        )
        launch_payload.task.task_id = task_id

        preset_config: AgentConfig = load_agent_config(
            profile=(
                launch_payload.config
                if isinstance(launch_payload.config, str)
                else "default"
            )
        )
        runtime_config = preset_config.runtime
        if launch_payload.iterations is not None:
            runtime_config.iterations = launch_payload.iterations

        initial_state = TaskState(
            task_id=task_id,
            task_prompt=launch_payload.task.prompt,
            runtime=runtime_config,
        )

        graph_structure = AgentGraphConfig(
            state_type=preset_config.state_type,
            entrypoint=preset_config.entrypoint,
            nodes=preset_config.nodes,
            edges=preset_config.edges,
            condition_node=preset_config.condition_node,
            condition_map=preset_config.condition_map,
            middleware=preset_config.middleware,
        )
        agent_graph = AgentGraph(graph_structure).build_graph()
        await agent_graph.ainvoke(initial_state.model_dump())

    except AegisError as e:
        console.print(f"  [bold red]ERROR DURING EXECUTION:[/bold red] {e}")
        return False
    except Exception as e:
        console.print(f"  [bold red]UNEXPECTED SCRIPT ERROR:[/bold red] {e}")
        console.print_exception(show_locals=False)
        return False

    provenance_path = Path("reports") / task_id / "provenance.json"
    if not provenance_path.exists():
        console.print(
            f"  [bold red]FAIL:[/bold red] Provenance report not found at '{provenance_path}'"
        )
        return False

    try:
        with provenance_path.open("r") as f:
            report = json.load(f)

        final_status = report.get("final_status")
        if final_status == "SUCCESS":
            console.print(f"  [bold green]PASS:[/bold green] Agent reported success.")
            return True
        else:
            console.print(
                f"  [bold red]FAIL:[/bold red] Agent reported status: [yellow]{final_status}[/yellow]"
            )
            return False

    except (IOError, json.JSONDecodeError) as e:
        console.print(
            f"  [bold red]FAIL:[/bold red] Could not read or parse provenance report: {e}"
        )
        return False


@app.command()
def main():
    """
    Discovers and runs all regression tests, then reports the results.
    """
    import_all_tools()

    console.rule("[bold blue]AEGIS Regression Test Suite[/bold blue]")
    regression_dir = Path("tests/regression")

    if not regression_dir.is_dir():
        console.print(
            f"[bold red]Error:[/bold red] Regression test directory not found at '{regression_dir}'"
        )
        raise typer.Exit(1)

    for script_path in regression_dir.glob("*.py"):
        console.print(
            f"Setting executable permissions for [cyan]{script_path.name}[/cyan]..."
        )
        st = os.stat(script_path)
        os.chmod(script_path, st.st_mode | stat.S_IEXEC)

    test_files = sorted(regression_dir.glob("test_*.yaml"))

    if not test_files:
        console.print("[yellow]No regression tests found.[/yellow]")
        raise typer.Exit()

    console.print(f"Found {len(test_files)} test(s) to run.\n")

    results = {"passed": 0, "failed": 0}

    for test_file in test_files:
        passed = asyncio.run(run_single_test(test_file))
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1
        console.print("-" * 20)

    console.rule("[bold blue]Test Summary[/bold blue]")
    console.print(f"[bold green]Passed: {results['passed']}[/bold green]")
    console.print(f"[bold red]Failed: {results['failed']}[/bold red]")

    if results["failed"] > 0:
        raise typer.Exit(code=1)
    else:
        console.print("\n[bold green]✅ All tests passed successfully![/bold green]")


if __name__ == "__main__":
    app()
