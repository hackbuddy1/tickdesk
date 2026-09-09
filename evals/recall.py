"""Retrieval recall@k over the golden set.

Measured separately from execution accuracy on purpose: when a question
fails end to end, this tells you whether the retriever failed to surface
the right table or the model failed to use what it was given.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import asyncpg
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag.retriever import retrieve  # noqa: E402

DSN = os.environ.get(
    "DATABASE_URL", "postgresql://tick:tick@localhost:5433/tickdesk"
)
GOLDEN = Path(__file__).parent / "golden_set.yaml"


async def main() -> None:
    cases = yaml.safe_load(GOLDEN.read_text(encoding="utf-8"))
    conn = await asyncpg.connect(DSN)

    full_hits = 0
    partial = 0
    misses: list[tuple[str, set[str], list[str]]] = []

    try:
        for case in cases:
            picked = await retrieve(conn, case["question"])
            got = [c.title for c in picked["schema"]]
            need = set(case["tables"])
            found = need & set(got)

            if found == need:
                full_hits += 1
            else:
                partial += len(found) / len(need)
                misses.append((case["id"], need - found, got))
    finally:
        await conn.close()

    n = len(cases)
    print(f"cases:            {n}")
    print(f"all tables found: {full_hits}/{n}  ({full_hits / n:.1%})")
    print(f"per-table recall: {(full_hits + partial) / n:.1%}")

    if misses:
        print(f"\nmissed ({len(misses)}):")
        for cid, missing, got in misses:
            print(f"  {cid}  missing={sorted(missing)}  got={got}")


if __name__ == "__main__":
    asyncio.run(main())