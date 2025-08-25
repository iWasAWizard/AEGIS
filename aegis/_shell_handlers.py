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
import stat
import sys
import uuid
from pathlib import Path
import argparse
from unittest.mock import patch, AsyncMock

import cmd2
import yaml
from rich.json import JSON
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from aegis.agents.agent_graph import AgentGraph
from aegis.agents.task_state import TaskState
from aegis.exceptions import AegisError, ToolExecutionError
from aegis.providers.replay_provider import ReplayProvider
from aegis.registry import TOOL_REGISTRY
from aegis.schemas.agent import AgentConfig, AgentGraphConfig
from aegis.schemas.launch import LaunchRequest
from aegis.schemas.task import TaskRequest
from aegis.utils.backend_loader import get_backend_config
from aegis.utils.cli_helpers import (
    create_new_tool,
    validate_all_configs,
    validate_tool_file,
)
from aegis.utils.config_loader import load_agent_config
from aegis.utils.log_sinks import task_id_context
from aegis.utils.memory_indexer import update_memory_index
from aegis.utils.tool_loader import import_all_tools
from aegis.utils.dryrun import dry_run
from aegis.registry import TOOL_REGISTRY, ensure_discovered
from aegis.utils.tool_loader import import_all_tools
import cmd2


def _ensure_tools_loaded(self: cmd2.Cmd):
    """Lazy, race-free tool discovery. Safe to call many times."""
    if getattr(self, "tools_loaded", False):
        return
    # ensure_discovered runs importer only once per process
    ensure_discovered(import_all_tools)
    self.poutput(
        cmd2.ansi.style(
            f"✅ Tool registry loaded with {len(TOOL_REGISTRY)} tools.", fg="green"
        )
    )
    self.tools_loaded = True


def _print_failure_details(self, report: dict, task_id: str) -> None:
    """Pretty-print a concise failure summary from an agent provenance report.

    Parameters
    ----------
    self : AegisShell
        The shell instance for output helpers.
    report : dict
        Parsed JSON provenance report for the task.
    task_id : str
        The task identifier.
    """
    try:
        status = report.get("final_status", "UNKNOWN")
        thought = report.get("last_plan", {}).get("thought") or report.get(
            "latest_plan", {}
        ).get("thought")
        tool = report.get("last_plan", {}).get("tool_name") or report.get(
            "latest_plan", {}
        ).get("tool_name")
        error = report.get("error") or report.get("last_error")
        observation = report.get("last_observation") or report.get("observation")

        self.poutput(
            f"  {cmd2.ansi.style('FAIL:', fg='red', bold=True)} Agent reported status: {status}"
        )
        if tool:
            self.poutput(f"  Tool: {tool}")
        if thought:
            self.poutput(f"  Thought: {thought}")
        if observation:
            trimmed = observation[:500]
            suffix = "…" if observation and len(observation) > 500 else ""
            self.poutput(f"  Observation: {trimmed}{suffix}")
        if error:
            self.perror(f"  Error: {error}")
        self.poutput(
            f"  See provenance: .aegis/{task_id}/provenance.jsonl (if enabled)"
        )
    except Exception as e:
        self.perror(f"  FAIL: Unable to render failure details: {e}")


# --- Task Handlers ---


def _task_run_handler(self: cmd2.Cmd, args):
    """Handles the 'task run' sub-command."""
    asyncio.run(_async_task_run_handler(self, args))


