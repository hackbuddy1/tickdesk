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
    "instruments": {
        "description": "reference data per tradable symbol: name, sector, exchange, lot and tick size",
        "columns": {
            "symbol": "text",
            "name": "text",
            "sector": "text",
            "exchange": "text",
            "currency": "text",
            "lot_size": "integer",
            "tick_size": "double precision",
            "listed_on": "date",
        },
    },
    "accounts": {
        "description": "trading accounts, one per desk",
        "columns": {
            "account_id": "integer",
            "name": "text",
            "desk": "text",
            "base_currency": "text",
            "opened_on": "date",
        },
    },
    "orders": {
        "description": "submitted orders with side, type, quantity and lifecycle status",
        "columns": {
            "order_id": "bigint",
            "ts": "timestamptz",
            "account_id": "integer",
            "symbol": "text",
            "side": "text",
            "order_type": "text",
            "limit_price": "double precision",
            "qty": "integer",
            "status": "text",
        },
    },
    "fills": {
        "description": "executions against orders, with fill price, quantity and fee",
        "columns": {
            "fill_id": "bigint",
            "order_id": "bigint",
            "ts": "timestamptz",
            "symbol": "text",
            "price": "double precision",
            "qty": "integer",
            "fee": "double precision",
        },
    },
    "positions_eod": {
        "description": "end-of-day net position and average cost per account and symbol",
        "columns": {
            "as_of": "date",
            "account_id": "integer",
            "symbol": "text",
            "net_qty": "integer",
            "avg_cost": "double precision",
        },
    },
    "corporate_actions": {
        "description": "splits, dividends and mergers with ex-dates per symbol",
        "columns": {
            "action_id": "integer",
            "symbol": "text",
            "ex_date": "date",
            "action_type": "text",
            "ratio": "double precision",
            "cash_amount": "double precision",
            "note": "text",
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