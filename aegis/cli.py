# aegis/cli.py
"""
Command-line interface (CLI) for the AEGIS framework.

This module provides a set of commands for interacting with the AEGIS agent
from the terminal, such as running tasks, listing tools, and inspecting
configuration. It uses the Typer library to create a clean and user-friendly
CLI experience.
"""

import asyncio
import importlib
import sys
import uuid
from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table
from typing_extensions import Annotated
from langgraph.pregel import GraphInterrupt
from langfuse.langchain import CallbackHandler

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState
from aegis.exceptions import AegisError, ConfigurationError
from aegis.registry import TOOL_REGISTRY
from aegis.schemas.agent import AgentConfig, AgentGraphConfig
from aegis.schemas.launch import LaunchRequest
from aegis.utils.config_loader import load_agent_config
from aegis.utils.log_sinks import task_id_context
from aegis.utils.logger import setup_logger
from aegis.utils.tool_loader import import_all_tools
from aegis.utils.backend_loader import get_backend_config
from aegis.utils.machine_loader import get_machine
from aegis.utils.config import get_config

# Initialize Typer app, Rich console, and logger
app = typer.Typer(
    name="aegis",
    help="A modular, autonomous agent framework for planning and execution.",
    add_completion=False,
)
console = Console()
logger = setup_logger(__name__)


@app.callback()
def main_callback() -> None:
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

    try:
        asyncio.run(execute_graph(launch_payload))
    except AegisError as e:
        console.print(
            f"\n[bold red]AGENT FAILED:[/bold red] A critical error occurred during execution."
        )
        console.print(f"[bold]Type:[/bold] {e.__class__.__name__}")
        console.print(f"[bold]Reason:[/bold] {e}")
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"\n[bold red]UNEXPECTED FATAL ERROR:[/bold red] {e}")
        console.print_exception(show_locals=True)
        raise typer.Exit(code=1)
    finally:
        console.print("\n[bold blue]--- Execution Finished ---[/bold blue]")


async def execute_graph(payload: LaunchRequest) -> None:
    """The core asynchronous logic for running the agent graph."""
    task_id = payload.task.task_id or str(uuid.uuid4())
    task_id_context.set(task_id)

    try:
        preset_config: AgentConfig = load_agent_config(
            profile=payload.config if isinstance(payload.config, str) else "default"
        )

        runtime_config = preset_config.runtime
        if payload.execution:
            runtime_config = runtime_config.model_copy(
                update=payload.execution.model_dump(exclude_unset=True)
            )
        if payload.iterations is not None:
            runtime_config.iterations = payload.iterations

        initial_state = TaskState(
            task_id=task_id, task_prompt=payload.task.prompt, runtime=runtime_config
        )

        graph_structure = AgentGraphConfig(
            state_type=preset_config.state_type,
            entrypoint=preset_config.entrypoint,
            nodes=preset_config.nodes,
            edges=preset_config.edges,
            condition_node=preset_config.condition_node,
            condition_map=preset_config.condition_map,
            middleware=preset_config.middleware,
            interrupt_nodes=preset_config.interrupt_nodes,
        )

        agent_graph = AgentGraph(graph_structure).build_graph()

        # Set up LangFuse tracing for the CLI run
        langfuse_handler = CallbackHandler()
        invocation_config = {
            "callbacks": [langfuse_handler],
            "metadata": {"user_id": "aegis-cli-user", "session_id": task_id},
        }

        console.print("\n[yellow]--- Agent Execution Starting ---[/yellow]")
        final_state_dict = await agent_graph.ainvoke(
            initial_state.model_dump(), config=invocation_config
        )
        console.print("\n[green]--- Agent Execution Complete ---[/green]")

        final_state = TaskState(**final_state_dict)

        console.print("\n[bold]Final Summary:[/bold]")
        console.print(final_state.final_summary or "[No summary was generated]")

    except GraphInterrupt:
        console.print(
            f"\n[bold yellow]⏸️ TASK PAUSED:[/bold yellow] Agent has paused for human input."
        )
        console.print(
            "To resume, you must use the API's /resume endpoint. Halting CLI execution."
        )


