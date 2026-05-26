"""Embedding generation and vector similarity.

Generates text embeddings for document chunks and computes
cosine similarity for retrieval.

Uses numpy for vector math.  Production would use a dedicated
vector store (Pinecone, pgvector, Qdrant).
"""

from __future__ import annotations

import hashlib
from typing import Any

import numpy as np
import structlog

logger = structlog.get_logger()

# In-memory vector store: {id: {"embedding": np.array, "metadata": dict}}
_vectors: dict[str, dict[str, Any]] = {}


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


async def generate_embedding(text: str) -> np.ndarray:
    """Generate an embedding vector for a text chunk.

    Placeholder: uses a deterministic hash-based pseudo-embedding.
    Production replaces this with an actual embedding model call.
    """
    # Deterministic pseudo-embedding for development
    rng = np.random.default_rng(seed=int(_hash_text(text), 16) % (2**31))
    embedding = rng.standard_normal(256).astype(np.float32)
    return embedding / np.linalg.norm(embedding)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


async def store_embedding(text: str, metadata: dict | None = None) -> str:
    """Generate and store an embedding.  Returns the vector ID."""
    vec_id = _hash_text(text)
    embedding = await generate_embedding(text)
    _vectors[vec_id] = {"embedding": embedding, "metadata": metadata or {}, "text": text[:500]}
    return vec_id


async def search(query: str, k: int = 3) -> list[dict]:
    """Find the k most similar stored embeddings to a query."""
    if not _vectors:
        return []

    query_embedding = await generate_embedding(query)
    scored = []
    for vec_id, entry in _vectors.items():
        score = cosine_similarity(query_embedding, entry["embedding"])
        scored.append({"id": vec_id, "score": score, **entry})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:k]
