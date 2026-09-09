# Table: positions_eod

Purpose: End-of-day net position and average cost per account and symbol.
Rows: ~120

## Columns
- as_of (date) — the trading day
- account_id (integer)
- symbol (text)
- net_qty (integer) — signed: positive is long, negative is short
- avg_cost (double precision) — volume-weighted average cost

## Query guidance
- Primary key is (as_of, account_id, symbol).
- net_qty is signed. "Largest position" usually means ABS(net_qty).
- Position value = net_qty * avg_cost (cost basis), not market value.

## Relationships
- positions_eod.account_id -> accounts.account_id
- positions_eod.symbol -> instruments.symbol