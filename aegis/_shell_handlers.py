# aegis/_shell_handlers.py
"""
Handler functions for the AegisShell (cmd2) commands.
This file is separated to keep the main shell.py file clean and focused on command parsing.
"""
import asyncio
import importlib
import json
import os
import shutil
import sys
import uuid
from pathlib import Path

import cmd2
import requests
import yaml
from langfuse import Langfuse
from langgraph.pregel import GraphInterrupt
from rich.json import JSON
from rich.markdown import Markdown
from rich.table import Table

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState
from aegis.registry import TOOL_REGISTRY
from aegis.schemas.agent import AgentConfig, AgentGraphConfig
from aegis.schemas.launch import LaunchRequest
from aegis.utils.backend_loader import get_backend_config
from aegis.utils.cli_helpers import (
    create_new_tool,
    validate_all_configs,
    validate_tool_file,
)
from aegis.utils.config_loader import load_agent_config
from aegis.utils.log_sinks import task_id_context


# --- Task Handlers ---


async def _task_run_handler(self: cmd2.Cmd, args):
    """Handles the 'task run' sub-command."""
    task_file: Path = args.task_file
    if not task_file.is_file():
        self.perror(f"ERROR: Task file not found at '{task_file}'")
        return

    self.poutput(
        f"📄 Loading task from: {cmd2.ansi.style(str(task_file), cyan=True, bold=True)}"
    )
    try:
        payload_data = yaml.safe_load(task_file.read_text())

        if self.session_preset and not payload_data.get("config"):
            payload_data["config"] = self.session_preset
            self.pfeedback(f"Using session default preset: {self.session_preset}")
        if self.session_backend and not (payload_data.get("execution") or {}).get(
            "backend_profile"
        ):
            if "execution" not in payload_data:
                payload_data["execution"] = {}
            payload_data["execution"]["backend_profile"] = self.session_backend
            self.pfeedback(f"Using session default backend: {self.session_backend}")

        launch_payload = LaunchRequest.model_validate(payload_data)
    except (yaml.YAMLError, ValueError, Exception) as e:
        self.perror(f"ERROR: Failed to parse or validate task file: {e}")
        return

    self.poutput(
        f"🚀 Launching task: {cmd2.ansi.style(launch_payload.task.prompt, magenta=True, bold=True)}"
    )
    await self._execute_graph(launch_payload)


async def _task_resume_handler(self: cmd2.Cmd, args):
    """Handles the 'task resume' sub-command."""
    task_id = args.task_id
    self.poutput(f"▶️  Attempting to resume task: {cmd2.ansi.style(task_id, cyan=True)}")
    feedback = self.read_input("Provide your feedback for the agent > ")

    try:
        response = requests.post(
            "http://localhost:8000/api/resume",
            json={"task_id": task_id, "human_feedback": feedback},
        )
        response.raise_for_status()
        result = response.json()
        self.poutput(
            cmd2.ansi.style("✅ Task resumed and completed successfully.", green=True)
        )
        self.poutput(f"\n{cmd2.ansi.style('Final Summary:', bold=True)}")
        self.console.print(Markdown(result.get("summary", "No summary provided.")))
    except requests.exceptions.RequestException as e:
        self.perror(f"ERROR: Failed to call resume API: {e}")
    except Exception as e:
        self.perror(f"An unexpected error occurred during resumption: {e}")


# --- Tool Handlers ---


