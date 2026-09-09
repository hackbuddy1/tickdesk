"""Hybrid retrieval over kb_chunks.

Two independent arms run against the same table:

  * a vector arm  (cosine distance over MiniLM embeddings)
  * a keyword arm (Postgres full-text ts_rank)

Pure vector search is weak on exact tokens -- column names, tickers, status
values like 'REJECTED' -- because those carry little semantic signal. Pure
keyword search misses paraphrases. Running both and fusing the ranks covers
each one's blind spot.
"""
from __future__ import annotations

from dataclasses import dataclass

import asyncpg

from .embed import embed_one, to_pgvector

RRF_K = 10 # standard smoothing constant from the RRF paper
CANDIDATES = 30  # how many rows each arm returns before fusion


@dataclass
class Chunk:
    id: int
    kind: str
    title: str
    content: str
    score: float


async def _vector_arm(
    conn: asyncpg.Connection, question: str, limit: int
) -> list[asyncpg.Record]:
    vec = to_pgvector(embed_one(question))
    return await conn.fetch(
        """SELECT id, kind, title, content
             FROM kb_chunks
            ORDER BY embedding <=> $1::vector
            LIMIT $2""",
        vec,
        limit,
    )


async def _keyword_arm(
    conn: asyncpg.Connection, question: str, limit: int
) -> list[asyncpg.Record]:
    """Lexical arm.

    plainto_tsquery ANDs every term, so "fill rate by desk" only matches a
    chunk containing all of fill, rate and desk -- on a 46-chunk corpus that
    returned one row for almost every question, leaving fusion effectively
    vector-only. Ranking by ts_rank over an OR of the terms keeps the arm
    alive while still ordering by how many terms hit.
    """
    return await conn.fetch(
        """WITH q AS (
               SELECT to_tsquery(
                   'english',
                   array_to_string(
                       ARRAY(
                           SELECT lexeme
                             FROM unnest(to_tsvector('english', $1))
                       ), ' | '
                   )
               ) AS tsq
           )
           SELECT id, kind, title, content
             FROM kb_chunks, q
            WHERE q.tsq IS NOT NULL
              AND tsv @@ q.tsq
            ORDER BY ts_rank(tsv, q.tsq) DESC
            LIMIT $2""",
        question,
        limit,
    )


def _rrf(*ranked_lists: list[asyncpg.Record]) -> list[Chunk]:
    """Reciprocal Rank Fusion: score = sum over lists of 1 / (RRF_K + rank).

    Fusing on rank rather than raw score matters here: cosine distance and
    ts_rank live on different scales and adding them directly would let one
    arm dominate for reasons that have nothing to do with relevance.
    """
    scores: dict[int, float] = {}
    seen: dict[int, asyncpg.Record] = {}

    for rows in ranked_lists:
        for rank, row in enumerate(rows, start=1):
            scores[row["id"]] = scores.get(row["id"], 0.0) + 1.0 / (RRF_K + rank)
            seen.setdefault(row["id"], row)

    merged = [
        Chunk(
            id=r["id"],
            kind=r["kind"],
            title=r["title"],
            content=r["content"],
            score=scores[r["id"]],
        )
        for r in seen.values()
    ]
    merged.sort(key=lambda c: c.score, reverse=True)
    return merged


async def retrieve(
    conn: asyncpg.Connection,
    question: str,
    k_schema: int = 3,
    k_glossary: int = 2,
    k_example: int = 3,
) -> dict[str, list[Chunk]]:
    """Retrieve context for one question, fusing per kind.

    Fusing globally and then slicing per kind starves the smaller buckets:
    examples dominate the merged list because there are three times as many
    of them, so schema cards fall off the end. Ranking within each kind and
    then taking top-k keeps every bucket full.
    """
    vec_rows = await _vector_arm(conn, question, CANDIDATES)
    kw_rows = await _keyword_arm(conn, question, CANDIDATES)

    quotas = {"schema": k_schema, "glossary": k_glossary, "example": k_example}
    picked: dict[str, list[Chunk]] = {}

    for kind, k in quotas.items():
        v = [r for r in vec_rows if r["kind"] == kind]
        w = [r for r in kw_rows if r["kind"] == kind]
        picked[kind] = _rrf(v, w)[:k]

    return picked
