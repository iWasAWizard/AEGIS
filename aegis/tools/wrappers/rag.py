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
    setup_logger(__name__).warning(  # Use setup_logger directly for early logging
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
    """
    logger.warning("Falling back to basic keyword search for RAG query.")
    logger.debug(f"Logs directory for keyword search: {LOGS_DIR.resolve()}")
    if not LOGS_DIR.exists():
        logger.error(
            f"No knowledge base (logs directory) found at '{LOGS_DIR.resolve()}' for keyword search."
        )
        return f"No knowledge base (logs directory) found at '{LOGS_DIR}'. Cannot perform keyword search."

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
        return (
            f"[ERROR] An error occurred during keyword search directory traversal: {e}"
        )

    if not matches:
        return "No relevant information found in knowledge base via keyword search."

    # Return the most recent matches (from potentially later files or later in files)
    # This is a simple heuristic; true recency would need timestamp parsing.
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
        logger.debug(f"Attempting to load SentenceTransformer model: '{MODEL_NAME}'")
        model = SentenceTransformer(MODEL_NAME)
        logger.debug(f"SentenceTransformer model '{MODEL_NAME}' loaded successfully.")

        logger.debug(f"Attempting to read FAISS index from: {INDEX_PATH.resolve()}")
        index = faiss.read_index(str(INDEX_PATH))
        logger.debug(
            f"FAISS index loaded successfully. Index contains {index.ntotal} vectors."
        )

        logger.debug(f"Attempting to read mapping file from: {MAPPING_PATH.resolve()}")
        with MAPPING_PATH.open("r", encoding="utf-8") as f:
            text_mapping = json.load(f)
        logger.debug(
            f"Mapping file loaded successfully. Contains {len(text_mapping)} entries."
        )

        if not isinstance(text_mapping, list) and not (
            isinstance(text_mapping, dict)
            and all(isinstance(k, str) and k.isdigit() for k in text_mapping.keys())
        ):
            logger.error(
                f"Mapping file {MAPPING_PATH} is not a list or a dict with stringified integer keys. Type: {type(text_mapping)}"
            )
            raise ToolExecutionError(
                f"Invalid format in mapping file {MAPPING_PATH}. Expected list or dict of int-keyed strings."
            )

        logger.debug(f"Encoding query for semantic search: '{query}'")
        query_embedding = model.encode([query]).astype("float32")
        logger.debug("Query encoding complete.")

        logger.debug(f"Searching FAISS index for top {top_k} results.")
        distances, indices = index.search(query_embedding, top_k)
        logger.debug(
            f"FAISS search complete. Found indices: {indices}, distances: {distances}"
        )

        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if idx != -1:  # -1 means no more valid results for that query vector
                dist = distances[0][i]
                try:
                    # Handle if text_mapping is a list (older way) or dict (newer robust way from memory_indexer)
                    if isinstance(text_mapping, list):
                        text_content = text_mapping[idx]
                    elif isinstance(
                        text_mapping, dict
                    ):  # Current memory_indexer saves a dict with string keys '0', '1', ...
                        text_content = text_mapping.get(str(idx))
                    else:  # Should have been caught by earlier check
                        text_content = None

                    if text_content is not None:
                        results.append(f"[Relevance: {1 - dist:.2f}] {text_content}")
                    else:
                        logger.warning(
                            f"Index {idx} found in FAISS but missing in mapping file. This might indicate an outdated mapping file."
                        )
                except IndexError:
                    logger.warning(
                        f"Index {idx} out of bounds for text_mapping list (size {len(text_mapping)}). Possible index/mapping mismatch."
                    )
                except KeyError:
                    logger.warning(
                        f"Key '{str(idx)}' not found in text_mapping dictionary. Possible index/mapping mismatch."
                    )
            else:
                logger.debug(
                    f"FAISS index search returned -1 at position {i}, indicating fewer than top_k results."
                )

        if not results:
            return (
                "No relevant information found in knowledge base via semantic search."
            )
        return "Found the following relevant entries in my memory:\n\n" + "\n\n".join(
            results
        )
    except FileNotFoundError as e:
        logger.error(
            f"Required file not found during semantic search: {e.filename}. Full error: {e}"
        )
        raise ToolExecutionError(
            f"Semantic search setup error: A required file ({e.filename}) was not found. Ensure index is built."
        ) from e
    except Exception as e:
        logger.exception(f"Semantic search failed internally: {e}")
        raise ToolExecutionError(f"Semantic search failed: {e}") from e


@register_tool(
    name="query_knowledge_base",
    input_model=KnowledgeQueryInput,
    description="Queries the agent's long-term memory (indexed logs) to find relevant context or past examples.",
    category="LLM",  # Changed from "RAG" to "LLM" as it assists the LLM
    tags=[
        "rag",
        "memory",
        "internal",
        "llm",
    ],  # "internal" as it queries agent's own data
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
    """
    print("DEBUG RAG: query_knowledge_base FUNCTION ENTERED", flush=True)
    logger.info(
        f"Querying knowledge base with: '{input_data.query}' (top_k={input_data.top_k})"
    )
    logger.debug(f"VECTOR_SEARCH_ENABLED: {VECTOR_SEARCH_ENABLED}")
    logger.debug(f"INDEX_PATH ({INDEX_PATH.resolve()}) exists: {INDEX_PATH.exists()}")
    logger.debug(
        f"MAPPING_PATH ({MAPPING_PATH.resolve()}) exists: {MAPPING_PATH.exists()}"
    )

    if VECTOR_SEARCH_ENABLED and INDEX_PATH.exists() and MAPPING_PATH.exists():
        try:
            logger.info("Attempting semantic search for knowledge query.")
            return _semantic_search(input_data.query, input_data.top_k)
        except ToolExecutionError as e:
            logger.warning(
                f"Semantic search failed with ToolExecutionError: {e}. Falling back to keyword search."
            )
            return _fallback_keyword_search(input_data.query, input_data.top_k)
        except (
            Exception
        ) as e:  # Catch any other unexpected error during the semantic search attempt
            logger.exception(
                f"Unexpected error during semantic search attempt, before fallback: {e}"
            )
            logger.warning(
                "Falling back to keyword search due to unexpected error in semantic search."
            )
            return _fallback_keyword_search(input_data.query, input_data.top_k)
    else:
        if not VECTOR_SEARCH_ENABLED:
            logger.warning(
                "Dependencies for vector search not installed (faiss-cpu, sentence-transformers). Cannot perform semantic search."
            )
        if not INDEX_PATH.exists():
            logger.warning(
                f"Memory index file not found at '{INDEX_PATH.resolve()}'. Cannot perform semantic search."
            )
        if not MAPPING_PATH.exists():
            logger.warning(
                f"Memory mapping file not found at '{MAPPING_PATH.resolve()}'. Cannot perform semantic search."
            )

        logger.info(
            "Proceeding with keyword search due to missing components for semantic search."
        )
        return _fallback_keyword_search(input_data.query, input_data.top_k)
