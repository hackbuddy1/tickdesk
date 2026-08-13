SCHEMA = {
    "ticks": {
        "description": "raw trade prints (~5M rows), TimescaleDB hypertable on ts",
        "columns": {
            "ts": "timestamptz",
            "symbol": "text",
            "price": "double precision",
            "qty": "integer",
            "bid": "double precision",
            "ask": "double precision",
        },
    },
    "bars_1s": {
        "description": "1-second OHLCV+VWAP continuous aggregate over ticks",
        "columns": {
            "symbol": "text",
            "bucket": "timestamptz",
            "open": "double precision",
            "high": "double precision",
            "low": "double precision",
            "close": "double precision",
            "volume": "bigint",
        },
    },
}

ALLOWED_TABLES = set(SCHEMA)


def render_schema(tables=None) -> str:
    tables = tables or ALLOWED_TABLES
    out = []
    for name in sorted(tables):
        t = SCHEMA[name]
        cols = ", ".join(f"{c} {typ}" for c, typ in t["columns"].items())
        out.append(f"{name}  -- {t['description']}\n    ({cols})")
    return "\n".join(out)
