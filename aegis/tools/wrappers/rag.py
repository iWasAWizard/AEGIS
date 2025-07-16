# aegis/tools/wrappers/rag.py
"""
A tool for providing Retrieval-Augmented Generation (RAG) capabilities.

This allows the agent to query its own long-term memory, which is stored
as structured logs, to inform its planning process.
"""
import json
from pathlib import Path

from pydantic import BaseModel, Field

from aegis.exceptions import ToolExecutionError
from aegis.registry import register_tool
from aegis.utils.config import get_config
from aegis.utils.logger import setup_logger

try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    VECTOR_SEARCH_ENABLED = True
except ImportError:
    VECTOR_SEARCH_ENABLED = False
    # Log this at module load time so it's clear if dependencies are missing
    setup_logger(__name__).warning(
        "faiss-cpu or sentence-transformers not installed. RAG semantic search will be disabled. "
        "Tool will fallback to keyword search or fail if logs are also unavailable."
    )

logger = setup_logger(__name__)

# Load paths and model from central config
config = get_config()
RAG_CONFIG = config.get("rag", {})
PATHS_CONFIG = config.get("paths", {})

LOGS_DIR = Path(PATHS_CONFIG.get("logs", "logs"))
INDEX_DIR = Path(PATHS_CONFIG.get("index", "index"))
MODEL_NAME = RAG_CONFIG.get("embedding_model", "all-MiniLM-L6-v2")
INDEX_PATH = INDEX_DIR / RAG_CONFIG.get("index_filename", "aegis_memory.faiss")
MAPPING_PATH = INDEX_DIR / RAG_CONFIG.get(
    "mapping_filename", "aegis_memory_mapping.json"
)


class KnowledgeQueryInput(BaseModel):
    """Input model for querying the agent's knowledge base.

    :ivar query: A natural language question about a past task, error, tool, or concept.
    :vartype query: str
    :ivar top_k: The maximum number of relevant log entries to return.
    :vartype top_k: int
    """

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
    """Performs a simple keyword search if vector search is unavailable.

    :param query: The search query string.
    :type query: str
    :param top_k: The number of results to return.
    :type top_k: int
    :return: A formatted string of search results.
    :rtype: str
    :raises ToolExecutionError: If there's an issue accessing the log directory.
    """
    logger.warning("Falling back to basic keyword search for RAG query.")
    logger.debug(f"Logs directory for keyword search: {LOGS_DIR.resolve()}")
    if not LOGS_DIR.exists() or not LOGS_DIR.is_dir():
        msg = f"Knowledge base (logs directory) not found or not a directory at '{LOGS_DIR.resolve()}'."
        logger.error(msg)
        raise ToolExecutionError(msg)

    matches = []
    files_scanned_count = 0
    try:
        for log_file in LOGS_DIR.glob("*.jsonl"):
            files_scanned_count += 1
            logger.debug(f"Keyword searching in file: {log_file.name}")
            try:
                with log_file.open("r", encoding="utf-8") as f:
                    for line_num, line in enumerate(f, 1):
                        if query.lower() in line.lower():
                            matches.append(
                                f"- Log: {log_file.name}, Line: {line_num}: {line.strip()}"
                            )
            except Exception as e:
                logger.error(
                    f"Could not process log file {log_file} during keyword search: {e}"
                )
        logger.debug(
            f"Keyword search scanned {files_scanned_count} files and found {len(matches)} potential matches."
        )
    except Exception as e:
        logger.exception(
            f"Error while globbing or iterating log files for keyword search: {e}"
        )
        raise ToolExecutionError(
            f"An error occurred during keyword search directory traversal: {e}"
        )

    if not matches:
        return "No relevant information found in knowledge base via keyword search."

    return "Found the following relevant entries (via keyword search):\n\n" + "\n".join(
        matches[-top_k:]
    )


def _semantic_search(query: str, top_k: int) -> str:
    """Performs a semantic vector search using a FAISS index.

    :param query: The search query string.
    :type query: str
    :param top_k: The number of results to return.
    :type top_k: int
    :return: A formatted string of search results with relevance scores.
    :rtype: str
    :raises ToolExecutionError: If the model, index, or mapping cannot be loaded or queried.
    """
    logger.info("Performing semantic search with FAISS index.")
    try:
        model = SentenceTransformer(MODEL_NAME)
        if not INDEX_PATH.exists():
            raise ToolExecutionError(
                f"FAISS index file not found at {INDEX_PATH}. Run memory indexer."
            )
        index = faiss.read_index(str(INDEX_PATH))

        if not MAPPING_PATH.exists():
            raise ToolExecutionError(
                f"FAISS mapping file not found at {MAPPING_PATH}. Run memory indexer."
            )
        with MAPPING_PATH.open("r", encoding="utf-8") as f:
            text_mapping = json.load(f)

        query_embedding = model.encode([query]).astype("float32")
        distances, indices = index.search(query_embedding, top_k)

        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if idx != -1:
                dist = distances[0][i]
                try:
                    text_content = text_mapping.get(str(idx))
                    if text_content is not None:
                        results.append(f"[Relevance: {1 - dist:.2f}] {text_content}")
                    else:
                        logger.warning(
                            f"Index {idx} found in FAISS but missing in mapping file."
                        )
                except (KeyError, IndexError):
                    logger.warning(
                        f"Index {idx} from FAISS search not found in mapping file."
                    )

        if not results:
            return (
                "No relevant information found in knowledge base via semantic search."
            )
        return "Found the following relevant entries in my memory:\n\n" + "\n\n".join(
            results
        )
    except Exception as e:
        logger.exception(f"Semantic search failed internally: {e}")
        raise ToolExecutionError(f"Semantic search failed: {e}")


@register_tool(
    name="query_knowledge_base",
    input_model=KnowledgeQueryInput,
    description="Queries the agent's long-term memory (indexed logs) to find relevant context or past examples.",
    category="LLM",
    tags=[
        "rag",
        "memory",
        "internal",
        "llm",
    ],
    safe_mode=True,
    purpose="Search past experiences to inform current decisions.",
)
def query_knowledge_base(input_data: KnowledgeQueryInput) -> str:
    """Performs a search for relevant information in the agent's memory.

    It will attempt to use a pre-built FAISS vector index for fast semantic
    search. If the index or required libraries are not found, it will fall
    back to a simple keyword search across the raw log files.

    :param input_data: The query and number of results to return.
    :type input_data: KnowledgeQueryInput
    :return: A string containing the search results.
    :rtype: str
    :raises ToolExecutionError: If semantic search fails critically or keyword search cannot access logs.
    """
    logger.info(
        f"Querying knowledge base with: '{input_data.query}' (top_k={input_data.top_k})"
    )

    if VECTOR_SEARCH_ENABLED and INDEX_PATH.exists() and MAPPING_PATH.exists():
        try:
            logger.info("Attempting semantic search for knowledge query.")
            return _semantic_search(input_data.query, input_data.top_k)
        except ToolExecutionError as e:
            logger.warning(
                f"Semantic search failed: {e}. Falling back to keyword search."
            )
    else:
        if not VECTOR_SEARCH_ENABLED:
            logger.warning(
                "Dependencies for vector search not installed (faiss-cpu, sentence-transformers)."
            )
        if not INDEX_PATH.exists():
            logger.warning(f"Memory index file not found at '{INDEX_PATH.resolve()}'.")
        if not MAPPING_PATH.exists():
            logger.warning(
                f"Memory mapping file not found at '{MAPPING_PATH.resolve()}'."
            )

    logger.info("Proceeding with keyword search as fallback.")
    return _fallback_keyword_search(input_data.query, input_data.top_k)
