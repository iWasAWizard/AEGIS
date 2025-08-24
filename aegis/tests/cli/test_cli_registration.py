# tests/cli/test_cli_registration.py
import pytest

from aegis.shell import AegisShell


@pytest.mark.parametrize(
    "cmd_name",
    [
        "compose",
        "docker",
        "kube",
        "ssh",
        "redis",
        "http",
        "gitlab",
        "local",
    ],
)
def test_executor_cli_is_registered(cmd_name):
    """
    Sanity check: the shell should expose the CLI verbs we registered.
    We rely on cmd2's convention that registered commands appear as
    do_<name> bound methods on the application.
    """
    app = AegisShell()
    assert hasattr(app, f"do_{cmd_name}"), f"Missing CLI: {cmd_name}"
