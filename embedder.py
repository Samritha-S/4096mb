"""
embedder.py — Attach embedding vectors to Chunk objects.

Supports two backends (set via EMBEDDING_BACKEND env var):
  • "gemini"  — Gemini text-embedding-004 via REST API (no SDK required)
  • "local"   — sentence-transformers all-MiniLM-L6-v2  (fully offline)
"""

from __future__ import annotations

import logging
import os
import time
from typing import List

from chunker import Chunk

logger = logging.getLogger(__name__)

_GEMINI_BATCH_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/gemini-embedding-001:batchEmbedContents"
)


def _embed_gemini(texts: List[str], api_key: str, batch_size: int = 20) -> List[List[float]]:
    """
    Embed texts using the Gemini batchEmbedContents REST endpoint in batches.
    Handles rate-limiting (429) with exponential back-off up to 30s.
    """
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    session.verify = False  # captive portal injects self-signed cert on this network
    embeddings: List[List[float]] = []

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        requests_payload = [
            {
                "model": "models/gemini-embedding-001",
                "content": {"parts": [{"text": t}]},
                "taskType": "RETRIEVAL_DOCUMENT",
            }
            for t in batch
        ]
        payload = {"requests": requests_payload}

        for attempt in range(8):
            try:
                resp = session.post(
                    _GEMINI_BATCH_EMBED_URL,
                    params={"key": api_key},
                    json=payload,
                    timeout=60,
                )
                if resp.status_code == 429:
                    wait = min(60, (2 ** attempt) * 2 + 5)
                    logger.warning(
                        "Gemini rate limit (429) on batch [%d:%d], attempt %d/8 — sleeping %ds for quota recovery",
                        start, start + len(batch), attempt + 1, wait,
                    )
                    time.sleep(wait)
                    continue

                if not resp.ok:
                    raise ValueError(f"HTTP {resp.status_code}: {resp.text[:200]}")

                data = resp.json()
                for item in data.get("embeddings", []):
                    embeddings.append(item["values"])
                break
            except Exception as exc:
                wait = min(60, 2 ** attempt + 3)
                logger.warning(
                    "Gemini embed attempt %d/8 failed for batch [%d:%d]: %s — retrying in %ds",
                    attempt + 1, start, start + len(batch), exc, wait,
                )
                time.sleep(wait)
        else:
            logger.error("All retries failed for batch [%d:%d]; inserting empty vectors.", start, start + len(batch))
            embeddings.extend([[] for _ in batch])

        # Small politeness delay between batches to respect RPM limits
        time.sleep(0.5)

    return embeddings


# ── Local backend ─────────────────────────────────────────────────────────────

_local_model = None  # module-level cache — load once


def _embed_local(texts: List[str]) -> List[List[float]]:
    """
    Embed texts using sentence-transformers all-MiniLM-L6-v2 (offline).
    Model is downloaded on first call (~90 MB) and cached by HuggingFace.
    """
    global _local_model
    if _local_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info("Loading sentence-transformers model (first call may download ~90 MB)…")
        _local_model = SentenceTransformer("all-MiniLM-L6-v2")

    vecs = _local_model.encode(texts, show_progress_bar=False, convert_to_numpy=True)
    return [v.tolist() for v in vecs]


# ── Public API ────────────────────────────────────────────────────────────────

def embed_chunks(
    chunks: List[Chunk],
    backend: str = "gemini",
    batch_size: int = 32,
) -> List[Chunk]:
    """
    Attach embedding vectors to each Chunk in-place and return the list.

    Args:
        chunks:     List of Chunk objects (embedding field is None on input).
        backend:    "gemini" or "local".
        batch_size: Number of texts per embedding call (used by local backend).

    Returns:
        The same list with .embedding filled in.
    """
    if not chunks:
        return chunks

    api_key = os.getenv("GEMINI_API_KEY", "")

    if backend == "gemini":
        if not api_key:
            raise EnvironmentError(
                "EMBEDDING_BACKEND=gemini but GEMINI_API_KEY is not set.\n"
                "Either set the key or switch to EMBEDDING_BACKEND=local in .env"
            )
        texts = [c.text for c in chunks]
        embeddings = _embed_gemini(texts, api_key)
        for chunk, vec in zip(chunks, embeddings):
            chunk.embedding = vec

    elif backend == "local":
        texts = [c.text for c in chunks]
        # Process in batches to avoid OOM on large repos
        all_vecs: List[List[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            all_vecs.extend(_embed_local(batch))
        for chunk, vec in zip(chunks, all_vecs):
            chunk.embedding = vec

    else:
        raise ValueError(
            f"Unknown EMBEDDING_BACKEND={backend!r}. Choose 'gemini' or 'local'."
        )

    return chunks
