from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class Role:
    name: str
    tools: FrozenSet[str]
    max_limit: int

VIEWER = Role("viewer", frozenset({"get_schema", "compute_metric"}), max_limit=100)
QUANT = Role("quant", frozenset({"get_schema", "compute_metric", "run_sql"}), max_limit=1000)

ROLES = {r.name: r for r in (VIEWER, QUANT)}
def get_role(name: str) -> Role:
    if name not in ROLES:
        raise ValueError(f"unknown role: {name!r}")
    return ROLES[name]
