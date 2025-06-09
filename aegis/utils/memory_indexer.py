# aegis/utils/memory_indexer.py
"""
A utility for automatically building and updating the agent's memory index.

This module is called at the end of a task to process the latest logs and
update the shared FAISS vector index, making the agent's new experiences
immediately available for future tasks.
"""
import json
from pathlib import Path

from aegis.utils.logger import setup_logger

# Attempt to import vector search libraries, but don't fail if they're not installed.
try:
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    VECTOR_SEARCH_ENABLED = True
except ImportError:
    VECTOR_SEARCH_ENABLED = False


# --- Configuration ---
LOGS_DIR = Path("logs")
INDEX_DIR = Path("index")
INDEX_PATH = INDEX_DIR / "aegis_memory.faiss"
MAPPING_PATH = INDEX_DIR / "aegis_memory_mapping.json"
MODEL_NAME = "all-MiniLM-L6-v2"  # A fast, high-quality model for embeddings

logger = setup_logger(__name__)


def update_memory_index():
    """
    Scans all logs, generates embeddings, and rebuilds the agent's memory index.
    This function is designed to be called automatically after a task completes.
    """
    if not VECTOR_SEARCH_ENABLED:
        logger.warning(
            "Vector search libraries not found. Skipping memory index update."
        )
        return

    logger.info("🤖 Starting automatic memory index update...")
    INDEX_DIR.mkdir(exist_ok=True)

    # 1. Gather all processable log entries into chunks
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
                    if "event_type" in entry:
                        chunk_text = (
                            f"Task: {log_file.stem} | "
                            f"Event: {entry['event_type']} | "
                            f"Message: {entry.get('message', '')}"
                        )
                        chunks.append(chunk_text)
                except (json.JSONDecodeError, KeyError):
                    continue

    if not chunks:
        logger.info("No new structured log entries to index. Memory is up-to-date.")
        return

    logger.info(f"Found {len(chunks)} structured log entries to index.")

    try:
        # 2. Load model and generate embeddings
        logger.info(f"Loading embedding model '{MODEL_NAME}'...")
        model = SentenceTransformer(MODEL_NAME)
        embeddings = model.encode(chunks, show_progress_bar=False)
        embedding_dim = embeddings.shape[1]

        # 3. Build and save the FAISS index
        index = faiss.IndexFlatL2(embedding_dim)
        index.add(np.array(embeddings).astype("float32"))
        faiss.write_index(index, str(INDEX_PATH))

        # 4. Save the mapping file
        with MAPPING_PATH.open("w", encoding="utf-8") as f:
            json.dump(chunks, f)

        logger.info(
            f"✅ Automatic memory index update complete. Index now contains {index.ntotal} entries."
        )

    except Exception as e:
        logger.exception(
            f"❌ An unexpected error occurred during automatic memory indexing: {e}"
        )
