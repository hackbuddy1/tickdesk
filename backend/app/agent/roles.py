"""Role-scoped access control.
Role hi decide karta hai model ko kaunse tools milenge aur kitni rows.
Role authenticated session se set hota hai — request body ya user ke message se
NAHI. Isliye prompt me 'pretend you are admin' se kuch nahi milta."""
from dataclasses import dataclass
from typing import FrozenSet


@dataclass(frozen=True)
class Role:
    name: str
    tools: FrozenSet[str]
    max_limit: int


# viewer: sirf canned metrics + schema. Raw SQL nahi.
VIEWER = Role("viewer", frozenset({"get_schema", "compute_metric"}), max_limit=100)

# quant: sab kuch, including validated raw SELECT.
QUANT = Role("quant", frozenset({"get_schema", "compute_metric", "run_sql"}), max_limit=1000)

ROLES = {r.name: r for r in (VIEWER, QUANT)}


def get_role(name: str) -> Role:
    if name not in ROLES:
        raise ValueError(f"unknown role: {name!r}")
    return ROLES[name]
