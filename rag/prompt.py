"""Turn retrieved chunks into a prompt section."""
from __future__ import annotations

from .retriever import Chunk


def build_context(picked: dict[str, list[Chunk]], as_of: str | None = None) -> str:
    """Render retrieved chunks as a single grounding block.

    Order matters: schema first (the model needs column names before
    anything else is useful), then vocabulary, then worked examples.

    as_of pins what "now" means. The dataset is a fixed historical capture,
    so a query written against now() returns nothing; anchoring relative
    time to the latest tick keeps "today" and "the last hour" meaningful.
    """
    parts: list[str] = []

    if as_of:
        parts.append(
            f"## Current time\n\n"
            f"Treat the current time as {as_of}. This dataset ends there, so "
            f"write relative time filters against that timestamp rather than "
            f"now().\n"
        )

    if picked.get("schema"):
        parts.append("## Relevant tables\n")
        for c in picked["schema"]:
            parts.append(c.content.strip())
            parts.append("")

    if picked.get("glossary"):
        parts.append("## Terminology\n")
        for c in picked["glossary"]:
            parts.append(c.content.strip())
            parts.append("")

    if picked.get("example"):
        parts.append("## Similar questions answered before\n")
        for c in picked["example"]:
            parts.append(c.content.strip())
            parts.append("")

    return "\n".join(parts).strip()