def _tool_list_handler(self: cmd2.Cmd):
    table = Table(title="🛠️ AEGIS Registered Tools", expand=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Category", style="magenta")
    table.add_column("Description", style="white")
    table.add_column("Safe Mode", style="yellow")
    if not TOOL_REGISTRY:
        self.pwarning("No tools are registered.")
    else:
        for name, tool in sorted(TOOL_REGISTRY.items()):
            safe_str = "✅" if tool.safe_mode else "❌"
            table.add_row(name, tool.category or "N/A", tool.description, safe_str)
        self.console.print(table)


def _tool_validate_handler(self: cmd2.Cmd, args):
    self.poutput(
        f"🔎 Validating tool file: {cmd2.ansi.style(str(args.file_path), cyan=True, bold=True)}"
    )
    try:
        validate_tool_file(args.file_path)
        self.poutput(
            cmd2.ansi.style("✅ Validation Successful!", green=True, bold=True)
        )
    except Exception as e:
        self.perror(f"❌ Validation Failed: {e}")


def _tool_new_handler(self: cmd2.Cmd):
    self.poutput("⚙️ Scaffolding new tool...")
    try:
        name = self.read_input("Tool Name (e.g., 'get_weather') > ")
        description = self.read_input("Description > ")
        category = self.read_input("Category (e.g., 'network') > ") or "custom"
        is_safe_str = self.read_input("Is this tool safe? (yes/no) > ") or "yes"

        if not name or not description:
            self.perror("Tool name and description cannot be empty.")
            return

        file_path = create_new_tool(
            name, description, category, is_safe_str.lower().startswith("y")
        )
        self.poutput(
            cmd2.ansi.style(
                f"✅ Success! New tool created at: {file_path}", green=True, bold=True
            )
        )
    except (FileExistsError, Exception) as e:
        self.perror(f"ERROR: {e}")


def _tool_view_handler(self: cmd2.Cmd, args):
    tool = TOOL_REGISTRY.get(args.tool_name)
    if not tool:
        self.perror(f"Tool '{args.tool_name}' not found.")
        return
    self.poutput(
        f"--- Details for Tool: {cmd2.ansi.style(tool.name, cyan=True, bold=True)} ---"
    )
    self.poutput(f"Description: {tool.description}")
    self.poutput(f"Category: {tool.category or 'N/A'}")
    self.poutput(f"Tags: {', '.join(tool.tags)}")
    self.poutput(f"Safe Mode: {'✅' if tool.safe_mode else '❌'}")
    self.poutput("Input Schema:")
    self.console.print(JSON(json.dumps(tool.input_model.model_json_schema())))


# --- Config Handlers ---


def _config_validate_handler(self: cmd2.Cmd):
    self.poutput(
        cmd2.ansi.style("--- AEGIS Configuration Validator ---", blue=True, bold=True)
    )
    results = validate_all_configs()
    errors_found = 0
    for res in results:
        if res["status"] == "OK":
            self.poutput(
                f"🔍 Validating {cmd2.ansi.style(res['name'], cyan=True)}... {cmd2.ansi.style('✅ OK', green=True)}"
            )
        else:
            self.poutput(
                f"🔍 Validating {cmd2.ansi.style(res['name'], cyan=True)}... {cmd2.ansi.style('❌ FAILED', red=True, bold=True)}"
            )
            self.poutput(
                f"   {cmd2.ansi.style(f'└─ Reason: ' + {res['reason']}, red=True)}"
            )
            errors_found += 1

    self.poutput(cmd2.ansi.style("---", blue=True))
    if errors_found == 0:
        self.poutput(
            cmd2.ansi.style(
                "✅ All configurations validated successfully!", green=True, bold=True
            )
        )
    else:
        self.perror(f"❌ Found {errors_found} configuration error(s).")


def _config_view_handler(self: cmd2.Cmd, args):
    safelist = ["config.yaml", "backends.yaml", "machines.yaml", "models.yaml"]
    if args.filename not in safelist:
        self.perror(
            f"Cannot view '{args.filename}'. Only safelisted files are viewable."
        )
        return
    file_path = Path(args.filename)
    if not file_path.is_file():
        self.perror(f"File not found: {args.filename}")
        return
    self.poutput(f"--- Contents of {args.filename} ---")
    self.poutput(file_path.read_text())


def _config_edit_handler(self: cmd2.Cmd, args):
    safelist = ["config.yaml", "backends.yaml", "machines.yaml", "models.yaml"]
    if args.filename not in safelist:
        self.perror(
            f"Cannot edit '{args.filename}'. Only safelisted files are editable."
        )
        return
    editor = os.getenv("EDITOR", "vim")
    os.system(f"{editor} {args.filename}")


# --- Artifact Handlers ---


def _list_artifacts_handler(self: cmd2.Cmd):
    reports_dir = Path("reports")
    if not reports_dir.is_dir():
        self.pwarning("Reports directory not found.")
        return

    table = Table(title="📦 Task Artifacts", expand=True)
    table.add_column("Task ID", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Prompt", style="yellow")

    for task_dir in sorted(reports_dir.iterdir()):
        if task_dir.is_dir():
            prov_path = task_dir / "provenance.json"
            status, prompt = "UNKNOWN", ""
            if prov_path.is_file():
                try:
                    data = json.loads(prov_path.read_text())
                    status = data.get("final_status", "UNKNOWN")
                    prompt = data.get("task_prompt", "")
                except Exception:
                    pass
            table.add_row(
                task_dir.name,
                status,
                (prompt[:75] + "...") if len(prompt) > 75 else prompt,
            )
    self.console.print(table)


def _artifact_view_handler(self: cmd2.Cmd, args):
    task_dir = Path("reports") / args.task_id
    summary_path = task_dir / "summary.md"
    prov_path = task_dir / "provenance.json"

    if not task_dir.is_dir():
        self.perror(f"Artifacts for task '{args.task_id}' not found.")
        return

    if summary_path.is_file():
        self.poutput(f"--- Summary for {args.task_id} ---")
        self.console.print(Markdown(summary_path.read_text()))
    else:
        self.pwarning("No summary found for this task.")

    if prov_path.is_file():
        self.poutput(f"\n--- Provenance for {args.task_id} ---")
        self.console.print(JSON(prov_path.read_text()))
    else:
        self.pwarning("No provenance report found for this task.")


def _artifact_delete_handler(self: cmd2.Cmd, args):
    task_dir = Path("reports") / args.task_id
    if not task_dir.is_dir():
        self.perror(f"Artifacts for task '{args.task_id}' not found.")
        return

    if (
        self.read_input(
            f"Are you sure you want to delete all artifacts for task '{args.task_id}'? [y/N] > "
        ).lower()
        == "y"
    ):
        try:
            shutil.rmtree(task_dir)
            self.poutput(cmd2.ansi.style("✅ Artifacts deleted.", green=True))
        except Exception as e:
            self.perror(f"Failed to delete artifacts: {e}")
    else:
        self.poutput("Deletion cancelled.")


# --- Preset Handlers ---


def _list_presets_handler(self: cmd2.Cmd):
    presets_dir = Path("presets")
    if not presets_dir.is_dir():
        self.pwarning("Presets directory not found.")
        return

    table = Table(title="🧠 Available Agent Presets", expand=True)
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Description", style="yellow")

    for preset_file in sorted(presets_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(preset_file.read_text())
            table.add_row(
                preset_file.stem, data.get("name", ""), data.get("description", "")
            )
        except Exception:
            table.add_row(preset_file.stem, "N/A", "[Error reading file]")
    self.console.print(table)


def _preset_view_handler(self: cmd2.Cmd, args):
    preset_path = Path("presets") / f"{args.preset_id}.yaml"
    if not preset_path.is_file():
        self.perror(f"Preset '{args.preset_id}' not found.")
        return
    self.poutput(f"--- Contents of {preset_path.name} ---")
    self.poutput(preset_path.read_text())


def _preset_delete_handler(self: cmd2.Cmd, args):
    preset_path = Path("presets") / f"{args.preset_id}.yaml"
    if not preset_path.is_file():
        self.perror(f"Preset '{args.preset_id}' not found.")
        return
    if (
        self.read_input(
            f"Are you sure you want to delete preset '{args.preset_id}'? [y/N] > "
        ).lower()
        == "y"
    ):
        try:
            preset_path.unlink()
            self.poutput(cmd2.ansi.style("✅ Preset deleted.", green=True))
        except Exception as e:
            self.perror(f"Failed to delete preset: {e}")
    else:
        self.poutput("Deletion cancelled.")


# --- Eval Handlers ---


async def _eval_run_handler(self: cmd2.Cmd, args):
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


def _eval_list_datasets_handler(self: cmd2.Cmd):
    try:
        langfuse = Langfuse()
        datasets = langfuse.get_datasets()
        table = Table(title="📊 Available LangFuse Datasets", expand=True)
        table.add_column("Name", style="cyan")
        table.add_column("Items", style="white")
        for dataset in datasets:
            table.add_row(dataset.name, str(len(dataset.items)))
        self.console.print(table)
    except Exception as e:
        self.perror(f"Failed to fetch datasets from LangFuse: {e}")


def _eval_view_dataset_handler(self: cmd2.Cmd, args):
    try:
        langfuse = Langfuse()
        dataset = langfuse.get_dataset(name=args.dataset_name)
        self.poutput(
            f"--- Items in Dataset: {cmd2.ansi.style(dataset.name, cyan=True)} ---"
        )
        for item in dataset.items:
            prompt = (item.input or {}).get("task", {}).get("prompt", "N/A")
            self.poutput(f"- Item ID: {item.id}")
            self.poutput(
                f"  Prompt: {(prompt[:100] + '...') if len(prompt) > 100 else prompt}"
            )
            self.poutput(f"  Expected Output: {item.expected_output}")
    except Exception as e:
        self.perror(f"Failed to fetch dataset '{args.dataset_name}': {e}")


# --- Backend Handlers ---


def _backend_list_handler(self: cmd2.Cmd):
    try:
        backends_path = Path("backends.yaml")
        if not backends_path.is_file():
            self.pwarning("backends.yaml not found.")
            return

        table = Table(title="🔌 Available Backend Profiles", expand=True)
        table.add_column("Profile Name", style="cyan")
        table.add_column("Type", style="white")

        backend_profiles = yaml.safe_load(backends_path.read_text()).get("backends", [])
        for profile in backend_profiles:
            table.add_row(
                profile.get("profile_name", "N/A"), profile.get("type", "N/A")
            )
        self.console.print(table)
    except Exception as e:
        self.perror(f"Could not read backends.yaml: {e}")


# --- Session Handlers ---


def _session_set_handler(self: cmd2.Cmd, args):
    if args.key == "backend":
        self.session_backend = args.value
        self.poutput(
            f"Session default backend set to: {cmd2.ansi.style(args.value, cyan=True)}"
        )
    elif args.key == "preset":
        self.session_preset = args.value
        self.poutput(
            f"Session default preset set to: {cmd2.ansi.style(args.value, cyan=True)}"
        )


def _session_view_handler(self: cmd2.Cmd):
    self.poutput("--- Current Session Defaults ---")
    self.poutput(
        f"Backend: {cmd2.ansi.style(self.session_backend or 'Not Set', cyan=True)}"
    )
    self.poutput(
        f"Preset: {cmd2.ansi.style(self.session_preset or 'Not Set', cyan=True)}"
    )


# --- Core Graph Execution Logic ---


async def _execute_graph(self: cmd2.Cmd, payload: LaunchRequest):
    task_id = payload.task.task_id or str(uuid.uuid4())
    task_id_context.set(task_id)

    try:
        preset_config = load_agent_config(
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

        self.poutput(
            f"\n{cmd2.ansi.style('--- Agent Execution Starting ---', yellow=True)}"
        )
        final_state_dict = await agent_graph.ainvoke(
            initial_state.model_dump(), config=invocation_config
        )
        self.poutput(
            f"\n{cmd2.ansi.style('--- Agent Execution Complete ---', green=True)}"
        )
        final_state = TaskState(**final_state_dict)
        self.poutput(f"\n{cmd2.ansi.style('Final Summary:', bold=True)}")
        self.console.print(
            Markdown(final_state.final_summary or "[No summary was generated]")
        )

    except GraphInterrupt:
        self.poutput(
            f"\n{cmd2.ansi.style('⏸️ TASK PAUSED:', yellow=True, bold=True)} Agent has paused for human input."
        )
        self.poutput("To resume, use the 'task resume <task_id>' command.")


# --- Tab Completion Choice Providers ---


def _provide_tool_choices(self):
    return sorted(list(TOOL_REGISTRY.keys()))


def _provide_config_choices(self):
    return ["config.yaml", "backends.yaml", "machines.yaml", "models.yaml"]


def _provide_artifact_choices(self):
    reports_dir = Path("reports")
    if not reports_dir.is_dir():
        return []
    return sorted([d.name for d in reports_dir.iterdir() if d.is_dir()])


def _provide_preset_choices(self):
    presets_dir = Path("presets")
    if not presets_dir.is_dir():
        return []
    return sorted([f.stem for f in presets_dir.glob("*.yaml")])


def _provide_backend_choices(self):
    try:
        backends_path = Path("backends.yaml")
        if not backends_path.is_file():
            return []
        backend_profiles = yaml.safe_load(backends_path.read_text()).get("backends", [])
        return sorted(
            [p.get("profile_name") for p in backend_profiles if p.get("profile_name")]
        )
    except Exception:
        return []


def _provide_dataset_choices(self):
    try:
        langfuse = Langfuse()
        datasets = langfuse.get_datasets()
        return sorted([d.name for d in datasets])
    except Exception:
        return []


def _session_set_value_completer(self, text, line, begidx, endidx):
    """Context-aware completer for `session set <key> <value>`."""
    try:
        tokens = line.split()
        if len(tokens) > 2:
            key = tokens[2]
            if key == "backend":
                return [p for p in _provide_backend_choices(self) if p.startswith(text)]
            elif key == "preset":
                return [p for p in _provide_preset_choices(self) if p.startswith(text)]
    except Exception:
        pass
    return []