async def _async_task_run_handler(self: cmd2.Cmd, args):
    if not args.task_identifier or args.task_identifier == "help":
        self.do_help("task run")
        return

    _ensure_tools_loaded(self)
    task_identifier: str = args.task_identifier
    task_file = Path(task_identifier)
    payload_data = {}

    if task_file.is_file():
        self.poutput(
            f"📄 Loading task from file: {cmd2.ansi.style(str(task_file), fg='cyan', bold=True)}"
        )
        try:
            payload_data = yaml.safe_load(task_file.read_text())
        except (yaml.YAMLError, Exception) as e:
            self.perror(f"ERROR: Failed to parse task file: {e}")
            return
    else:
        self.poutput(
            f"🚀 Running task from direct prompt: {cmd2.ansi.style(task_identifier, fg='magenta', bold=True)}"
        )
        payload_data = {"task": {"prompt": task_identifier}}

    try:
        # Apply session defaults for preset and backend if not specified
        if self.session_preset and not payload_data.get("config"):
            payload_data["config"] = self.session_preset
            self.pfeedback(f"Using session default preset: '{self.session_preset}'")
        if self.session_backend and not (payload_data.get("execution") or {}).get(
            "backend_profile"
        ):
            if "execution" not in payload_data:
                payload_data["execution"] = {}
            payload_data["execution"]["backend_profile"] = self.session_backend
            self.pfeedback(f"Using session default backend: '{self.session_backend}'")

        # Fallback to 'default' preset if none is specified at all
        if not payload_data.get("config"):
            payload_data["config"] = "default"
            self.pfeedback("Using system default preset: 'default'")

        launch_payload = LaunchRequest.model_validate(payload_data)
    except (ValueError, Exception) as e:
        self.perror(f"ERROR: Failed to validate task configuration: {e}")
        return

    await self._execute_graph(launch_payload)


def _task_resume_handler(self: cmd2.Cmd, args):
    """Handles the 'task resume' sub-command for the CLI."""
    asyncio.run(_async_task_resume_handler(self, args))


async def _async_task_resume_handler(self: cmd2.Cmd, args):
    if not args.task_id or args.task_id == "help":
        self.do_help("task resume")
        return

    _ensure_tools_loaded(self)
    task_id = args.task_id
    self.poutput(f"▶️  Attempting to resume task: {cmd2.ansi.style(task_id, fg='cyan')}")

    interrupted_session = self.interrupted_tasks.pop(task_id, None)
    if not interrupted_session:
        self.perror(
            f"ERROR: Paused task with ID '{task_id}' not found in this shell session."
        )
        return

    feedback = self.read_input("Provide your feedback for the agent > ")

    agent_graph = interrupted_session["graph"]
    saved_state_dict = interrupted_session["state"]
    saved_state_dict["human_feedback"] = feedback

    try:
        self.poutput(
            f"\n{cmd2.ansi.style('--- Agent Execution Resuming ---', fg='yellow')}"
        )
        final_state_dict = await agent_graph.ainvoke(saved_state_dict)
        final_state = TaskState(**final_state_dict)
    except Exception as e:
        self.perror(f"An unexpected error occurred during resumption: {e}")


# --- Tool Handlers ---


def _tool_list_handler(self: cmd2.Cmd, args):
    from inspect import getdoc

    _ensure_tools_loaded(self)

    # JSON mode: structured and script-friendly
    if getattr(args, "json", False):
        tools_data = []
        for name, entry in sorted(TOOL_REGISTRY.items()):
            func = entry.func
            tools_data.append(
                {
                    "name": entry.name,
                    "timeout": entry.timeout,
                    "module": getattr(func, "__module__", "unknown"),
                    "qualname": getattr(
                        func, "__qualname__", getattr(func, "__name__", "func")
                    ),
                    "input_model": entry.input_model.__name__,
                    "schema": entry.input_model.model_json_schema(),
                    "summary": (
                        (getdoc(func) or "").strip().splitlines()[0]
                        if getdoc(func)
                        else ""
                    ),
                }
            )
        self.poutput(json.dumps(tools_data, indent=2))
        return

    # Pretty table mode
    table = Table(title="🛠️  AEGIS Registered Tools", expand=True)
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Timeout", style="magenta", no_wrap=True)
    table.add_column("Module", style="white")
    table.add_column("Summary", style="yellow")

    if not TOOL_REGISTRY:
        self.pwarning("No tools are registered.")
    else:
        for name, entry in sorted(TOOL_REGISTRY.items()):
            func = entry.func
            mod = getattr(func, "__module__", "unknown")
            summary = (
                (getdoc(func) or "").strip().splitlines()[0] if getdoc(func) else ""
            )
            table.add_row(entry.name, str(entry.timeout or "—"), mod, summary or "—")
        self.console.print(table)