@app.command(name="list-tools")
def list_tools() -> None:
    """
    Lists all registered tools available to the agent.
    """
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


@app.command(name="run-evals")
def run_evals(
        dataset_name: Annotated[
            str, typer.Argument(help="The name of the dataset in LangFuse to run.")
        ],
        judge_model: Annotated[
            str,
            typer.Option(
                help="The model profile to use as the judge (e.g., 'openai_gpt4' or a vLLM profile)."
            ),
        ] = "openai_gpt4",
) -> None:
    """
    Runs an evaluation suite against a LangFuse dataset.
    """
    console.print(
        f"🧪 Starting evaluation run for dataset: [bold cyan]{dataset_name}[/bold cyan]"
    )
    try:
        from aegis.evaluation.eval_runner import main as run_eval_main

        asyncio.run(run_eval_main(dataset_name, judge_model))
    except ImportError as e:
        console.print(
            f"[bold red]Error:[/bold red] Failed to import evaluation module: {e}"
        )
        raise typer.Exit(code=1)
    except Exception as e:
        console.print(f"[bold red]EVALUATION FAILED:[/bold red] {e}")
        console.print_exception(show_locals=True)
        raise typer.Exit(code=1)


@app.command(name="validate-config")
def validate_config() -> None:
    """
    Proactively loads and validates all key configuration files.
    """
    console.rule("[bold blue]AEGIS Configuration Validator[/bold blue]")
    errors_found = 0

    def check(name, action):
        nonlocal errors_found
        try:
            console.print(f"🔍 Validating [cyan]{name}[/cyan]...", end="")
            action()
            console.print(f" [green]✅ OK[/green]")
        except (ConfigurationError, FileNotFoundError, Exception) as e:
            console.print(f" [bold red]❌ FAILED[/bold red]")
            console.print(f"   [red]└─ Reason: {e}[/red]")
            errors_found += 1

    # 1. Validate main config.yaml
    check("config.yaml", get_config)

    # 2. Validate all backend profiles
    try:
        backends_path = Path("backends.yaml")
        if backends_path.is_file():
            backend_profiles = yaml.safe_load(backends_path.read_text()).get("backends", [])
            for profile in backend_profiles:
                profile_name = profile.get("profile_name")
                if profile_name:
                    check(f"Backend Profile: {profile_name}", lambda: get_backend_config(profile_name))
    except Exception as e:
        console.print(f" [bold red]❌ FAILED[/bold red]")
        console.print(f"   [red]└─ Could not parse backends.yaml: {e}[/red]")
        errors_found += 1

    # 3. Validate all machine profiles
    try:
        machines_path = Path("machines.yaml")
        if machines_path.is_file():
            machine_profiles = yaml.safe_load(machines_path.read_text())
            for machine_name in machine_profiles:
                check(f"Machine Profile: {machine_name}", lambda name=machine_name: get_machine(name))
    except Exception as e:
        console.print(f" [bold red]❌ FAILED[/bold red]")
        console.print(f"   [red]└─ Could not parse machines.yaml: {e}[/red]")
        errors_found += 1

    # 4. Validate all presets
    presets_dir = Path("presets")
    if presets_dir.is_dir():
        for preset_file in presets_dir.glob("*.yaml"):
            profile_name = preset_file.stem
            check(f"Preset: {preset_file.name}", lambda name=profile_name: load_agent_config(profile=name))

    console.rule()
    if errors_found == 0:
        console.print("[bold green]✅ All configurations validated successfully![/bold green]")
    else:
        console.print(
            f"[bold red]❌ Found {errors_found} configuration error(s). Please review the output above.[/bold red]")
        raise typer.Exit(code=1)


