# aegis/utils/memory_indexer.py
"""
A utility for automatically building and updating the agent's memory index.

This module is called at the end of a task to process the latest logs and
update the shared FAISS vector index, making the agent's new experiences
immediately available for future tasks via Retrieval-Augmented Generation (RAG).
"""
import json
from pathlib import Path

from aegis.utils.config import get_config
from aegis.utils.logger import setup_logger

try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    VECTOR_SEARCH_ENABLED = True
except ImportError:
    VECTOR_SEARCH_ENABLED = False

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


def update_memory_index():
    """
    Scans all logs, generates embeddings, and rebuilds the agent's memory index.

    This function is designed to be called automatically after a task completes. It
    performs the following steps:
    1. Scans the `logs/` directory for all `.jsonl` files.
    2. Parses each file, extracting structured log entries that have an `event_type`.
    3. Formats these entries into text chunks.
    4. Uses a SentenceTransformer model to convert these chunks into vector embeddings.
    5. Builds a FAISS index from the embeddings for fast semantic search.
    6. Saves the FAISS index and a mapping file (from index ID to original text chunk).
    """
    if not VECTOR_SEARCH_ENABLED:
        logger.warning(
            "Vector search libraries (faiss-cpu, sentence-transformers) not found. Skipping memory index update."
        )
        return

    logger.info("🤖 Starting automatic memory index update...")
    INDEX_DIR.mkdir(exist_ok=True)

    if not LOGS_DIR.exists():
        logger.warning(f"Log directory not found at '{LOGS_DIR}'. Cannot update index.")
        return

    chunks = []
    log_files = list(LOGS_DIR.glob("*.jsonl"))
    for log_file in log_files:
        with log_file.open("r", encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    # We only index structured events that provide meaningful context
                    if "event_type" in entry:
                        chunk_text = (
                            f"Task: {log_file.stem} | "
                            f"Event: {entry['event_type']} | "
                            f"Message: {entry.get('message', '')}"
                        )
                        chunks.append(chunk_text)
                except (json.JSONDecodeError, KeyError):
                    # Ignore malformed lines or logs without an event_type
                    continue

    if not chunks:
        logger.info("No new structured log entries to index. Memory is up-to-date.")
        return

    logger.info(f"Found {len(chunks)} structured log entries to index.")

    try:
        # Load model and generate embeddings
        logger.info(f"Loading embedding model '{MODEL_NAME}'...")
        model = SentenceTransformer(MODEL_NAME)
        embeddings = model.encode(chunks, show_progress_bar=False)
        embedding_dim = embeddings.shape[1]

        # Build and save the FAISS index
        index = faiss.IndexFlatL2(embedding_dim)
        index.add(embeddings.astype(np.float32))
        faiss.write_index(index, str(INDEX_PATH))

        # Save the mapping file (from vector index to text chunk)
        # Store as a dictionary with integer index as key (stringified for JSON)
        # to allow non-contiguous indices if logs are deleted/re-indexed later.
        mapping_dict = {str(i): chunk for i, chunk in enumerate(chunks)}
        with MAPPING_PATH.open("w", encoding="utf-8") as f:
            json.dump(mapping_dict, f)

        logger.info(
            f"✅ Automatic memory index update complete. Index now contains {index.ntotal} entries."
        )

    except Exception as e:
        logger.exception(
            f"❌ An unexpected error occurred during automatic memory indexing: {e}"
        )
