# aegis/tools/wrappers/rag.py
"""
A tool for providing Retrieval-Augmented Generation (RAG) capabilities.

This allows the agent to query its own long-term memory, which is stored
as structured logs, to inform its planning process.
"""
import json
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field

from aegis.registry import register_tool
from aegis.utils.logger import setup_logger

# Attempt to import vector search libraries, but don't fail if they're not installed.
try:
    import faiss
    from sentence_transformers import SentenceTransformer

    VECTOR_SEARCH_ENABLED = True
except ImportError:
    VECTOR_SEARCH_ENABLED = False

logger = setup_logger(__name__)

# --- Configuration ---
INDEX_DIR = Path("index")
INDEX_PATH = INDEX_DIR / "aegis_memory.faiss"
MAPPING_PATH = INDEX_DIR / "aegis_memory_mapping.json"
MODEL_NAME = "all-MiniLM-L6-v2"


class KnowledgeQueryInput(BaseModel):
    """Input model for querying the agent's knowledge base."""

    query: str = Field(
        ...,
        description="A natural language question about a past task, error, tool, or concept.",
    )
    top_k: int = Field(
        5,
        ge=1,
        le=20,
        description="The maximum number of relevant log entries to return.",
    )


def _fallback_keyword_search(query: str, top_k: int) -> str:
    """Performs a simple keyword search if vector search is unavailable."""
    logger.warning("Falling back to basic keyword search for RAG query.")
    log_dir = Path("logs")
    if not log_dir.exists():
        return "No knowledge base (logs directory) found."

    matches = []
    for log_file in log_dir.glob("*.jsonl"):
        try:
            with log_file.open("r", encoding="utf-8") as f:
                for line in f:
                    if query.lower() in line.lower():
                        matches.append(f"- {line.strip()}")
        except Exception as e:
            logger.error(
                f"Could not process log file {log_file} during keyword search: {e}"
            )

    if not matches:
        return "No relevant information found in knowledge base via keyword search."

    return "Found the following relevant entries (via keyword search):\n\n" + "\n".join(
        matches[-top_k:]
    )


def _semantic_search(query: str, top_k: int) -> str:
    """Performs a semantic vector search using a FAISS index."""
    logger.info("Performing semantic search with FAISS index.")

    # 1. Load the model, index, and mapping
    model = SentenceTransformer(MODEL_NAME)
    index = faiss.read_index(str(INDEX_PATH))
    with MAPPING_PATH.open("r", encoding="utf-8") as f:
        text_mapping = json.load(f)

    # 2. Create an embedding for the query
    query_embedding = model.encode([query]).astype("float32")

    # 3. Perform the search
    distances, indices = index.search(query_embedding, top_k)

    # 4. Retrieve and format the results
    results = []
    for i in range(len(indices[0])):
        idx = indices[0][i]
        if idx != -1:  # FAISS returns -1 for no result
            dist = distances[0][i]
            text = text_mapping[idx]
            results.append(f"[Relevance: {1 - dist:.2f}] {text}")

    if not results:
        return "No relevant information found in knowledge base via semantic search."

    return "Found the following relevant entries in my memory:\n\n" + "\n\n".join(
        results
    )


@register_tool(
    name="query_knowledge_base",
    input_model=KnowledgeQueryInput,
    description="Queries the agent's long-term memory (indexed logs and documents) to find relevant context or past examples.",
    category="LLM",
    tags=["rag", "memory", "internal", "llm"],
    safe_mode=True,
    purpose="Search past experiences to inform current decisions.",
)
def query_knowledge_base(input_data: KnowledgeQueryInput) -> str:
    """
    Performs a search for relevant information in the agent's memory.

    It will attempt to use a pre-built FAISS vector index for fast semantic
    search. If the index or required libraries are not found, it will fall
    back to a simple keyword search across the raw log files.
    """
    logger.info(f"Querying knowledge base with: '{input_data.query}'")

    if VECTOR_SEARCH_ENABLED and INDEX_PATH.exists() and MAPPING_PATH.exists():
        try:
            return _semantic_search(input_data.query, input_data.top_k)
        except Exception as e:
            logger.exception(
                f"Semantic search failed. Falling back to keyword search. Error: {e}"
            )
            return _fallback_keyword_search(input_data.query, input_data.top_k)
    else:
        if not VECTOR_SEARCH_ENABLED:
            logger.warning(
                "Dependencies for vector search not installed (faiss, sentence-transformers)."
            )
        else:
            logger.warning(f"Memory index not found at '{INDEX_PATH}'.")
        return _fallback_keyword_search(input_data.query, input_data.top_k)
