"""Load the RAG corpus, embed it, and write it into kb_chunks.

Run from the project root:

    python -m rag.ingest

The whole table is rewritten on every run, so the corpus files on disk are
always the source of truth.
"""
from __future__ import annotations

import asyncio
import glob
import os
import sys
from pathlib import Path

import asyncpg
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rag.embed import embed_many, to_pgvector  # noqa: E402

CORPUS = Path(__file__).parent / "corpus"
DSN = os.environ.get(
    "DATABASE_URL", "postgresql://tick:tick@localhost:5433/tickdesk"
)


def load_schema_chunks() -> list[dict]:
    """One chunk per table card. The whole card is both content and embed text."""
    out = []
    for path in sorted(glob.glob(str(CORPUS / "schema" / "*.md"))):
        text = Path(path).read_text(encoding="utf-8")
        out.append(
            {
                "kind": "schema",
                "title": Path(path).stem,
                "content": text,
                "embed_text": text,
            }
        )
    return out


def load_glossary_chunks() -> list[dict]:
    """One chunk per business term.

    Aliases go into embed_text but not into content: they help the retriever
    match the user's wording without cluttering the prompt.
    """
    terms = yaml.safe_load((CORPUS / "glossary.yaml").read_text(encoding="utf-8"))
    out = []
    for t in terms:
        aliases = " ".join(t.get("aliases", []))
        out.append(
            {
                "kind": "glossary",
                "title": t["term"],
                "content": (
                    f"Term: {t['term']}\n"
                    f"Definition: {t['definition']}\n"
                    f"SQL: {t['sql_hint']}"
                ),
                 "embed_text": (
                    f"{t['term']} {aliases} {t['definition']} {t['sql_hint']}"
                ),
            }
        )
    return out


def load_example_chunks() -> list[dict]:
    """One chunk per question/SQL pair.

    Only the question is embedded. Embedding the SQL too would pull the vector
    towards keyword soup (SELECT, FROM, GROUP BY) that every example shares.
    """
    examples = yaml.safe_load((CORPUS / "examples.yaml").read_text(encoding="utf-8"))
    out = []
    for i, ex in enumerate(examples):
        out.append(
            {
                "kind": "example",
                "title": f"example_{i:03d}",
                "content": f"Question: {ex['question']}\nSQL:\n{ex['sql'].strip()}",
                "embed_text": ex["question"],
            }
        )
    return out


async def main() -> None:
    chunks = load_schema_chunks() + load_glossary_chunks() + load_example_chunks()

    by_kind: dict[str, int] = {}
    for c in chunks:
        by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
    print(f"Loaded {len(chunks)} chunks: {by_kind}")

    print("Embedding...")
    vectors = embed_many([c["embed_text"] for c in chunks], show_progress=True)

    conn = await asyncpg.connect(DSN)
    try:
        async with conn.transaction():
            await conn.execute("TRUNCATE kb_chunks RESTART IDENTITY")
            await conn.executemany(
                """INSERT INTO kb_chunks (kind, title, content, embed_text, embedding)
                   VALUES ($1, $2, $3, $4, $5::vector)""",
                [
                    (
                        c["kind"],
                        c["title"],
                        c["content"],
                        c["embed_text"],
                        to_pgvector(v),
                    )
                    for c, v in zip(chunks, vectors)
                ],
            )
    finally:
        await conn.close()

    print(f"Ingested {len(chunks)} chunks into kb_chunks.")


if __name__ == "__main__":
    asyncio.run(main())
