"""
Generates embeddings for text chunks.

Primary:  OpenAI text-embedding-3-small (API)
Fallback: local sentence-transformers model (all-MiniLM-L6-v2)

If the primary embedder fails (network error, rate limit, missing/invalid
API key, timeout), we automatically fall back to the local model so
ingestion doesn't hard-fail. This is logged so it's visible during the
demo/review.
"""

import os
import logging
from typing import List, Tuple

logger = logging.getLogger("ingestion.embedder")

OPENAI_MODEL = "text-embedding-3-small"
FALLBACK_MODEL_NAME = "all-MiniLM-L6-v2"

_fallback_model = None  # lazy-loaded singleton


def _get_fallback_model():
    global _fallback_model
    if _fallback_model is None:
        from sentence_transformers import SentenceTransformer
        logger.info(f"Loading local fallback embedding model: {FALLBACK_MODEL_NAME}")
        _fallback_model = SentenceTransformer(FALLBACK_MODEL_NAME)
    return _fallback_model


def _embed_with_openai(texts: List[str]) -> List[List[float]]:
    from openai import OpenAI

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")

    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(model=OPENAI_MODEL, input=texts)
    return [item.embedding for item in response.data]


def _embed_with_fallback(texts: List[str]) -> List[List[float]]:
    model = _get_fallback_model()
    vectors = model.encode(texts, show_progress_bar=False)
    return [v.tolist() for v in vectors]


def embed_chunks(texts: List[str]) -> Tuple[List[List[float]], bool]:
    """
    Returns (embeddings, used_fallback).
    Tries the primary (OpenAI) embedder first; falls back to the local
    model automatically on any failure.
    """
    try:
        embeddings = _embed_with_openai(texts)
        return embeddings, False
    except Exception as e:
        logger.warning(f"Primary embedder failed ({e}). Falling back to local model.")
        try:
            embeddings = _embed_with_fallback(texts)
            return embeddings, True
        except Exception as fallback_error:
            logger.error(f"Fallback embedder also failed: {fallback_error}")
            raise
