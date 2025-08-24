# tests/executors/test_local_ssh_redaction.py
import re

from aegis.executors.local_exec import _sanitize_cli as local_sanitize
from aegis.executors.ssh_exec import _sanitize_cli_list as ssh_sanitize


def _no_secret_leaks(s: str, secrets: list[str]):
    s_lower = s.lower()
    for sec in secrets:
        assert sec.lower() not in s_lower, f"secret leaked in log: {sec}"


def test_local_sanitize_masks_common_tokens():
    cmd = (
        "curl -H 'Authorization: Bearer SECRET_TOKEN' "
        "-H 'Cookie: SESSIONID=abc123; path=/' "
        "--password supersecret --private-key /home/user/.ssh/id_ed25519 "
        "endpoint?api_key=SHH"
    )
    masked = local_sanitize(cmd)
    # ensure obvious tokens are gone
    _no_secret_leaks(
        masked, ["SECRET_TOKEN", "abc123", "supersecret", "id_ed25519", "api_key=SHH"]
    )
    # preserve non-sensitive structure
    assert "Authorization" in masked and "Cookie" in masked and "--password" in masked


def test_ssh_sanitize_masks_identity_file_and_tokens():
    argv = [
        "ssh",
        "-p",
        "22",
        "-i",
        "/home/user/.ssh/id_rsa",
        "user@host",
        "echo",
        "hello",
        "password=opensesame",
        "token=XYZ",
    ]
    masked = ssh_sanitize(argv)
    _no_secret_leaks(masked, ["/home/user/.ssh/id_rsa", "opensesame", "XYZ"])
    # sanity: still looks like a command line
    assert masked.startswith("ssh ") and "user@host" in masked
