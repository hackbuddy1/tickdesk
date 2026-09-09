# Table: ticks

Purpose: Raw trade prints. One row per trade, with top-of-book bid/ask at that moment.
Rows: ~5,000,000
Type: TimescaleDB hypertable, partitioned on `ts`

## Columns
- ts (timestamptz) — trade timestamp. Partition key.
- symbol (text) — instrument ticker
- price (double precision) — traded price
- qty (integer) — quantity traded in this print
- bid (double precision) — best bid at print time
- ask (double precision) — best ask at print time

## Query guidance
- ALWAYS filter on a `ts` range, otherwise the planner scans every chunk.
- For anything longer than a few minutes, prefer `bars_1s` over raw ticks.
- Spread = ask - bid, computed per row then averaged.

## Relationships
- ticks.symbol -> instruments.symbol