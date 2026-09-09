"""Compare baseline (full schema dump) vs retrieved context size."""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import asyncpg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app.agent.schema import render_schema  # noqa: E402
from rag.prompt import build_context  # noqa: E402
from rag.retriever import retrieve  # noqa: E402

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
    baseline = render_schema()
    print(f"baseline (full schema dump): {len(baseline)} chars\n")

    conn = await asyncpg.connect(DSN)
    try:
        sizes = []
        for q in QUESTIONS:
            ctx = build_context(await retrieve(conn, q))
            sizes.append(len(ctx))
            print(f"{len(ctx):6d}  {q}")
        print(f"\nmean retrieved context: {sum(sizes) / len(sizes):.0f} chars")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())