def _tool_validate_handler(self: cmd2.Cmd, args):
    if not args.file_path or args.file_path == "help":
        self.do_help("tool validate")
        return
    self.poutput(
        f"🔎 Validating tool file: {cmd2.ansi.style(str(args.file_path), fg='cyan', bold=True)}"
    )
    try:
        validate_tool_file(args.file_path)
        self.poutput(
            cmd2.ansi.style("✅ Validation Successful!", fg="green", bold=True)
        )
    except Exception as e:
        self.perror(f"❌ Validation Failed: {e}")


def _tool_new_handler(self: cmd2.Cmd, args):
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
                f"✅ Success! New tool created at: {file_path}", fg="green", bold=True
            )
        )
    except (FileExistsError, Exception) as e:
        self.perror(f"ERROR: {e}")


def _tool_view_handler(self: cmd2.Cmd, args):
    if not args.tool_name or args.tool_name == "help":
        self.do_help("tool view")
        return

    _ensure_tools_loaded(self)
    entry = TOOL_REGISTRY.get(args.tool_name)
    if not entry:
        self.perror(f"Tool '{args.tool_name}' not found.")
        return

    func = entry.func
    doc = (func.__doc__ or "").strip()
    module = getattr(func, "__module__", "unknown")
    qualname = getattr(func, "__qualname__", getattr(func, "__name__", "func"))
    timeout = entry.timeout or "—"

    self.poutput(
        f"--- Details for Tool: {cmd2.ansi.style(entry.name, fg='cyan', bold=True)} ---"
    )
    self.poutput(f"Module: {module}")
    self.poutput(f"Callable: {qualname}")
    self.poutput(f"Timeout: {timeout}s")
    if doc:
        self.poutput("\nSummary:")
        self.console.print(Markdown(doc))

    try:
        schema = entry.input_model.model_json_schema()
        self.poutput("\nInput Schema:")
        self.console.print(JSON(json.dumps(schema, indent=2)))
    except Exception as e:
        self.pwarning(f"(Could not render input schema: {e})")


# --- Config Handlers ---


def _config_validate_handler(self: cmd2.Cmd, args):
    self.poutput(
        cmd2.ansi.style("--- AEGIS Configuration Validator ---", fg="blue", bold=True)
    )
    results = validate_all_configs()
    errors_found = 0
    for res in results:
        if res["status"] == "OK":
            self.poutput(
                f"🔍 Validating {cmd2.ansi.style(res['name'], fg='cyan')}... {cmd2.ansi.style('✅ OK', fg='green')}"
            )
        else:
            self.poutput(
                f"🔍 Validating {cmd2.ansi.style(res['name'], fg='cyan')}... {cmd2.ansi.style('❌ FAILED', fg='red', bold=True)}"
            )
            self.poutput(
                f"   {cmd2.ansi.style('└─ Reason: ' + res['reason'], fg='red')}"
            )
            errors_found += 1

    self.poutput(cmd2.ansi.style("---", fg="blue"))
    if errors_found == 0:
        self.poutput(
            cmd2.ansi.style(
                "✅ All configurations validated successfully!", fg="green", bold=True
            )
        )
    else:
        self.perror(f"❌ Found {errors_found} configuration error(s).")


def _config_view_handler(self: cmd2.Cmd, args):
    if not args.filename or args.filename == "help":
        self.do_help("config view")
        return
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
    if not args.filename or args.filename == "help":
        self.do_help("config edit")
        return
    safelist = ["config.yaml", "backends.yaml", "machines.yaml", "models.yaml"]
    if args.filename not in safelist:
        self.perror(
            f"Cannot edit '{args.filename}'. Only safelisted files are editable."
        )
        return
    editor = os.getenv("EDITOR", "vim")
    os.system(f"{editor} {args.filename}")


# --- Artifact Handlers ---


