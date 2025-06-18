# aegis/tests/utils/test_memory_indexer.py
"""
Unit tests for the RAG memory indexing utility.
"""
import json
from pathlib import Path

import pytest

from aegis.utils import memory_indexer

# Mark this module to be skipped if vector dependencies are not installed
faiss = pytest.importorskip("faiss", reason="faiss-cpu not installed")
SentenceTransformer = pytest.importorskip("sentence_transformers",
                                          reason="sentence-transformers not installed").SentenceTransformer


# --- Fixtures ---

@pytest.fixture
def mock_log_dir(tmp_path: Path, monkeypatch):
    """Creates a temporary log and index directory structure for testing."""
    logs_dir = tmp_path / "logs"
    index_dir = tmp_path / "index"
    logs_dir.mkdir()
    index_dir.mkdir()

    # Log file with valid, structured events
    log_file_1 = logs_dir / "task-001.jsonl"
    log_events_1 = [
        {"event_type": "ToolStart", "message": "Starting nmap scan."},
        {"event_type": "ToolEnd", "message": "Nmap scan complete."},
    ]
    with log_file_1.open("w") as f:
        for event in log_events_1:
            f.write(json.dumps(event) + "\n")

    # Log file with mixed and invalid content
    log_file_2 = logs_dir / "task-002.jsonl"
    with log_file_2.open("w") as f:
        # A valid entry
        f.write(json.dumps({"event_type": "PlannerError", "message": "LLM failed"}) + "\n")
        # An entry without an event_type (should be skipped)
        f.write(json.dumps({"message": "Just a random log"}) + "\n")
        # A line that is not JSON (should be skipped)
        f.write("this is not json\n")

    # Monkeypatch the constants in the indexer module
    monkeypatch.setattr(memory_indexer, "LOGS_DIR", logs_dir)
    monkeypatch.setattr(memory_indexer, "INDEX_DIR", index_dir)

    return {"logs_dir": logs_dir, "index_dir": index_dir}


def test_update_memory_index_success(mock_log_dir):
    """
    Verify that the memory indexer correctly processes valid log files,
    creates the index and mapping files, and ignores invalid entries.
    """
    # Run the indexer
    memory_indexer.update_memory_index()

    index_dir = mock_log_dir["index_dir"]
    index_path = index_dir / "aegis_memory.faiss"
    mapping_path = index_dir / "aegis_memory_mapping.json"

    # 1. Check that the files were created
    assert index_path.is_file(), "FAISS index file was not created."
    assert mapping_path.is_file(), "Index-to-text mapping file was not created."

    # 2. Check the content of the mapping file
    with mapping_path.open("r") as f:
        mapping_data = json.load(f)

    # There should be exactly 3 valid entries with 'event_type' from our mock files
    assert len(mapping_data) == 3

    # Check that the content is what we expect
    assert "Event: ToolStart | Message: Starting nmap scan." in mapping_data
    assert "Event: ToolEnd | Message: Nmap scan complete." in mapping_data
    assert "Event: PlannerError | Message: LLM failed" in mapping_data

    # 3. Check the FAISS index itself
    index = faiss.read_index(str(index_path))
    assert index.ntotal == 3  # The number of vectors should match the number of valid entries
