# aegis/shell.py
"""
An interactive shell interface for the AEGIS framework, built with cmd2.

This module provides a cohesive, line-oriented command processor for interacting
with the AEGIS agent, using a noun-verb sub-command paradigm.
"""
import asyncio
from pathlib import Path

import cmd2
from rich.console import Console

from aegis.registry import TOOL_REGISTRY
from aegis.utils.tool_loader import import_all_tools


@cmd2.with_default_category("AEGIS Shell")
class AegisShell(cmd2.Cmd):
    """The main class for the AEGIS interactive shell."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The prompt is now a dynamic property, see below
        self.intro = cmd2.ansi.style(
            "Welcome to the AEGIS Agentic Framework Shell. Type 'help' for a list of commands.",
            bold=True,
        )
        self.console = Console()
        # Session-specific settings
        self.session_backend = None
        self.session_preset = None
        self.interrupted_tasks = {}
        self.tools_loaded = False  # Flag to ensure tools are loaded only once

    @property
    @cmd2.with_category("cmd2")
    def prompt(self) -> str:
        """A dynamic prompt that displays the current session context."""
        parts = ["(aegis"]
        if self.session_preset:
            parts.append(f"| preset:{self.session_preset}")
        if self.session_backend:
            parts.append(f"| backend:{self.session_backend}")
        parts.append(") > ")
        return cmd2.ansi.style(" ".join(parts), bold=True)

    def startup(self):
        """This method is called once at the start of the application."""
        # Tool loading is now deferred to when it's actually needed.
        self.poutput("AEGIS shell ready. Tools will be loaded on first use.")

    @cmd2.with_category("Session Commands")
    def do_exit(self, args):
        """Exit the AEGIS shell."""
        return True

    @cmd2.with_category("Session Commands")
    def do_quit(self, args):
        """Exit the AEGIS shell."""
        return self.do_exit(args)

    # --- Noun: task ---
    task_parser = cmd2.Cmd2ArgumentParser(description="Run and manage agent tasks.")
    task_subparsers = task_parser.add_subparsers(
        title="sub-commands", help="Task actions"
    )

    parser_run = task_subparsers.add_parser(
        "run",
        help="Run a task from a file or a direct prompt string.",
        epilog='Example:\n  task run "Create a file named hello.txt"\n  task run ./tasks/my_task.yaml',
    )
    parser_run.add_argument(
        "task_identifier",
        nargs="?",
        help="Path to the task YAML file or a prompt string. Omit to see help.",
    )

    parser_resume = task_subparsers.add_parser(
        "resume",
        help="Resume a paused agent task with human feedback.",
        epilog="Example: task resume f16a9f5b-...",
    )
    parser_resume.add_argument(
        "task_id",
        nargs="?",
        help="The ID of the paused task. Omit to see help.",
        choices_provider=lambda self: sorted(self.interrupted_tasks.keys()),
    )

    @cmd2.with_argparser(task_parser)
    @cmd2.with_category("Agent Commands")
    def do_task(self, args):
        if hasattr(args, "func"):
            args.func(self, args)
        else:
            self.do_help("task")

    # --- Noun: tool ---
    tool_parser = cmd2.Cmd2ArgumentParser(description="Manage agent tools.")
    tool_subparsers = tool_parser.add_subparsers(
        title="sub-commands", help="Tool actions"
    )

    parser_list_tools = tool_subparsers.add_parser(
        "list",
        help="List all registered tools available to the agent.",
        aliases=["ls"],
        epilog="Example: tool list",
    )
    parser_list_tools.add_argument("--json", action="store_true", help="Output as JSON")
    parser_validate_tool = tool_subparsers.add_parser(
        "validate",
        help="Validate a tool file for syntax and registration errors.",
        epilog="Example: tool validate plugins/my_new_tool.py",
    )
    parser_validate_tool.add_argument(
        "file_path", nargs="?", type=Path, help="Path to the Python tool file."
    )
    parser_new_tool = tool_subparsers.add_parser(
        "new",
        help="Create a new boilerplate tool file in the plugins/ directory.",
        aliases=["create"],
        epilog="Example: tool new",
    )
    parser_view_tool = tool_subparsers.add_parser(
        "view",
        help="View details and the input schema for a specific tool.",
        aliases=["show"],
        epilog="Example: tool view run_local_command",
    )
    parser_view_tool.add_argument(
        "tool_name",
        nargs="?",
        help="The name of the tool to view.",
        choices_provider=lambda self: self._provide_tool_choices(),
    )

    @cmd2.with_argparser(tool_parser)
    @cmd2.with_category("Agent Commands")
    def do_tool(self, args):
        if hasattr(args, "func"):
            args.func(self, args)
        else:
            self.do_help("tool")

    # --- Noun: config ---
    config_parser = cmd2.Cmd2ArgumentParser(description="Manage system configurations.")
    config_subparsers = config_parser.add_subparsers(
        title="sub-commands", help="Config actions"
    )

    parser_validate_config = config_subparsers.add_parser(
        "validate",
        help="Validate all core .yaml configuration files.",
        aliases=["check"],
        epilog="Example: config validate",
    )
    parser_view_config = config_subparsers.add_parser(
        "view",
        help="View a safelisted configuration file.",
        aliases=["show"],
        epilog="Example: config view backends.yaml",
    )
    parser_view_config.add_argument(
        "filename",
        nargs="?",
        help="The name of the config file.",
        choices_provider=lambda self: self._provide_config_choices(),
    )
    parser_edit_config = config_subparsers.add_parser(
        "edit",
        help="Edit a safelisted configuration file in $EDITOR.",
        epilog="Example: config edit machines.yaml",
    )
    parser_edit_config.add_argument(
        "filename",
        nargs="?",
        help="The name of the config file to edit.",
        choices_provider=lambda self: self._provide_config_choices(),
    )

    @cmd2.with_argparser(config_parser)
    @cmd2.with_category("Agent Commands")
    def do_config(self, args):
        if hasattr(args, "func"):
            args.func(self, args)
        else:
            self.do_help("config")

    # --- Noun: artifact ---
    artifact_parser = cmd2.Cmd2ArgumentParser(description="Manage task artifacts.")
    artifact_subparsers = artifact_parser.add_subparsers(
        title="sub-commands", help="Artifact actions"
    )

    parser_list_artifacts = artifact_subparsers.add_parser(
        "list",
        help="List all completed task artifacts.",
        aliases=["ls"],
        epilog="Example: artifact list",
    )
    parser_list_artifacts.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )
    parser_view_artifact = artifact_subparsers.add_parser(
        "view",
        help="View the summary and provenance for a task.",
        aliases=["show"],
        epilog="Example: artifact view test-basic_file_ops-...",
    )
    parser_view_artifact.add_argument(
        "task_id",
        nargs="?",
        help="The ID of the task to view.",
        choices_provider=lambda self: self._provide_artifact_choices(),
    )
    parser_delete_artifact = artifact_subparsers.add_parser(
        "delete",
        help="Delete all artifacts for a specific task.",
        aliases=["rm"],
        epilog="Example: artifact delete test-basic_file_ops-...",
    )
    parser_delete_artifact.add_argument(
        "task_id",
        nargs="?",
        help="The ID of the task artifacts to delete.",
        choices_provider=lambda self: self._provide_artifact_choices(),
    )

    @cmd2.with_argparser(artifact_parser)
    @cmd2.with_category("Agent Commands")
    def do_artifact(self, args):
        if hasattr(args, "func"):
            args.func(self, args)
        else:
            self.do_help("artifact")

    # --- Noun: preset ---
    preset_parser = cmd2.Cmd2ArgumentParser(description="Manage agent presets.")
    preset_subparsers = preset_parser.add_subparsers(
        title="sub-commands", help="Preset actions"
    )

    parser_list_presets = preset_subparsers.add_parser(
        "list",
        help="List available agent presets.",
        aliases=["ls"],
        epilog="Example: preset list",
    )
    parser_list_presets.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )
    parser_view_preset = preset_subparsers.add_parser(
        "view",
        help="View a specific preset file.",
        aliases=["show"],
        epilog="Example: preset view default",
    )
    parser_view_preset.add_argument(
        "preset_id",
        nargs="?",
        help="The ID of the preset to view (filename without .yaml).",
        choices_provider=lambda self: self._provide_preset_choices(),
    )
    parser_new_preset = preset_subparsers.add_parser(
        "new",
        help="Create a new boilerplate preset file.",
        aliases=["create"],
        epilog="Example: preset new",
    )
    parser_delete_preset = preset_subparsers.add_parser(
        "delete",
        help="Delete a preset file.",
        aliases=["rm"],
        epilog="Example: preset delete my_temporary_preset",
    )
    parser_delete_preset.add_argument(
        "preset_id",
        nargs="?",
        help="The ID of the preset to delete.",
        choices_provider=lambda self: self._provide_preset_choices(),
    )

    @cmd2.with_argparser(preset_parser)
    @cmd2.with_category("Agent Commands")
    def do_preset(self, args):
        if hasattr(args, "func"):
            args.func(self, args)
        else:
            self.do_help("preset")

    # --- Noun: backend ---
    backend_parser = cmd2.Cmd2ArgumentParser(
        description="Manage backend configurations."
    )
    backend_subparsers = backend_parser.add_subparsers(
        title="sub-commands", help="Backend actions"
    )

    parser_list_backends = backend_subparsers.add_parser(
        "list",
        help="List available backend profiles from backends.yaml.",
        aliases=["ls"],
        epilog="Example: backend list",
    )
    parser_list_backends.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    @cmd2.with_argparser(backend_parser)
    @cmd2.with_category("Agent Commands")
    def do_backend(self, args):
        if hasattr(args, "func"):
            args.func(self, args)
        else:
            self.do_help("backend")

    # --- Noun: machine ---
    machine_parser = cmd2.Cmd2ArgumentParser(description="Manage machine definitions.")
    machine_subparsers = machine_parser.add_subparsers(
        title="sub-commands", help="Machine actions"
    )
    parser_list_machines = machine_subparsers.add_parser(
        "list",
        help="List all defined machines from machines.yaml.",
        aliases=["ls"],
        epilog="Example: machine list",
    )
    parser_list_machines.add_argument(
        "--json", action="store_true", help="Output as JSON"
    )

    @cmd2.with_argparser(machine_parser)
    @cmd2.with_category("Agent Commands")
    def do_machine(self, args):
        if hasattr(args, "func"):
            args.func(self, args)
        else:
            self.do_help("machine")

    # --- Noun: session ---
    session_parser = cmd2.Cmd2ArgumentParser(
        description="Manage shell session settings."
    )
    session_subparsers = session_parser.add_subparsers(
        title="sub-commands", help="Session actions"
    )

    parser_set_session = session_subparsers.add_parser(
        "set",
        help="Set a default preset or backend for the current session.",
        epilog="Example:\n  session set preset verified_flow\n  session set backend openai_gpt4",
    )
    parser_set_session.add_argument(
        "key", nargs="?", choices=["backend", "preset"], help="The setting to change."
    )
    parser_set_session.add_argument(
        "value",
        nargs="?",
        help="The new default value.",
        completer=lambda self, text, line, begidx, endidx: self._session_set_value_completer(
            text, line, begidx, endidx
        ),
    )

    parser_view_session = session_subparsers.add_parser(
        "view",
        help="View current session defaults.",
        aliases=["show"],
        epilog="Example: session view",
    )

    @cmd2.with_argparser(session_parser)
    @cmd2.with_category("Session Commands")
    def do_session(self, args):
        if hasattr(args, "func"):
            args.func(self, args)
        else:
            self.do_help("session")

    # --- Noun: test ---
    test_parser = cmd2.Cmd2ArgumentParser(description="Run the regression test suite.")
    test_subparsers = test_parser.add_subparsers(
        title="sub-commands", help="Test actions"
    )

    parser_run_tests = test_subparsers.add_parser(
        "run",
        help="Run a single test or the entire suite.",
        epilog="Example:\n  test run\n  test run basic_file_ops",
    )
    parser_run_tests.add_argument(
        "test_name",
        nargs="?",
        help="The specific test to run (e.g., 'basic_file_ops'). If omitted, all tests run.",
        choices_provider=lambda self: self._provide_test_choices(),
    )
    parser_list_tests = test_subparsers.add_parser(
        "list",
        help="List all available regression tests.",
        aliases=["ls"],
        epilog="Example: test list",
    )
    parser_list_tests.add_argument("--json", action="store_true", help="Output as JSON")

    @cmd2.with_argparser(test_parser)
    @cmd2.with_category("Agent Commands")
    def do_test(self, args):
        if hasattr(args, "func"):
            args.func(self, args)
        else:
            self.do_help("test")

    # --- Handler Implementations ---
    from aegis._shell_handlers import (
        _task_run_handler,
        _task_resume_handler,
        _execute_graph,
        _tool_list_handler,
        _tool_validate_handler,
        _tool_new_handler,
        _tool_view_handler,
        _config_validate_handler,
        _config_view_handler,
        _config_edit_handler,
        _list_artifacts_handler,
        _artifact_view_handler,
        _artifact_delete_handler,
        _list_presets_handler,
        _preset_view_handler,
        _preset_new_handler,
        _preset_delete_handler,
        _backend_list_handler,
        _machine_list_handler,
        _session_set_handler,
        _session_view_handler,
        _test_run_handler,
        _test_list_handler,
        _provide_tool_choices,
        _provide_config_choices,
        _provide_artifact_choices,
        _provide_preset_choices,
        _provide_backend_choices,
        _provide_dataset_choices,
        _provide_test_choices,
        _session_set_value_completer,
        _ensure_tools_loaded,
    )

    # Bind handlers to their parsers
    parser_run.set_defaults(func=_task_run_handler)
    parser_resume.set_defaults(func=_task_resume_handler)
    parser_list_tools.set_defaults(func=_tool_list_handler)
    parser_validate_tool.set_defaults(func=_tool_validate_handler)
    parser_new_tool.set_defaults(func=_tool_new_handler)
    parser_view_tool.set_defaults(func=_tool_view_handler)
    parser_validate_config.set_defaults(func=_config_validate_handler)
    parser_view_config.set_defaults(func=_config_view_handler)
    parser_edit_config.set_defaults(func=_config_edit_handler)
    parser_list_artifacts.set_defaults(func=_list_artifacts_handler)
    parser_view_artifact.set_defaults(func=_artifact_view_handler)
    parser_delete_artifact.set_defaults(func=_artifact_delete_handler)
    parser_list_presets.set_defaults(func=_list_presets_handler)
    parser_view_preset.set_defaults(func=_preset_view_handler)
    parser_new_preset.set_defaults(func=_preset_new_handler)
    parser_delete_preset.set_defaults(func=_preset_delete_handler)
    parser_list_backends.set_defaults(func=_backend_list_handler)
    parser_list_machines.set_defaults(func=_machine_list_handler)
    parser_set_session.set_defaults(func=_session_set_handler)
    parser_view_session.set_defaults(func=_session_view_handler)
    parser_run_tests.set_defaults(func=_test_run_handler)
    parser_list_tests.set_defaults(func=_test_list_handler)