def _list_artifacts_handler(self: cmd2.Cmd, args):
    reports_dir = Path("reports")
    if not reports_dir.is_dir():
        self.pwarning("Reports directory not found.")
        return

    artifacts_data = []
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
            artifacts_data.append(
                {"task_id": task_dir.name, "status": status, "prompt": prompt}
            )

    if args.json:
        self.poutput(json.dumps(artifacts_data, indent=2))
        return

    table = Table(title="📦 Task Artifacts", expand=True)
    table.add_column("Task ID", style="cyan")
    table.add_column("Status", style="white")
    table.add_column("Prompt", style="yellow")
    for item in artifacts_data:
        prompt_summary = (
            (item["prompt"][:75] + "...")
            if len(item["prompt"]) > 75
            else item["prompt"]
        )
        table.add_row(item["task_id"], item["status"], prompt_summary)
    self.console.print(table)


def _artifact_view_handler(self: cmd2.Cmd, args):
    if not args.task_id or args.task_id == "help":
        self.do_help("artifact view")
        return
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
    if not args.task_id or args.task_id == "help":
        self.do_help("artifact delete")
        return
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
            self.poutput(cmd2.ansi.style("✅ Artifacts deleted.", fg="green"))
        except Exception as e:
            self.perror(f"Failed to delete artifacts: {e}")
    else:
        self.poutput("Deletion cancelled.")


# --- Preset Handlers ---


def _list_presets_handler(self: cmd2.Cmd, args):
    presets_dir = Path("presets")
    if not presets_dir.is_dir():
        self.pwarning("Presets directory not found.")
        return

    presets_data = []
    for preset_file in sorted(presets_dir.glob("*.yaml")):
        try:
            data = yaml.safe_load(preset_file.read_text())
            presets_data.append(
                {
                    "id": preset_file.stem,
                    "name": data.get("name", ""),
                    "description": data.get("description", ""),
                }
            )
        except Exception:
            presets_data.append(
                {
                    "id": preset_file.stem,
                    "name": "N/A",
                    "description": "[Error reading file]",
                }
            )

    if args.json:
        self.poutput(json.dumps(presets_data, indent=2))
        return

    table = Table(title="🧠 Available Agent Presets", expand=True)
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="white")
    table.add_column("Description", style="yellow")
    for item in presets_data:
        self.console.print  # no-op to satisfy linters if needed
        table.add_row(item["id"], item["name"], item["description"])
    self.console.print(table)


def _preset_view_handler(self: cmd2.Cmd, args):
    if not args.preset_id or args.preset_id == "help":
        self.do_help("preset view")
        return
    preset_path = Path("presets") / f"{args.preset_id}.yaml"
    if not preset_path.is_file():
        self.perror(f"Preset '{args.preset_id}' not found.")
        return
    self.poutput(f"--- Contents of {preset_path.name} ---")
    self.poutput(preset_path.read_text())


def _preset_new_handler(self: cmd2.Cmd, args):
    self.poutput("⚙️ Scaffolding new preset...")
    try:
        preset_id = self.read_input("Preset ID (e.g., 'my_agent') > ")
        if not preset_id or " " in preset_id:
            self.perror("Preset ID must be a single word.")
            return

        preset_path = Path("presets") / f"{preset_id}.yaml"
        if preset_path.exists():
            self.perror(f"Preset file '{preset_path}' already exists.")
            return

        name = (
            self.read_input(f"Preset Name (e.g., 'My Custom Agent') > ") or "My Agent"
        )
        description = self.read_input("Description > ") or "A new agent preset."

        default_content = Path("presets/default.yaml").read_text()
        new_content = (
            f'name: "{name}"\n' f'description: "{description}"\n' f"{default_content}"
        )

        preset_path.write_text(new_content)
        self.poutput(
            cmd2.ansi.style(
                f"✅ Success! New preset created at: {preset_path}",
                fg="green",
                bold=True,
            )
        )
    except Exception as e:
        self.perror(f"ERROR: {e}")


def _preset_delete_handler(self: cmd2.Cmd, args):
    if not args.preset_id or args.preset_id == "help":
        self.do_help("preset delete")
        return
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
            self.poutput(cmd2.ansi.style("✅ Preset deleted.", fg="green"))
        except Exception as e:
            self.perror(f"Failed to delete preset: {e}")
    else:
        self.poutput("Deletion cancelled.")


