# run_regression_tests.py
"""
A simple regression test runner for the AEGIS framework.

This script discovers and runs all task-based regression tests defined in
the 'tests/regression/' directory. It uses the agent's own provenance
reporting to verify success or failure. For test cases that include an
'expected_output', it uses an LLM-as-judge to score the agent's performance.
"""

import asyncio
import json
import os
import stat
import uuid
from pathlib import Path
from typing import Optional

import typer
import yaml
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState
from aegis.exceptions import AegisError
from aegis.schemas.agent import AgentConfig, AgentGraphConfig
from aegis.schemas.launch import LaunchRequest
from aegis.tools.wrappers.evaluation import llm_judge, LLMJudgeInput, Judgement
from aegis.utils.config_loader import load_agent_config
from aegis.utils.llm_query import get_provider_for_profile
from aegis.utils.log_sinks import task_id_context
from aegis.utils.tool_loader import import_all_tools

app = typer.Typer()
console = Console()


async def run_and_evaluate_test(
    test_path: Path, judge_model_profile: Optional[str]
) -> dict:
    """
    Loads and executes a single regression test file, and evaluates if applicable.
    """
    console.print(f"▶️  Running test: [cyan]{test_path.name}[/cyan]")
    task_id = f"test-{test_path.stem}-{uuid.uuid4().hex[:6]}"
    task_id_context.set(task_id)
    final_summary = "Agent did not produce a final summary."
    final_status = "UNKNOWN"
    judgement = None

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
        if launch_payload.execution:
            runtime_config = runtime_config.model_copy(
                update=launch_payload.execution.model_dump(exclude_unset=True)
            )
        if launch_payload.iterations is not None:
            runtime_config.iterations = launch_payload.iterations

        initial_state = TaskState(
            task_id=task_id,
            task_prompt=launch_payload.task.prompt,
            runtime=runtime_config,
        )

        graph_structure = AgentGraphConfig(**preset_config.model_dump())
        agent_graph = AgentGraph(graph_structure).build_graph()
        final_state_dict = await agent_graph.ainvoke(initial_state.model_dump())
        final_state = TaskState(**final_state_dict)
        final_summary = final_state.final_summary or final_summary

        provenance_path = Path("reports") / task_id / "provenance.json"
        if provenance_path.exists():
            report = json.loads(provenance_path.read_text())
            final_status = report.get("final_status", "UNKNOWN")

        # --- Evaluation Step ---
        if launch_payload.task.expected_output and judge_model_profile:
            console.print("  [yellow]⚖️ Evaluating output with LLM Judge...[/yellow]")
            judge_input = LLMJudgeInput(
                task_prompt=launch_payload.task.prompt,
                expected_output=launch_payload.task.expected_output,
                actual_output=final_summary,
            )
            # We need a provider and state for the judge tool
            judge_provider = get_provider_for_profile(judge_model_profile)
            judge_state = TaskState(
                task_id="judge", task_prompt="", runtime=runtime_config
            )

            judgement_dict = await llm_judge(judge_input, judge_state, judge_provider)
            judgement = Judgement(**judgement_dict)
            final_status = "EVALUATED"

    except AegisError as e:
        console.print(f"  [bold red]ERROR DURING EXECUTION:[/bold red] {e}")
        final_status = "EXECUTION_ERROR"
    except Exception as e:
        console.print(f"  [bold red]UNEXPECTED SCRIPT ERROR:[/bold red] {e}")
        console.print_exception(show_locals=False)
        final_status = "SCRIPT_ERROR"

    return {"status": final_status, "judgement": judgement}


@app.command()
def main(
    judge_model: Optional[str] = typer.Option(
        None,
        "--judge-model",
        "-j",
        help="The backend profile to use for the LLM Judge. If not provided, evaluation is skipped.",
    )
):
    """
    Discovers and runs all regression tests, then reports the results.
    """
    import_all_tools()

    console.rule("[bold blue]AEGIS Regression & Evaluation Suite[/bold blue]")
    regression_dir = Path("tests/regression")

    if not regression_dir.is_dir():
        console.print(
            f"[bold red]Error:[/bold red] Regression test directory not found at '{regression_dir}'"
        )
        raise typer.Exit(1)

    for script_path in regression_dir.glob("*.py"):
        os.chmod(script_path, stat.S_IRWXU)

    test_files = sorted(regression_dir.glob("test_*.yaml"))
    if not test_files:
        console.print("[yellow]No regression tests found.[/yellow]")
        raise typer.Exit()

    console.print(f"Found {len(test_files)} test(s) to run.")
    if judge_model:
        console.print(
            f"⚖️  LLM Judge is enabled using backend profile: [bold cyan]{judge_model}[/bold cyan]"
        )
    else:
        console.print("⚖️  LLM Judge is disabled. Running as a simple regression suite.")
    console.print("-" * 20)

    results = []
    for test_file in test_files:
        result = asyncio.run(run_and_evaluate_test(test_file, judge_model))
        results.append({"name": test_file.name, **result})
        console.print("-" * 20)

    console.rule("[bold blue]Test Summary[/bold blue]")

    passed_count = sum(1 for r in results if r["status"] == "SUCCESS")
    failed_count = sum(
        1 for r in results if r["status"] not in ["SUCCESS", "EVALUATED"]
    )
    evaluated_tests = [r for r in results if r["status"] == "EVALUATED"]

    console.print(f"[bold green]Simple Pass: {passed_count}[/bold green]")
    console.print(f"[bold red]Simple Fail: {failed_count}[/bold red]")

    if evaluated_tests:
        total_score = sum(r["judgement"].score for r in evaluated_tests)
        avg_score = total_score / len(evaluated_tests)
        console.print(f"[bold yellow]Evaluated: {len(evaluated_tests)}[/bold yellow]")
        console.print(f"[bold cyan]Average Score: {avg_score:.2f} / 5.00[/bold cyan]")

        for res in evaluated_tests:
            judgement = res["judgement"]
            color = (
                "green"
                if judgement.score >= 4
                else "yellow" if judgement.score == 3 else "red"
            )
            panel = Panel(
                f"[bold]Rationale:[/bold]\n{judgement.rationale}",
                title=f"[bold {color}]{res['name']} - Score: {judgement.score}/5[/bold {color}]",
                border_style=color,
            )
            console.print(panel)

    if failed_count > 0:
        raise typer.Exit(code=1)
    else:
        console.print(
            "\n[bold green]✅ All tests passed or were successfully evaluated![/bold green]"
        )


if __name__ == "__main__":
    app()
