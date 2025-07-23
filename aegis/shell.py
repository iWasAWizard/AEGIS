# aegis/shell.py
"""
An interactive shell interface for the AEGIS framework, built with cmd2.

This module provides a cohesive, line-oriented command processor for interacting
with the AEGIS agent, replacing the previous Typer-based CLI. It offers a more
fluid and persistent session for operators.
"""
import asyncio
import importlib
import sys
import uuid
from pathlib import Path

import cmd2
import yaml
from rich.console import Console
from rich.table import Table

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState
from aegis.exceptions import AegisError
from aegis.registry import TOOL_REGISTRY
from aegis.schemas.agent import AgentConfig, AgentGraphConfig
from aegis.schemas.launch import LaunchRequest
from aegis.utils.cli_helpers import create_new_tool, validate_all_configs
from aegis.utils.config_loader import load_agent_config
from aegis.utils.log_sinks import task_id_context
from aegis.utils.logger import setup_logger
from aegis.utils.tool_loader import import_all_tools


class AegisShell(cmd2.Cmd):
    """The main class for the AEGIS interactive shell."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt = cmd2.ansi.style("(aegis) > ", bold=True)
        self.intro = cmd2.ansi.style(
            "Welcome to the AEGIS Agentic Framework Shell. Type 'help' for a list of commands.",
            bold=True,
        )
        # Keep rich console for its excellent table formatting
        self.console = Console()

    def startup(self):
        """This method is called once at the start of the application."""
        self.poutput("Importing all available tools...")
        import_all_tools()
        self.poutput(
            cmd2.ansi.style(
                f"✅ Tool registry loaded with {len(TOOL_REGISTRY)} tools.", green=True
            )
        )

    # --- Argument Parsers ---
    run_task_parser = cmd2.Cmd2ArgumentParser()
    run_task_parser.add_argument(
        "task_file", type=Path, help="Path to the YAML file with the task request."
    )

    run_evals_parser = cmd2.Cmd2ArgumentParser()
    run_evals_parser.add_argument(
        "dataset_name", help="The name of the dataset in LangFuse to run."
    )
    run_evals_parser.add_argument(
        "--judge-model",
        default="openai_gpt4",
        help="The model profile for the judge LLM.",
    )

    validate_tool_parser = cmd2.Cmd2ArgumentParser()
    validate_tool_parser.add_argument(
        "file_path", type=Path, help="Path to the Python tool file to validate."
    )

    # --- Core Commands ---

    @cmd2.with_argparser(run_task_parser)
    async def do_run_task(self, args):
        """Runs a single agent task from a specified YAML file."""
        task_file: Path = args.task_file
        if not task_file.is_file():
            self.perror(f"ERROR: Task file not found at '{task_file}'")
            return

        self.poutput(
            f"📄 Loading task from: {cmd2.ansi.style(str(task_file), cyan=True, bold=True)}"
        )
        try:
            launch_payload = LaunchRequest.model_validate(
                yaml.safe_load(task_file.read_text())
            )
        except (yaml.YAMLError, ValueError) as e:
            self.perror(f"ERROR: Failed to parse or validate task file: {e}")
            return

        self.poutput(
            f"🚀 Launching task: {cmd2.ansi.style(launch_payload.task.prompt, magenta=True, bold=True)}"
        )

        try:
            await self._execute_graph(launch_payload)
        except AegisError as e:
            self.perror(f"\nAGENT FAILED: A critical error occurred during execution.")
            self.perror(f"Type: {e.__class__.__name__}")
            self.perror(f"Reason: {e}")
        except Exception as e:
            self.perror(f"\nUNEXPECTED FATAL ERROR: {e}")
            self.pfeedback(
                "An unexpected error occurred. See the full traceback above."
            )
        finally:
            self.poutput(
                f"\n{cmd2.ansi.style('--- Execution Finished ---', blue=True, bold=True)}"
            )

    async def _execute_graph(self, payload: LaunchRequest):
        """The core async logic for running the agent graph, adapted for cmd2."""
        task_id = payload.task.task_id or str(uuid.uuid4())
        task_id_context.set(task_id)

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
        graph_structure = AgentGraphConfig(**preset_config.model_dump())
        agent_graph = AgentGraph(graph_structure).build_graph()

        langfuse_handler = CallbackHandler()
        invocation_config = {
            "callbacks": [langfuse_handler],
            "metadata": {"user_id": "aegis-shell-user", "session_id": task_id},
        }

        self.poutput(f"\n{cmd2.ansi.style('--- Agent Execution Starting ---', yellow=True)}")
        try:
            final_state_dict = await agent_graph.ainvoke(
                initial_state.model_dump(), config=invocation_config
            )
            self.poutput(f"\n{cmd2.ansi.style('--- Agent Execution Complete ---', green=True)}")
            final_state = TaskState(**final_state_dict)
            self.poutput(f"\n{cmd2.ansi.style('Final Summary:', bold=True)}")
            self.poutput(final_state.final_summary or "[No summary was generated]")
        except GraphInterrupt:
            self.poutput(
                f"\n{cmd2.ansi.style('⏸️ TASK PAUSED:', yellow=True, bold=True)} Agent has paused for human input."
            )
            self.poutput(
                "To resume, you must use the API's /resume endpoint. Halting shell execution."
            )

    @cmd2.with_argparser(run_evals_parser)
    async def do_run_evals(self, args):
        """Runs an evaluation suite against a LangFuse dataset."""
        self.poutput(
            f"🧪 Starting evaluation run for dataset: {cmd2.ansi.style(args.dataset_name, cyan=True, bold=True)}"
        )
        try:
            from aegis.evaluation.eval_runner import main as run_eval_main

            await run_eval_main(args.dataset_name, args.judge_model)
        except ImportError as e:
            self.perror(f"ERROR: Failed to import evaluation module: {e}")
        except Exception as e:
            self.perror(f"EVALUATION FAILED: {e}")

    def do_list_tools(self, _):
        """Lists all registered tools available to the agent."""
        table = Table(title="🛠️ AEGIS Registered Tools")
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Category", style="magenta")
        table.add_column("Description", style="white")
        table.add_column("Safe Mode", style="yellow")

        if not TOOL_REGISTRY:
            self.pwarning("No tools are registered.")
            return

        for name, tool in sorted(TOOL_REGISTRY.items()):
            safe_str = "✅" if tool.safe_mode else "❌"
            table.add_row(name, tool.category or "N/A", tool.description, safe_str)

        self.console.print(table)

    def do_validate_config(self, _):
        """Proactively loads and validates all key configuration files."""
        self.poutput(
            cmd2.ansi.style(
                "--- AEGIS Configuration Validator ---", blue=True, bold=True
            )
        )
        results = validate_all_configs()
        errors_found = 0
        for res in results:
            if res["status"] == "OK":
                self.poutput(
                    f"🔍 Validating {cmd2.ansi.style(res['name'], cyan=True)}... {cmd2.ansi.style('✅ OK', green=True)}")
            else:
                self.poutput(
                    f"🔍 Validating {cmd2.ansi.style(res['name'], cyan=True)}... {cmd2.ansi.style('❌ FAILED', red=True, bold=True)}")
                self.poutput(f"   {cmd2.ansi.style(f'└─ Reason: ' + {res['reason']}, red=True)}")
                errors_found += 1

                self.poutput(cmd2.ansi.style("---", blue=True))
                if errors_found == 0:
                    self.poutput(
                        cmd2.ansi.style(
                            "✅ All configurations validated successfully!", green=True, bold=True
                        )
                    )
                else:
                    self.perror(f"❌ Found {errors_found} configuration error(s).") \
 \
                    @ cmd2.with_argparser(validate_tool_parser)

    def do_validate_tool(self, args):
        """Validates a single tool file by attempting to import it."""
        file_path: Path = args.file_path
        self.poutput(
            f"🔎 Validating tool file: {cmd2.ansi.style(str(file_path), cyan=True, bold=True)}"
        )

        module_dir = file_path.parent.resolve()
        if str(module_dir) not in sys.path:
            sys.path.insert(0, str(module_dir))

        module_name = file_path.stem

        try:
            importlib.import_module(module_name)
            self.poutput(
                cmd2.ansi.style("✅ Validation Successful!", green=True, bold=True)
            )
            self.poutput(f"Tool(s) in '{file_path.name}' registered without errors.")
        except Exception as e:
            self.perror("❌ Validation Failed!")
            self.perror(f"An error occurred while trying to register the tool:")
            self.perror(f"{type(e).__name__}: {e}")
        finally:
            if str(module_dir) in sys.path:
                sys.path.remove(str(module_dir))

    def do_new_tool(self, _):
        """Creates a new boilerplate tool file in the 'plugins/' directory."""
        self.poutput("⚙️ Scaffolding new tool...")
        try:
            name = self.read_input("Tool Name (e.g., 'get_weather') > ")
            description = self.read_input("Description > ")
            category = self.read_input("Category (e.g., 'network') > ") or "custom"
            is_safe_str = self.read_input("Is this tool safe? (yes/no) > ") or "yes"
            is_safe = is_safe_str.lower().startswith("y")

            if not name or not description:
                self.perror("Tool name and description cannot be empty.")
                return

            file_path = create_new_tool(name, description, category, is_safe)

            self.poutput(
                cmd2.ansi.style(
                    f"✅ Success! New tool created at: {file_path}", green=True, bold=True
                )
            )
        except (FileExistsError, Exception) as e:
            self.perror(f"ERROR: {e}")