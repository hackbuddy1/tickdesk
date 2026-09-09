# Table: bars_1s

Purpose: 1-second OHLCV continuous aggregate built over `ticks`. Use this for
any time-series/candle question instead of scanning raw ticks.
Type: TimescaleDB continuous aggregate (materialized view)

## Columns
- symbol (text) — instrument ticker
- bucket (timestamptz) — start of the 1-second bucket. Time column, NOT `ts`.
- open (double precision) — first trade price in the bucket
- high (double precision) — highest trade price
- low (double precision) — lowest trade price
- close (double precision) — last trade price
- volume (bigint) — total quantity traded in the bucket

## Query guidance
- Time column is `bucket`, not `ts`. This is the most common mistake.
- Intraday high/low over a period: MAX(high) / MIN(low), not MAX(close).
- For coarser candles use time_bucket('1 minute', bucket) and re-aggregate.

## Relationships
- bars_1s.symbol -> instruments.symbol