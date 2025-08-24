# tests/executors/test_gitlab_exec.py
import json
import pytest

from aegis.executors.gitlab_exec import GitlabExecutor


def _mk_executor(monkeypatch):
    """
    Create a GitlabExecutor without importing/using the real python-gitlab SDK.
    We monkeypatch __init__ to avoid auth and just attach minimal attributes.
    """

    def fake_init(self):
        self.gl = object()
        self.default_timeout = 5  # not used by wrappers, but harmless

    monkeypatch.setattr(GitlabExecutor, "__init__", fake_init, raising=True)
    return GitlabExecutor()


def test_list_projects_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    projects = [
        {
            "id": 1,
            "name": "aegis",
            "path_with_namespace": "org/aegis",
            "visibility": "private",
            "web_url": "https://gitlab.example.com/org/aegis",
            "last_activity_at": "2024-01-01T00:00:00Z",
        }
    ]
    monkeypatch.setattr(exe, "list_projects", lambda **kwargs: projects, raising=True)

    res = exe.list_projects_result(search="aegis", visibility="private")
    assert res.ok is True
    assert json.loads(res.stdout) == projects
    assert res.exit_code == 0
    assert res.meta.get("search") == "aegis"
    assert res.meta.get("visibility") == "private"


def test_create_issue_result_success(monkeypatch):
    exe = _mk_executor(monkeypatch)
    issue = {
        "iid": 42,
        "title": "Bug: flakey test",
        "state": "opened",
        "web_url": "https://gitlab.example.com/org/aegis/-/issues/42",
        "created_at": "2024-01-02T00:00:00Z",
    }
    monkeypatch.setattr(exe, "create_issue", lambda **kwargs: issue, raising=True)

    res = exe.create_issue_result(project_id=1, title="Bug: flakey test")
    assert res.ok is True
    assert json.loads(res.stdout) == issue
    assert res.exit_code == 0
    assert res.meta.get("project_id") == 1
    assert res.meta.get("title") == "Bug: flakey test"


def test_list_projects_result_timeout_mapping(monkeypatch):
    exe = _mk_executor(monkeypatch)

    class Timeouty(Exception):
        def __str__(self):
            return "request timeout contacting gitlab"

    def boom(**kwargs):
        raise Timeouty()

    monkeypatch.setattr(exe, "list_projects", boom, raising=True)

    res = exe.list_projects_result(search=None, visibility=None)
    assert res.ok is False
    assert res.error_type == "Timeout"
    assert "timeout" in (res.stderr or "").lower()


def test_create_issue_result_auth_mapping(monkeypatch):
    exe = _mk_executor(monkeypatch)

    def boom(**kwargs):
        raise RuntimeError("permission denied: invalid token")

    monkeypatch.setattr(exe, "create_issue", boom, raising=True)

    res = exe.create_issue_result(project_id=1, title="Nope")
    assert res.ok is False
    assert res.error_type == "Auth"
    assert "permission" in (res.stderr or "").lower()
