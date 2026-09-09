"""Embedding helpers.

The model is loaded lazily and cached so that ingest.py and retriever.py
share a single instance instead of loading ~90 MB of weights twice.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Sequence

import numpy as np

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBED_DIM = 384  # must match the vector(384) column in kb_chunks


@lru_cache(maxsize=1)
def _model():
    # imported lazily so that importing this module stays cheap
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME)


def embed_many(texts: Sequence[str], show_progress: bool = False) -> np.ndarray:
    """Embed a batch of texts. Vectors are L2-normalised."""
    return _model().encode(
        list(texts),
        batch_size=32,
        show_progress_bar=show_progress,
        normalize_embeddings=True,
    )


def embed_one(text: str) -> list[float]:
    return embed_many([text])[0].tolist()


def to_pgvector(vec) -> str:
    """Render a vector in pgvector's text input format: '[0.1,0.2,...]'."""
    return "[" + ",".join(f"{float(x):.6f}" for x in vec) + "]"
