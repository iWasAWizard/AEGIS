# aegis/cli/gitlab.py
"""
GitLab CLI integration for AEGIS.

Subcommands:
  - projects           : List projects (optional search/visibility)
  - issue create       : Create an issue in a project

This module is a thin adapter that calls
`aegis.executors.gitlab_exec.GitlabExecutor` ToolResult wrappers directly.
No business logic is duplicated here.
"""
from __future__ import annotations

from typing import List, Optional
import json
import cmd2
from cmd2 import Cmd2ArgumentParser, with_argparser, with_default_category

from aegis.cli._common import print_result
from aegis.executors.gitlab_exec import GitlabExecutor


def _labels_from_args(values: Optional[List[str]]) -> Optional[List[str]]:
    """
    Accept --label multiple times or comma-separated entries.
    Example:
      --label bug --label "triage,backend"
    """
    if not values:
        return None
    out: List[str] = []
    for v in values:
        # split on commas but keep trimmed tokens
        parts = [p.strip() for p in v.split(",") if p.strip()]
        out.extend(parts)
    return out or None


def _maybe_file_text(s: Optional[str]) -> Optional[str]:
    """
    Support raw string or @/path/to/file for descriptions.
    """
    if not s:
        return None
    if s.startswith("@"):
        path = s[1:]
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    return s


def _make_parser() -> Cmd2ArgumentParser:
    p = Cmd2ArgumentParser(
        prog="gitlab",
        description="GitLab operations via GitlabExecutor",
        add_help=True,
    )
    sub = p.add_subparsers(dest="subcmd", required=True)

    # projects
    p_projects = sub.add_parser("projects", help="List projects")
    p_projects.add_argument("--search", help="Search term")
    p_projects.add_argument(
        "--visibility",
        choices=["public", "internal", "private"],
        help="Filter by visibility",
    )
    p_projects.add_argument("--json", dest="json_out", action="store_true")

    # issue group
    p_issue = sub.add_parser("issue", help="Issue operations")
    issue_sub = p_issue.add_subparsers(dest="issue_cmd", required=True)

    p_issue_create = issue_sub.add_parser("create", help="Create an issue")
    p_issue_create.add_argument(
        "--project-id", type=int, required=True, help="Numeric project ID"
    )
    p_issue_create.add_argument("--title", required=True, help="Issue title")
    p_issue_create.add_argument(
        "--description",
        help="Description text or @/path/to/file to load",
    )
    p_issue_create.add_argument(
        "--label",
        action="append",
        dest="labels",
        help="Label (repeatable) or comma-separated 'l1,l2'",
    )
    p_issue_create.add_argument("--json", dest="json_out", action="store_true")

    return p


@with_default_category("GitLab")
class GitlabCommandSet(cmd2.CommandSet):
    def __init__(self) -> None:
        super().__init__()
        self._parser = _make_parser()

    def _exe(self) -> GitlabExecutor:
        # Instantiation may validate env and authenticate
        return GitlabExecutor()

    @with_argparser(_make_parser())
    def do_gitlab(self, ns: cmd2.Statement) -> None:
        a = ns

        if a.subcmd == "projects":
            try:
                exe = self._exe()
                # Prefer ToolResult wrapper if available
                if hasattr(exe, "list_projects_result"):
                    res = exe.list_projects_result(
                        search=a.search, visibility=a.visibility
                    )
                    print_result(self._cmd, res, as_json=bool(a.json_out))
                else:
                    data = exe.list_projects(search=a.search, visibility=a.visibility)
                    if a.json_out:
                        self._cmd.poutput(json.dumps(data, indent=2))
                    else:
                        # Pretty minimal table
                        for pr in data:
                            line = f"{pr.get('id')}  {pr.get('path_with_namespace')}  [{pr.get('visibility')}]"
                            self._cmd.poutput(line)
            except Exception as e:
                self.perror(str(e))
            return

        if a.subcmd == "issue" and a.issue_cmd == "create":
            try:
                exe = self._exe()
                description = _maybe_file_text(a.description)
                labels = _labels_from_args(a.labels)
                if hasattr(exe, "create_issue_result"):
                    res = exe.create_issue_result(
                        project_id=a.project_id,
                        title=a.title,
                        description=description,
                        labels=labels,
                    )
                    print_result(self._cmd, res, as_json=bool(a.json_out))
                else:
                    data = exe.create_issue(
                        project_id=a.project_id,
                        title=a.title,
                        description=description,
                        labels=labels,
                    )
                    if a.json_out:
                        self._cmd.poutput(json.dumps(data, indent=2))
                    else:
                        self._cmd.poutput(
                            f"Issue !{data.get('iid')} created: {data.get('title')} ({data.get('web_url')})"
                        )
            except Exception as e:
                self.perror(str(e))
            return

        self.perror(f"Unknown subcommand: {getattr(a, 'subcmd', None)}")


def register(app: cmd2.Cmd) -> None:
    app.add_command_set(GitlabCommandSet())
