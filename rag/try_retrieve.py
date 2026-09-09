"""Eyeball what the retriever returns for a few questions.

    python -m rag.try_retrieve

This is a smoke test, not the evaluation. It exists so you can see whether
retrieval is obviously broken before wiring it into the agent.
"""
from __future__ import annotations
from rag.prompt import build_context  

import asyncio
import os
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag.retriever import retrieve  

DSN = os.environ.get(
    "DATABASE_URL", "postgresql://tick:tick@localhost:5433/tickdesk"
)

QUESTIONS = [
    "what is our fill rate by desk",
    "vwap for RELIANCE in the last 5 minutes",
    "which banking stocks did we trade the most",
    "upcoming splits",
    "average spread on INFY",
    "largest net positions",
    "how many orders were rejected",
    "1 minute candles for TCS",
]


async def main() -> None:
    conn = await asyncpg.connect(DSN)
    try:
        for q in QUESTIONS[:1]:         
            picked = await retrieve(conn, q)
            context = build_context(picked)
            print(f"=== {q}\n")
            print(context)
            print(f"\n--- context length: {len(context)} chars")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
