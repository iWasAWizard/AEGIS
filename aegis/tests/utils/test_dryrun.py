# tests/utils/test_dryrun.py
from aegis.utils.dryrun import dry_run


def test_callable_and_property_and_contexts():
    dry_run.set(False)
    assert dry_run.enabled is False
    assert dry_run() is False

    with dry_run.activate():
        assert dry_run.enabled is True
        assert dry_run() is True

    assert dry_run.enabled is False
    assert dry_run() is False

    with dry_run.override(True):
        assert dry_run.enabled is True
    assert dry_run.enabled is False


def test_preview_payload_shape():
    dry_run.set(True)
    p = dry_run.preview_payload(tool="redis.set", args={"k": "v"})
    assert p["tool"] == "redis.set"
    assert "args" in p and "ts_ms" in p