# --- Backend Handlers ---


def _backend_list_handler(self: cmd2.Cmd, args):
    try:
        backends_path = Path("backends.yaml")
        if not backends_path.is_file():
            self.pwarning("backends.yaml not found.")
            return

        backend_profiles_raw = yaml.safe_load(backends_path.read_text()).get(
            "backends", []
        )
        backend_profiles_data = [
            {"profile_name": p.get("profile_name", "N/A"), "type": p.get("type", "N/A")}
            for p in backend_profiles_raw
        ]

        if args.json:
            self.poutput(json.dumps(backend_profiles_data, indent=2))
            return

        table = Table(title="🔌 Available Backend Profiles", expand=True)
        table.add_column("Profile Name", style="cyan")
        table.add_column("Type", style="white")

        for profile in backend_profiles_data:
            table.add_row(profile["profile_name"], profile["type"])
        self.console.print(table)
    except Exception as e:
        self.perror(f"Could not read backends.yaml: {e}")


# --- Machine Handlers ---


def _machine_list_handler(self: cmd2.Cmd, args):
    try:
        machines_path = Path("machines.yaml")
        if not machines_path.is_file():
            self.pwarning("machines.yaml not found.")
            return

        machines = yaml.safe_load(machines_path.read_text()) or {}

        if args.json:
            self.poutput(json.dumps(machines, indent=2))
            return

        table = Table(title="🖥️  Available Machines", expand=True)
        table.add_column("Name", style="cyan")
        table.add_column("IP Address", style="white")
        table.add_column("Platform", style="yellow")
        table.add_column("Notes", style="white")

        for name, details in machines.items():
            table.add_row(
                name,
                details.get("ip", "N/A"),
                details.get("platform", "N/A"),
                details.get("notes", ""),
            )
        self.console.print(table)
    except Exception as e:
        self.perror(f"Could not read machines.yaml: {e}")


# --- Session Handlers ---


def _session_set_handler(app, args):
    key = (args.key or "").strip()
    val = (args.value or "").strip()

    if not key:
        app.do_help("session set")
        return

    if key == "dryrun":
        v = val.lower()
        if v in {"on", "true", "1", "yes"}:
            dry_run.enabled = True
            app.poutput("Dry-run mode ENABLED")
        elif v in {"off", "false", "0", "no"}:
            dry_run.enabled = False
            app.poutput("Dry-run mode DISABLED")
        else:
            app.perror("Expected: on|off")
        return

    if key == "backend":
        if not val:
            app.perror("Expected a backend profile name.")
            return
        choices = _provide_backend_choices(app)
        if choices and val not in choices:
            app.pwarning(
                f"Backend '{val}' not found in backends.yaml. "
                f"Available: {', '.join(choices) or '[none]'}"
            )
        app.session_backend = val
        app.poutput(f"Session backend set to: {cmd2.ansi.style(val, fg='cyan')}")
        return

    if key == "preset":
        if not val:
            app.perror("Expected a preset id (filename without .yaml).")
            return
        choices = _provide_preset_choices(app)
        if choices and val not in choices:
            app.pwarning(
                f"Preset '{val}' not found under presets/. "
                f"Available: {', '.join(choices) or '[none]'}"
            )
        app.session_preset = val
        app.poutput(f"Session preset set to: {cmd2.ansi.style(val, fg='cyan')}")
        return

    app.perror(f"Unknown session key: {key}")


def _session_view_handler(self: cmd2.Cmd, args):
    self.poutput("--- Current Session Defaults ---")
    self.poutput(
        f"Backend: {cmd2.ansi.style(self.session_backend or 'Not Set', fg='cyan')}"
    )
    self.poutput(
        f"Preset: {cmd2.ansi.style(self.session_preset or 'Not Set', fg='cyan')}"
    )


# --- Test Handlers (from run_regression_tests.py) ---