@app.command(name="validate-tool")
def validate_tool(
        file_path: Annotated[
            Path,
            typer.Argument(
                exists=True,
                file_okay=True,
                dir_okay=False,
                readable=True,
                help="Path to the Python file containing the tool to validate.",
            ),
        ],
) -> None:
    """
    Validates a single tool file by attempting to import it.

    This checks for syntax errors, missing metadata in @register_tool,
    and invalid Pydantic input models.
    """
    console.print(f"🔎 Validating tool file: [bold cyan]{file_path}[/bold cyan]")

    module_dir = file_path.parent.resolve()
    if str(module_dir) not in sys.path:
        sys.path.insert(0, str(module_dir))

    module_name = file_path.stem

    try:
        importlib.import_module(module_name)
        console.print("[bold green]✅ Validation Successful![/bold green]")
        console.print(f"Tool(s) in '{file_path.name}' registered without errors.")
    except Exception as e:
        console.print("[bold red]❌ Validation Failed![/bold red]")
        console.print(f"An error occurred while trying to register the tool:")
        console.print(f"[red]{type(e).__name__}: {e}[/red]")
        raise typer.Exit(code=1)
    finally:
        # Clean up the path
        if str(module_dir) in sys.path:
            sys.path.remove(str(module_dir))


def _to_pascal_case(snake_str: str) -> str:
    return "".join(word.capitalize() for word in snake_str.split("_"))


@app.command(name="new-tool")
def new_tool(
        name: Annotated[
            str,
            typer.Option(
                prompt=True, help="The callable name of the tool (e.g., 'get_weather')."
            ),
        ],
        description: Annotated[
            str,
            typer.Option(
                prompt=True, help="A short, one-sentence description of the tool."
            ),
        ],
        category: Annotated[
            str,
            typer.Option(
                prompt=True,
                default="custom",
                help="A high-level category (e.g., 'network', 'file').",
            ),
        ],
        is_safe: Annotated[
            bool,
            typer.Option(
                prompt=True, help="Is this tool safe to run without user confirmation?"
            ),
        ] = True,
) -> None:
    """
    Creates a new boilerplate tool file in the 'plugins/' directory.
    """
    console.print(f"⚙️  Scaffolding new tool: [bold cyan]{name}[/bold cyan]")

    plugins_dir = Path("plugins")
    plugins_dir.mkdir(exist_ok=True)

    (plugins_dir / "__init__.py").touch(exist_ok=True)

    file_path = plugins_dir / f"{name}.py"
    if file_path.exists():
        console.print(f"[bold red]Error:[/bold red] File '{file_path}' already exists.")
        raise typer.Exit(code=1)

    class_name = f"{_to_pascal_case(name)}Input"

    content = f"""# plugins/{name}.py
from pydantic import BaseModel, Field
from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

logger = setup_logger(__name__)


class {class_name}(BaseModel):
    \"\"\"Input model for the {name} tool.

    :ivar example_arg: An example argument for your tool.
    :vartype example_arg: str
    \"\"\"
    example_arg: str = Field(..., description="An example argument for your tool.")


@register_tool(
    name="{name}",
    input_model={class_name},
    description="{description}",
    category="{category}",
    tags=["custom", "{name}"],
    safe_mode={is_safe}
)
def {name}(input_data: {class_name}) -> str:
    \"\"\"{description}

    :param input_data: The validated input data for the tool.
    :type input_data: {class_name}
    :return: A string containing the result of the tool's execution.
    :rtype: str
    \"\"\"
    logger.info(f"Executing tool: {name}")

    # --- YOUR TOOL LOGIC GOES HERE ---
    result = f"Tool '{{name}}' executed with arg: {{input_data.example_arg}}"
    # ---------------------------------

    return result
"""

    try:
        file_path.write_text(content, encoding="utf-8")
        console.print(
            f"[bold green]✅ Success![/bold green] New tool created at: [bold cyan]{file_path}[/bold cyan]"
        )
        console.print("You can now edit this file to implement your tool's logic.")
    except IOError as e:
        console.print(
            f"[bold red]Error:[/bold red] Could not write to file '{file_path}': {e}"
        )
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()