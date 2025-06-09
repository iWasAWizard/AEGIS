# aegis/tests/tools/test_rag_wrapper.py
"""
Tests for the RAG (Retrieval-Augmented Generation) tool.
"""
import json
from pathlib import Path

import pytest

from aegis.tools.wrappers.rag import KnowledgeQueryInput, query_knowledge_base
from aegis.utils.memory_indexer import update_memory_index

# Mark this module to be skipped if vector dependencies are not installed
pytest.importorskip("faiss")
pytest.importorskip("sentence_transformers")


@pytest.fixture
def memory_setup(tmp_path: Path, monkeypatch):
    """
    Creates a temporary directory structure for logs and indexes,
    populates it with a sample log, and runs the indexer.
    """
    # Create fake project directories
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir()
    index_dir = tmp_path / "index"
    index_dir.mkdir()

    # Monkeypatch the paths in the modules to use our temp dirs
    monkeypatch.setattr("aegis.utils.memory_indexer.LOGS_DIR", logs_dir)
    monkeypatch.setattr("aegis.utils.memory_indexer.INDEX_DIR", index_dir)
    monkeypatch.setattr("aegis.tools.wrappers.rag.LOGS_DIR", logs_dir)
    monkeypatch.setattr("aegis.tools.wrappers.rag.INDEX_DIR", index_dir)

    # Create a sample log file with a structured event
    log_file = logs_dir / "task-123.jsonl"
    log_event = {
        "timestamp": "2024-01-01T12:00:00Z",
        "level": "INFO",
        "message": "The 'nmap_port_scan' tool was used to check for open web ports.",
        "logger_name": "aegis.test",
        "event_type": "ToolEnd",
    }
    log_file.write_text(json.dumps(log_event) + "\n")

    # Run the indexer to create the FAISS index from the log
    update_memory_index()

    return {"logs_dir": logs_dir, "index_dir": index_dir}


def test_rag_semantic_search_success(memory_setup):
    """Verify that a semantic query finds the relevant log entry via the FAISS index."""
    query = "How do I check for http ports?"
    input_data = KnowledgeQueryInput(query=query)

    result = query_knowledge_base(input_data)

    assert "Found the following relevant entries" in result
    assert "nmap_port_scan" in result
    assert "open web ports" in result


def test_rag_keyword_fallback(memory_setup, monkeypatch):
    """Verify the tool falls back to keyword search if the index is missing."""
    # Simulate a missing index by pointing to a non-existent file
    monkeypatch.setattr(
        "aegis.tools.wrappers.rag.INDEX_PATH", Path("non-existent-index")
    )

    query = "nmap"  # A direct keyword match
    input_data = KnowledgeQueryInput(query=query)

    result = query_knowledge_base(input_data)

    assert "via keyword search" in result
    assert "nmap_port_scan" in result


def test_rag_no_results_found(memory_setup):
    """Verify a 'not found' message is returned for an irrelevant query."""
    query = "how to make coffee"
    input_data = KnowledgeQueryInput(query=query)

    result = query_knowledge_base(input_data)

    assert "No relevant information found" in result