def _prime_agent_memory(self):
    """Creates a seed log file and runs the indexer."""
    self.poutput("🧠 Priming agent long-term memory for RAG tests...")
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    seed_log_path = logs_dir / "rag_seed.jsonl"
    seed_data = {
        "event_type": "ToolEnd",
        "message": "Tool `check_remote_file_exists` executed successfully.",
    }
    try:
        with seed_log_path.open("w") as f:
            f.write(json.dumps(seed_data) + "\n")
        update_memory_index()
        self.pfeedback("   - Memory indexing complete.")
    except Exception as e:
        self.perror(f"  FAIL: Could not prime agent memory: {e}")
        return False
    return True


def _test_run_handler(self, args):
    """Handles the 'test run' sub-command."""
    asyncio.run(_async_test_run_handler(self, args))


async def _async_test_run_handler(self, args):
    if args.test_name == "help":
        self.do_help("test run")
        return
    _ensure_tools_loaded(self)
    if not _prime_agent_memory(self):
        return

    regression_dir = Path("tests/regression")
    test_files = []
    if args.test_name:
        target_file = regression_dir / f"test_{args.test_name}.yaml"
        if not target_file.exists():
            self.perror(f"Test file '{target_file.name}' not found.")
            return
        test_files = [target_file]
    else:
        test_files = sorted(regression_dir.glob("test_*.yaml"))

    self.poutput(f"Found {len(test_files)} test(s) to run.")
    results = {"passed": 0, "failed": 0}

    for test_file in test_files:
        passed = await _run_single_test(self, test_file)
        if passed:
            results["passed"] += 1
        else:
            results["failed"] += 1

    self.poutput("\n" + cmd2.ansi.style("--- Test Summary ---", bold=True))
    self.poutput(
        f"{cmd2.ansi.style('Passed:', fg='green', bold=True)} {results['passed']}"
    )
    self.poutput(
        f"{cmd2.ansi.style('Failed:', fg='red', bold=True)} {results['failed']}"
    )


async def _run_single_test(self, test_path: Path) -> bool:
    """Loads and executes a single regression test file."""
    self.poutput(
        f"▶️  Running test: {cmd2.ansi.style(test_path.name, fg='cyan', bold=True)}"
    )
    task_id = f"test-{test_path.stem}-{uuid.uuid4().hex[:6]}"
    task_id_context.set(task_id)

    try:
        payload_data = yaml.safe_load(test_path.read_text())
        payload_data.setdefault("task", {})["task_id"] = task_id
        launch_payload = LaunchRequest.model_validate(payload_data)
        await self._execute_graph(launch_payload)
    except (AegisError, Exception) as e:
        self.perror(f"  ERROR DURING EXECUTION: {e}")
        return False

    provenance_path = Path("reports") / task_id / "provenance.json"
    if not provenance_path.exists():
        self.perror(f"  FAIL: Provenance report not found at '{provenance_path}'")
        return False

    try:
        with provenance_path.open("r") as f:
            report = json.load(f)
        if report.get("final_status") == "SUCCESS":
            self.poutput(
                f"  {cmd2.ansi.style('PASS:', fg='green', bold=True)} Agent reported success."
            )
            return True
        else:
            _print_failure_details(self, report, task_id)
            return False
    except (IOError, json.JSONDecodeError) as e:
        self.perror(f"  FAIL: Could not read or parse provenance report: {e}")
        return False


def _test_list_handler(self: cmd2.Cmd, args):
    """Handles the 'test list' sub-command."""
    regression_dir = Path("tests/regression")
    test_files = sorted(regression_dir.glob("test_*.yaml"))
    if not test_files:
        self.pwarning("No regression tests found.")
        return

    tests_data = []
    for test_file in test_files:
        try:
            test_config = yaml.safe_load(test_file.read_text())
            prompt = test_config.get("task", {}).get("prompt", "N/A")
            tests_data.append(
                {"name": test_file.stem.replace("test_", ""), "prompt": prompt.strip()}
            )
        except yaml.YAMLError:
            tests_data.append(
                {
                    "name": test_file.stem.replace("test_", ""),
                    "prompt": "[Invalid YAML]",
                }
            )

    if args.json:
        self.poutput(json.dumps(tests_data, indent=2))
        return

    table = Table(title="Regression Test Suite", expand=True)
    table.add_column("Test Name", style="cyan", no_wrap=True)
    table.add_column("Description / Prompt", style="white")
    for item in tests_data:
        prompt_summary = (
            (item["prompt"][:100] + "...")
            if len(item["prompt"]) > 100
            else item["prompt"]
        )
        table.add_row(item["name"], prompt_summary)
    self.console.print(table)


