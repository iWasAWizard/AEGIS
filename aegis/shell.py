# aegis/shell.py
"""
An interactive shell interface for the AEGIS framework, built with cmd2.

This module provides a cohesive, line-oriented command processor for interacting
with the AEGIS agent, using a noun-verb sub-command paradigm.
"""
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
        self.prompt = cmd2.ansi.style("(aegis) > ", bold=True)
        self.intro = cmd2.ansi.style(
            "Welcome to the AEGIS Agentic Framework Shell. Type 'help' for a list of commands.",
            bold=True,
        )
        self.console = Console()
        # Session-specific settings
        self.session_backend = None
        self.session_preset = None

    def startup(self):
        """This method is called once at the start of the application."""
        self.poutput("Importing all available tools...")
        import_all_tools()
        self.poutput(
            cmd2.ansi.style(
                f"✅ Tool registry loaded with {len(TOOL_REGISTRY)} tools.", green=True
            )
        )

    # --- Noun: task ---
    task_parser = cmd2.Cmd2ArgumentParser(description="Run and manage agent tasks.")
    task_subparsers = task_parser.add_subparsers(
        title="sub-commands", help="Task actions"
    )

    parser_run = task_subparsers.add_parser("run", help="Run a task from a YAML file.")
    parser_run.add_argument("task_file", type=Path, help="Path to the task YAML file.")

    parser_resume = task_subparsers.add_parser("resume", help="Resume a paused task.")
    parser_resume.add_argument(
        "task_id",
        help="The ID of the paused task.",
        choices_provider=lambda self: self._provide_artifact_choices(),
    )

    @cmd2.with_argparser(task_parser)
    async def do_task(self, args):
        if hasattr(args, "func"):
            await args.func(self, args)

    # --- Noun: tool ---
    tool_parser = cmd2.Cmd2ArgumentParser(description="Manage agent tools.")
    tool_subparsers = tool_parser.add_subparsers(
        title="sub-commands", help="Tool actions"
    )

    parser_list_tools = tool_subparsers.add_parser(
        "list", help="List all registered tools."
    )
    parser_validate_tool = tool_subparsers.add_parser(
        "validate", help="Validate a single tool file."
    )
    parser_validate_tool.add_argument(
        "file_path", type=Path, help="Path to the Python tool file."
    )
    parser_new_tool = tool_subparsers.add_parser(
        "new", help="Create a new boilerplate tool file."
    )
    parser_view_tool = tool_subparsers.add_parser(
        "view", help="View details for a specific tool."
    )
    parser_view_tool.add_argument(
        "tool_name",
        help="The name of the tool to view.",
        choices_provider=lambda self: self._provide_tool_choices(),
    )

    @cmd2.with_argparser(tool_parser)
    def do_tool(self, args):
        if hasattr(args, "func"):
            args.func(self, args)

    # --- Noun: config ---
    config_parser = cmd2.Cmd2ArgumentParser(description="Manage system configurations.")
    config_subparsers = config_parser.add_subparsers(
        title="sub-commands", help="Config actions"
    )

    parser_validate_config = config_subparsers.add_parser(
        "validate", help="Validate all .yaml config files."
    )
    parser_view_config = config_subparsers.add_parser(
        "view", help="View a configuration file."
    )
    parser_view_config.add_argument(
        "filename",
        help="The name of the config file (e.g., 'backends.yaml').",
        choices_provider=lambda self: self._provide_config_choices(),
    )
    parser_edit_config = config_subparsers.add_parser(
        "edit", help="Edit a configuration file in $EDITOR."
    )
    parser_edit_config.add_argument(
        "filename",
        help="The name of the config file to edit.",
        choices_provider=lambda self: self._provide_config_choices(),
    )

    @cmd2.with_argparser(config_parser)
    def do_config(self, args):
        if hasattr(args, "func"):
            args.func(self, args)

    # --- Noun: artifact ---
    artifact_parser = cmd2.Cmd2ArgumentParser(description="Manage task artifacts.")
    artifact_subparsers = artifact_parser.add_subparsers(
        title="sub-commands", help="Artifact actions"
    )

    parser_list_artifacts = artifact_subparsers.add_parser(
        "list", help="List all completed task artifacts."
    )
    parser_view_artifact = artifact_subparsers.add_parser(
        "view", help="View the summary and provenance for a task."
    )
    parser_view_artifact.add_argument(
        "task_id",
        help="The ID of the task to view.",
        choices_provider=lambda self: self._provide_artifact_choices(),
    )
    parser_delete_artifact = artifact_subparsers.add_parser(
        "delete", help="Delete the artifacts for a task."
    )
    parser_delete_artifact.add_argument(
        "task_id",
        help="The ID of the task artifacts to delete.",
        choices_provider=lambda self: self._provide_artifact_choices(),
    )

    @cmd2.with_argparser(artifact_parser)
    def do_artifact(self, args):
        if hasattr(args, "func"):
            args.func(self, args)

    # --- Noun: preset ---
    preset_parser = cmd2.Cmd2ArgumentParser(description="Manage agent presets.")
    preset_subparsers = preset_parser.add_subparsers(
        title="sub-commands", help="Preset actions"
    )

    parser_list_presets = preset_subparsers.add_parser(
        "list", help="List available agent presets."
    )
    parser_view_preset = preset_subparsers.add_parser(
        "view", help="View a specific preset file."
    )
    parser_view_preset.add_argument(
        "preset_id",
        help="The ID of the preset to view (filename without .yaml).",
        choices_provider=lambda self: self._provide_preset_choices(),
    )
    parser_delete_preset = preset_subparsers.add_parser(
        "delete", help="Delete a preset file."
    )
    parser_delete_preset.add_argument(
        "preset_id",
        help="The ID of the preset to delete.",
        choices_provider=lambda self: self._provide_preset_choices(),
    )

    @cmd2.with_argparser(preset_parser)
    def do_preset(self, args):
        if hasattr(args, "func"):
            args.func(self, args)

    # --- Noun: eval ---
    eval_parser = cmd2.Cmd2ArgumentParser(description="Manage and run evaluations.")
    eval_subparsers = eval_parser.add_subparsers(
        title="sub-commands", help="Evaluation actions"
    )

    parser_run_evals = eval_subparsers.add_parser(
        "run", help="Run an evaluation suite against a LangFuse dataset."
    )
    parser_run_evals.add_argument(
        "dataset_name",
        help="The name of the dataset in LangFuse.",
        choices_provider=lambda self: self._provide_dataset_choices(),
    )
    parser_run_evals.add_argument(
        "--judge-model",
        default="openai_gpt4",
        help="The model profile for the judge LLM.",
    )

    parser_list_datasets = eval_subparsers.add_parser(
        "list-datasets", help="List all available datasets in LangFuse."
    )
    parser_view_dataset = eval_subparsers.add_parser(
        "view", help="View the items in a LangFuse dataset."
    )
    parser_view_dataset.add_argument(
        "dataset_name",
        help="The name of the dataset to view.",
        choices_provider=lambda self: self._provide_dataset_choices(),
    )

    @cmd2.with_argparser(eval_parser)
    async def do_eval(self, args):
        if hasattr(args, "func"):
            await args.func(self, args)

    # --- Noun: backend ---
    backend_parser = cmd2.Cmd2ArgumentParser(
        description="Manage backend configurations."
    )
    backend_subparsers = backend_parser.add_subparsers(
        title="sub-commands", help="Backend actions"
    )

    parser_list_backends = backend_subparsers.add_parser(
        "list", help="List available backend profiles."
    )

    @cmd2.with_argparser(backend_parser)
    def do_backend(self, args):
        if hasattr(args, "func"):
            args.func(self, args)

    # --- Noun: session ---
    session_parser = cmd2.Cmd2ArgumentParser(
        description="Manage shell session settings."
    )
    session_subparsers = session_parser.add_subparsers(
        title="sub-commands", help="Session actions"
    )

    parser_set_session = session_subparsers.add_parser(
        "set", help="Set a default for the current session."
    )
    parser_set_session.add_argument(
        "key", choices=["backend", "preset"], help="The setting to change."
    )
    parser_set_session.add_argument(
        "value",
        help="The new default value.",
        completer=lambda self, text, line, begidx, endidx: self._session_set_value_completer(
            text, line, begidx, endidx
        ),
    )

    parser_view_session = session_subparsers.add_parser(
        "view", help="View current session defaults."
    )

    @cmd2.with_argparser(session_parser)
    def do_session(self, args):
        if hasattr(args, "func"):
            args.func(self, args)

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
        _preset_delete_handler,
        _eval_run_handler,
        _eval_list_datasets_handler,
        _eval_view_dataset_handler,
        _backend_list_handler,
        _session_set_handler,
        _session_view_handler,
        _provide_tool_choices,
        _provide_config_choices,
        _provide_artifact_choices,
        _provide_preset_choices,
        _provide_backend_choices,
        _provide_dataset_choices,
        _session_set_value_completer,
    )

    # Bind handlers to their parsers
    parser_run.set_defaults(func=_task_run_handler)
    parser_resume.set_defaults(func=_task_resume_handler)
    parser_list_tools.set_defaults(func=lambda self, args: self._tool_list_handler())
    parser_validate_tool.set_defaults(
        func=lambda self, args: self._tool_validate_handler(args)
    )
    parser_new_tool.set_defaults(func=lambda self, args: self._tool_new_handler())
    parser_view_tool.set_defaults(func=lambda self, args: self._tool_view_handler(args))
    parser_validate_config.set_defaults(
        func=lambda self, args: self._config_validate_handler()
    )
    parser_view_config.set_defaults(
        func=lambda self, args: self._config_view_handler(args)
    )
    parser_edit_config.set_defaults(
        func=lambda self, args: self._config_edit_handler(args)
    )
    parser_list_artifacts.set_defaults(
        func=lambda self, args: self._list_artifacts_handler()
    )
    parser_view_artifact.set_defaults(
        func=lambda self, args: self._artifact_view_handler(args)
    )
    parser_delete_artifact.set_defaults(
        func=lambda self, args: self._artifact_delete_handler(args)
    )
    parser_list_presets.set_defaults(
        func=lambda self, args: self._list_presets_handler()
    )
    parser_view_preset.set_defaults(
        func=lambda self, args: self._preset_view_handler(args)
    )
    parser_delete_preset.set_defaults(
        func=lambda self, args: self._preset_delete_handler(args)
    )
    parser_run_evals.set_defaults(func=lambda self, args: self._eval_run_handler(args))
    parser_list_datasets.set_defaults(
        func=lambda self, args: self._eval_list_datasets_handler()
    )
    parser_view_dataset.set_defaults(
        func=lambda self, args: self._eval_view_dataset_handler(args)
    )
    parser_list_backends.set_defaults(
        func=lambda self, args: self._backend_list_handler()
    )
    parser_set_session.set_defaults(
        func=lambda self, args: self._session_set_handler(args)
    )
    parser_view_session.set_defaults(
        func=lambda self, args: self._session_view_handler()
    )
