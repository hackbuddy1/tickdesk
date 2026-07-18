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

### API latency (200 req, 10 concurrent, 1000-row payload / 92 KB)

| Stage | p50 | p99 | mean |
|---|---|---|---|
| Redis cache, dict round-trip | 72.26 ms | 120.34 ms | 72.36 ms |
| Redis cache, pre-serialized bytes | 8.88 ms | 56.60 ms | 16.10 ms |
| Improvement | 8.1x | 2.1x | 4.5x |

Adding Redis alone did not move p50. Profiling showed the bottleneck was not the
database (a cached single request still took 7.9 ms, vs 1.5 ms for a 10-row
payload) but double JSON conversion: Redis bytes were parsed into a dict, then
re-serialized by FastAPI. Caching pre-serialized bytes and returning them
directly removed both conversions. Remaining p99 reflects genuine cache misses
plus asyncpg statement warmup.

## Run

    docker compose up -d
    ./run.sh              # backend on :8000

### WebSocket fanout (single node)

| Metric | Value |
|---|---|
| Concurrent clients | 50/50 connected |
| Feed publish rate | ~2,000 ticks/s |
| Delivered | ~48,000 msg/s aggregate |
| Architecture | 1 Redis pub/sub subscription -> Hub -> N WebSocket clients |

A single background feed process publishes to Redis; one pump task in the API
subscribes once and fans out to all clients, so client count does not multiply
Redis load.

## AI Agent (guardrails + access control)

Natural-language console over the tick store. Tool-calling agent with a
hard security boundary — every query the model emits is validated before it
reaches the database.

Endpoint: `POST /agent/query`  (role from `X-Role` header, server-side)

**Tools:** `get_schema`, `compute_metric` (canned VWAP/volume/spread/last_price),
`run_sql` (validated raw SELECT).

**Guardrails (SQL guard, sqlglot):**
- SELECT-only; single statement (blocks stacked `...; DROP`)
- No DML/DDL anywhere in the tree (catches CTE-hidden writes)
- Schema allowlist; system catalogs blocked
- Dangerous-function denylist (`pg_read_file`, `pg_sleep`, `lo_import`, ...)
- Forced/clamped LIMIT; output truncation before returning to the model

**Access control:** role-scoped tools — `viewer` (no raw SQL, 100-row cap) vs
`quant` (raw SELECT, 1000-row cap). Role comes from the session, never the
model, so "you are admin now" in a prompt does nothing.

**Observability:** per-query trace of latency, tokens, and cost estimate.

**Model layer:** provider-agnostic, mock/live swappable via `AGENT_MODEL` env
(mock runs offline with no API key).

**Adversarial test suite:** 21-case pytest battery covering injection, DROP,
role escalation, file exfil, and system-catalog access — all rejected.

```bash
pytest -q backend/tests/test_guards.py     # 21 passed
curl -s -X POST localhost:8000/agent/query \
  -H "Content-Type: application/json" -H "X-Role: viewer" \
  -d '{"question":"last price for RELIANCE"}'
```