def _test_replay_handler(self: cmd2.Cmd, args):
    """Handles the 'test replay' sub-command."""
    if not args.task_id or args.task_id == "help":
        self.do_help("test replay")
        return
    self.poutput(
        f"🔄 Replaying task: {cmd2.ansi.style(args.task_id, fg='cyan', bold=True)}"
    )
    # Placeholder for the actual replay logic
    self.poutput("   (Replay functionality not yet implemented.)")


# --- Core Graph Execution Logic ---


async def _execute_graph(self: cmd2.Cmd, payload: LaunchRequest):
    task_id = payload.task.task_id or str(uuid.uuid4())
    task_id_context.set(task_id)
    final_status = "UNKNOWN"
    final_state = None

    try:
        preset_config = load_agent_config(
            profile=payload.config if isinstance(payload.config, str) else None,
            raw_config=payload.config if isinstance(payload.config, dict) else None,
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

        self.poutput(
            f"\n{cmd2.ansi.style('--- Agent Execution Starting ---', fg='yellow')}"
        )
        final_state_dict = await agent_graph.ainvoke(initial_state.model_dump())
        final_state = TaskState(**final_state_dict)

        if (
            final_state.history
            and final_state.history[-1].plan.tool_name == "ask_human_for_input"
        ):
            final_status = "PAUSED"
            self.interrupted_tasks[task_id] = {
                "graph": agent_graph,
                "state": final_state.model_dump(),
                "preset_config": preset_config,
            }
        else:
            final_status = "COMPLETED"

    except Exception as e:
        final_status = "ERROR"
        self.perror(f"An unexpected error occurred during task execution: {e}")
    finally:
        if final_state:
            self.poutput(f"\n{cmd2.ansi.style('Final Summary:', bold=True)}")
            self.console.print(
                Markdown(final_state.final_summary or "[No summary was generated]")
            )
        summary_panel = Panel(
            f"[bold]Task ID:[/bold] {task_id}\n"
            f"[bold]Final Status:[/bold] {final_status}\n"
            f"[bold]Artifacts Path:[/bold] {cmd2.ansi.style(f'reports/{task_id}/', fg='cyan')}",
            title=f"[bold {cmd2.ansi.style('green', fg='green')}]Task Summary[/bold {cmd2.ansi.style('green', fg='green')}]",
            border_style="green",
            expand=False,
        )
        self.console.print(summary_panel)


# --- Tab Completion Choice Providers ---


def _provide_tool_choices(self):
    _ensure_tools_loaded(self)
    return sorted(list(TOOL_REGISTRY.keys()))


def _provide_config_choices(self):
    return ["config.yaml", "backends.yaml", "machines.yaml", "models.yaml"]


def _provide_artifact_choices(self):
    reports_dir = Path("reports")
    if not reports_dir.is_dir():
        return []
    return sorted([d.name for d in reports_dir.iterdir() if d.is_dir()])


def _provide_replay_choices(self):
    """Provides choices for task IDs that have a replay.jsonl file."""
    reports_dir = Path("reports")
    if not reports_dir.is_dir():
        return []
    replayable_tasks = []
    for task_dir in reports_dir.iterdir():
        if (task_dir / "replay.jsonl").is_file():
            replayable_tasks.append(task_dir.name)
    return sorted(replayable_tasks)


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


def _provide_test_choices(self):
    regression_dir = Path("tests/regression")
    if not regression_dir.is_dir():
        return []
    return [
        p.stem.replace("test_", "") for p in sorted(regression_dir.glob("test_*.yaml"))
    ]


def _provide_dataset_choices(self):
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
            elif key == "dryrun":
                return [v for v in ["on", "off"] if v.startswith(text.lower())]
    except Exception:
        pass
    return []
