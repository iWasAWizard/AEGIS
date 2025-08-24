# tests/executors/test_docker_sanitizers.py
from aegis.executors.docker_exec import _sanitize_env, _sanitize_auth_config


def _no_secret_leaks_in_mapping(m: dict, secrets: list[str]):
    joined = " ".join(f"{k}={v}" for k, v in (m or {}).items())
    for sec in secrets:
        assert sec.lower() not in joined.lower(), f"secret leaked: {sec}"


def test_sanitize_env_dict_masks_values():
    env = {"PASSWORD": "hunter2", "TOKEN": "abc123", "SAFE": "ok"}
    masked = _sanitize_env(env)
    assert isinstance(masked, dict)
    _no_secret_leaks_in_mapping(masked, ["hunter2", "abc123"])
    assert "SAFE" in masked


def test_sanitize_env_list_masks_values():
    env_list = ["PASSWORD=hunter2", "TOKEN=abc123", "SAFE=ok"]
    masked = _sanitize_env(env_list)
    assert isinstance(masked, dict)
    _no_secret_leaks_in_mapping(masked, ["hunter2", "abc123"])
    assert "SAFE" in masked


def test_sanitize_auth_config_masks_secret_fields():
    auth = {"username": "u", "password": "p@ss", "identitytoken": "tok"}
    masked = _sanitize_auth_config(auth)
    assert isinstance(masked, dict)
    _no_secret_leaks_in_mapping(masked, ["p@ss", "tok"])
    # username might remain visible; we only assert secrets are gone
