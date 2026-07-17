# TickDesk

Internal tick-data console with an AI agent layer, built over TimescaleDB.

## Stack

- TimescaleDB (Postgres 16) - 5M-row `ticks` hypertable, 1-hour chunks
- Continuous aggregate `bars_1s` - 1-second OHLCV + VWAP bars
- Redis - query cache
- FastAPI (async, asyncpg) - REST + WebSocket
- React - live tape, charts, agent console

## Local setup

Host Postgres port: 5433 (5432 occupied by a local Postgres service)

    DSN = postgresql://tick:tick@localhost:5433/tickdesk

    docker compose up -d
    python scripts/seed.py
    docker compose exec -T db psql -U tick -d tickdesk -f /dev/stdin < db/post_seed.sql

## Benchmarks

### Ingest

| Metric | Value |
|---|---|
| Rows seeded | 5,000,000 (20 symbols x 250k) |
| Seed time | 11.7 s (~425k rows/sec) |
| Method | asyncpg copy_records_to_table (binary COPY) |
| Post-seed: index + CAGG refresh + ANALYZE | 14.4 s |
| Chunks | 7 (1-hour interval) |
| bars_1s rows | 449,991 |

Ingest tuning: composite index created after load, synchronous_commit=off,
max_wal_size=4GB, maintenance_work_mem=512MB.

### Query latency (cold, direct to Postgres)

| Query | Rows | Time |
|---|---|---|
| 5-min window, single symbol | 3,354 | 5.98 ms |
| 1-hour avg spread, 20 symbols | ~800k scanned | 56.65 ms |
| bars_1s count, single symbol | 22,498 | 8.18 ms |

Query plan confirms chunk exclusion: a 5-minute window touches 1 of 7 chunks
(Bitmap Index Scan on ticks_symbol_ts_idx, 1.24 ms execution).

Redis cache comparison: see Hour 3-6.
