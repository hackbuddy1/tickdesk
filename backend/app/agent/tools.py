"""Agent tools + dispatch.
Guard ke upar do aur guardrails:
  * dispatch() role tool-membership dobara check karta hai -> jailbroken model jo
    tool uske paas nahi tha, execute nahi kar payega.
  * compute_metric params validate karta hai (symbol regex, int window), phir bhi
    SQL guard se guzarta hai (belt + suspenders).
Output model ko wapas jaane se pehle truncate hota hai."""
from __future__ import annotations
import re
from typing import Awaitable, Callable, List, Dict, Any

from .guards import validate_and_rewrite, SQLGuardError
from .roles import Role
from .schema import ALLOWED_TABLES, render_schema

Executor = Callable[[str], Awaitable[List[Dict[str, Any]]]]

_SYMBOL_RE = re.compile(r"^[A-Z0-9.\-]{1,12}$")
MAX_ROWS_TO_MODEL = 200

# canned safe metrics. {sym} regex-validated, {w} int-cast, tab templating.
_METRICS = {
    "last_price": "SELECT symbol, price, ts FROM ticks "
                  "WHERE symbol='{sym}' ORDER BY ts DESC LIMIT 1",
    "vwap":       "SELECT symbol, sum(price*qty)/nullif(sum(qty),0) AS vwap FROM ticks "
                  "WHERE symbol='{sym}' AND ts > now() - interval '{w} seconds' GROUP BY symbol",
    "volume":     "SELECT symbol, sum(qty) AS volume FROM ticks "
                  "WHERE symbol='{sym}' AND ts > now() - interval '{w} seconds' GROUP BY symbol",
    "range":      "SELECT symbol, max(high) AS hi, min(low) AS lo FROM bars_1s "
                  "WHERE symbol='{sym}' AND bucket > now() - interval '{w} seconds' GROUP BY symbol",
    "spread":     "SELECT symbol, avg(ask-bid) AS avg_spread FROM ticks "
                  "WHERE symbol='{sym}' AND ts > now() - interval '{w} seconds' GROUP BY symbol",
}


def tool_specs(role: Role) -> list[dict]:
    """Anthropic tool-format specs, role ke allowed tools tak filtered."""
    all_specs = {
        "get_schema": {
            "name": "get_schema",
            "description": "Return the columns and description of tables you can query.",
            "input_schema": {"type": "object", "properties": {}},
        },
        "compute_metric": {
            "name": "compute_metric",
            "description": "Compute a safe pre-defined metric for one symbol.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "metric": {"type": "string", "enum": list(_METRICS)},
                    "symbol": {"type": "string", "description": "e.g. AAPL"},
                    "window_s": {"type": "integer", "description": "lookback seconds", "default": 60},
                },
                "required": ["metric", "symbol"],
            },
        },
        "run_sql": {
            "name": "run_sql",
            "description": "Run a single read-only SELECT on ticks / bars_1s. "
                           "No writes, no DDL, no server-side functions. LIMIT enforced.",
            "input_schema": {
                "type": "object",
                "properties": {"sql": {"type": "string"}},
                "required": ["sql"],
            },
        },
    }
    return [all_specs[t] for t in all_specs if t in role.tools]


class Tools:
    def __init__(self, role: Role, execute: Executor):
        self.role = role
        self._execute = execute

    async def dispatch(self, name: str, args: dict) -> Any:
        # access control: jo tool role ke paas nahi, refuse — model ne jo bhi kiya ho.
        if name not in self.role.tools:
            return {"error": f"role '{self.role.name}' is not permitted to use '{name}'"}
        try:
            handler = getattr(self, f"_t_{name}")
            return await handler(**args)
        except (SQLGuardError, ValueError) as e:
            return {"error": str(e)}

    async def _t_get_schema(self) -> dict:
        return {"schema": render_schema(ALLOWED_TABLES)}

    async def _t_run_sql(self, sql: str) -> dict:
        safe = validate_and_rewrite(sql, ALLOWED_TABLES, self.role.max_limit)
        rows = await self._execute(safe)
        return _truncate(rows, safe)

    async def _t_compute_metric(self, metric: str, symbol: str, window_s: int = 60) -> dict:
        if metric not in _METRICS:
            raise ValueError(f"unknown metric: {metric}")
        if not _SYMBOL_RE.match(symbol):
            raise ValueError("invalid symbol")
        window_s = int(window_s)
        if not (1 <= window_s <= 86400):
            raise ValueError("window_s out of range")
        sql = _METRICS[metric].format(sym=symbol, w=window_s)
        safe = validate_and_rewrite(sql, ALLOWED_TABLES, self.role.max_limit)
        rows = await self._execute(safe)
        return _truncate(rows, safe)


def _truncate(rows: List[Dict[str, Any]], sql: str) -> dict:
    total = len(rows)
    return {
        "sql": sql,
        "row_count": total,
        "truncated": total > MAX_ROWS_TO_MODEL,
        "rows": rows[:MAX_ROWS_TO_MODEL],
    }
