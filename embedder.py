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

_DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "models/gemini-embedding-001")
_FALLBACK_GEMINI_MODEL = "models/gemini-embedding-2"


def _embed_gemini(texts: List[str], api_key: str, batch_size: int = 20) -> List[List[float]]:
    """
    Embed texts using the Gemini batchEmbedContents REST endpoint in batches.
    Handles rate-limiting (429) with exponential back-off and automatic fallback
    to gemini-embedding-2 (3072-dim) if the 1000/day free-tier quota is reached.
    """
    import requests
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    session = requests.Session()
    session.verify = False  # captive portal injects self-signed cert on this network
    embeddings: List[List[float]] = []

    model = _DEFAULT_GEMINI_MODEL

    # Probe model up front for daily quota exhaustion
    probe_url = f"https://generativelanguage.googleapis.com/v1beta/{model}:batchEmbedContents"
    probe_payload = {
        "requests": [{
            "model": model,
            "content": {"parts": [{"text": "probe"}]},
            "taskType": "RETRIEVAL_DOCUMENT",
        }]
    }
    try:
        pr = session.post(probe_url, params={"key": api_key}, json=probe_payload, timeout=10)
        if pr.status_code == 429 and ("PerDay" in pr.text or "daily" in pr.text.lower() or "limit: 1000" in pr.text):
            logger.warning(
                "Gemini '%s' daily quota limit reached. Falling back to '%s' (3072-dim).",
                model, _FALLBACK_GEMINI_MODEL,
            )
            model = _FALLBACK_GEMINI_MODEL
    except Exception as exc:
        logger.debug("Quota probe failed: %s; proceeding with %s", exc, model)

    embed_url = f"https://generativelanguage.googleapis.com/v1beta/{model}:batchEmbedContents"
    logger.info("Using Gemini embedding model: %s (dim=3072, batch_size=%d)", model, batch_size)

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        requests_payload = [
            {
                "model": model,
                "content": {"parts": [{"text": t}]},
                "taskType": "RETRIEVAL_DOCUMENT",
            }
            for t in batch
        ]
        payload = {"requests": requests_payload}

        for attempt in range(8):
            try:
                resp = session.post(
                    embed_url,
                    params={"key": api_key},
                    json=payload,
                    timeout=60,
                )
                if resp.status_code == 429:
                    err_text = resp.text
                    # If daily quota limit hit mid-run on primary model, switch to fallback
                    if model != _FALLBACK_GEMINI_MODEL and ("PerDay" in err_text or "limit: 1000" in err_text):
                        logger.warning(
                            "Gemini '%s' daily quota exhausted mid-run. Switching to '%s' (3072-dim).",
                            model, _FALLBACK_GEMINI_MODEL,
                        )
                        model = _FALLBACK_GEMINI_MODEL
                        embed_url = f"https://generativelanguage.googleapis.com/v1beta/{model}:batchEmbedContents"
                        for r_item in requests_payload:
                            r_item["model"] = model
                        continue

                    # Try to parse recommended retry delay from Google API response
                    wait = min(60, (2 ** attempt) * 2 + 5)
                    try:
                        err_json = resp.json()
                        for detail in err_json.get("error", {}).get("details", []):
                            delay_str = detail.get("retryDelay", "")
                            if delay_str.endswith("s"):
                                wait = max(wait, int(float(delay_str[:-1])) + 1)
                    except Exception:
                        pass

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

        # Small delay between batches to respect burst/RPM limits
        time.sleep(1.0)

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
