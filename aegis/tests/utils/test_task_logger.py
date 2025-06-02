from aegis.utils.task_logger import log_event


def test_log_event_creates_file(tmp_path):
    task_id = "testlog"
    log_event(task_id, {"event": "test"}, logs_dir=str(tmp_path))
    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    content = files[0].read_text()
    assert "event" in content
