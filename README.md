# TickDesk

Internal tick-data console with an AI agent layer, built over TimescaleDB.

## Stack

- TimescaleDB (Postgres 16) - 5M-row `ticks` hypertable, 1-hour chunks
- Continuous aggregate `bars_1s` - 1-second OHLCV + VWAP bars
- pgvector 0.8.0 - retrieval index for the agent's schema grounding
- Redis - query cache
- FastAPI (async, asyncpg) - REST + WebSocket
- React - live tape, charts, agent console

## Local setup

Host Postgres port: 5433 (5432 occupied by a local Postgres service)

    DSN = postgresql://tick:tick@localhost:5433/tickdesk

    docker compose up -d
    python scripts/seed.py
    docker compose exec -T db psql -U tick -d tickdesk -f /dev/stdin < db/post_seed.sql

The `db` service is built from `db/Dockerfile` rather than pulled directly, so
that pgvector is available alongside TimescaleDB. It is compiled with
`with_llvm=no`: pgxs looks for `clang-21`, the compiler the base image's
Postgres was built with, and Alpine only ships clang16/19. The JIT bitcode
that flag skips is an optional query optimisation, not part of the extension.

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

## Schema

Eight tables. `ticks` and `bars_1s` are the market data; the rest are the
order lifecycle and reference data the agent answers questions against.

| Table | Rows | What it holds |
|---|---|---|
| `ticks` | 5,000,000 | raw trade prints with top-of-book bid/ask |
| `bars_1s` | 449,991 | 1-second OHLCV continuous aggregate |
| `instruments` | 20 | reference data: sector, exchange, lot and tick size |
| `accounts` | 6 | trading accounts, one per desk |
| `orders` | 5,000 | side, type, quantity, lifecycle status |
| `fills` | 4,275 | executions against orders, with fee |
| `positions_eod` | 120 | end-of-day net position and average cost |
| `corporate_actions` | 16 | splits, dividends, mergers with ex-dates |

Two seeding bugs worth recording, since both produced data that looked
plausible until it was checked:

**All 5,000 orders came out BUY.** The seed drew `random()` into CTE columns
and read them three times — once for side, once for order type, once for
status. Postgres inlines non-recursive CTEs, so those columns were not
computed once and stored; the expression was re-evaluated per reference.
`WITH ... AS MATERIALIZED` fixes it. Distribution afterwards: 71% FILLED,
14% PARTIAL, 10% CANCELLED, 5% REJECTED, and BUY/SELL within a percent of even.

**Sectors were assigned by `hashtext()`.** This put HDFCBANK in Energy and ITC
in Financials. Any sector-grouped query returned correct SQL over nonsense
data. Replaced with a real NSE mapping across nine sectors.

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

Retrieval is not part of this boundary. Whatever the retriever surfaces, the
allowlist and SELECT-only checks run after generation and before execution,
so a retrieval miss can produce a wrong answer but never an unauthorised one.

## Retrieval layer (schema grounding)

The agent originally received the full schema on every call via
`render_schema()`. This layer replaces that with retrieved context: only the
tables, vocabulary and worked examples relevant to the question asked.

**Corpus** (46 chunks, hand-written, in `rag/corpus/`):

| Kind | Count | Contents |
|---|---|---|
| schema | 8 | columns, query guidance, foreign keys |
| glossary | 14 | VWAP, spread, fill rate, notional, and the SQL each maps to |
| example | 24 | question/SQL exemplars |

**Retrieval:** two arms over one `kb_chunks` table, fused with Reciprocal
Rank Fusion.

| Arm | Index | Covers |
|---|---|---|
| Vector | HNSW, pgvector, MiniLM-L6-v2 (384d) | paraphrase and intent |
| Lexical | GIN on a generated `tsvector` | exact tokens — column names, tickers, `REJECTED` |

Fusion is on rank, not score: cosine distance and `ts_rank` sit on different
scales, and adding them directly would let one arm dominate for reasons
unrelated to relevance.

Quotas are applied per kind (3 schema, 2 glossary, 3 examples) rather than
taking a global top-k. Examples outnumber schema cards three to one, so a
global cut regularly returned eight examples and no column names at all.

No separate vector store. The data is already in Postgres, and a second
system's operational cost is not justified by a 46-chunk corpus.

    python -m rag.ingest          # rebuild kb_chunks from rag/corpus/
    python -m rag.try_retrieve    # inspect what comes back for sample questions

### Evaluation

40-question golden set (`evals/golden_set.yaml`), disjoint from the exemplar
corpus — a question appearing in both would hand the model its own answer.
Each case records which tables a correct answer must touch, so a retrieval
failure can be told apart from a generation failure.

| Metric | Value |
|---|---|
| Questions retrieving every required table | 34/40 (85.0%) |
| Per-table recall | 94.2% |

    python -m evals.recall

Five of the six misses are the same table. Questions phrased around desks
("fees paid by each desk", "distinct symbols per desk") retrieve `accounts`
but not `orders` — even though `orders` carries the desk's actual activity
and `accounts` holds six rows of names. The lexical signal for "desk" lives
in the wrong card.

### What did not work

**Context size went up, not down.** The original goal was fewer prompt tokens.
Measured, it is the opposite:

| | Chars |
|---|---|
| Baseline (`render_schema()`, all 8 tables) | 1,560 |
| Retrieved context (mean over 40 questions) | 3,118 |

`render_schema()` emits one line per table. At eight tables the entire schema
is cheaper than three schema cards with their guidance attached. Retrieval
would need a far wider schema before it pays for itself on size — the claim
here is more useful context, not less of it.

**The lexical arm was dead for the first two iterations.**
`plainto_tsquery` ANDs every term, so "fill rate by desk" matched only chunks
containing all of *fill*, *rate* and *desk* — one row out of 46 for most
questions. Fusion was running, but it was fusing a 20-row list with a 1-row
list, which is vector search wearing a hat. Fixed by OR-ing the lexemes and
letting `ts_rank` handle ordering.

**RRF's standard K=60 flattens small corpora.** With `1/(60+rank)`, rank 1
scores 0.0164 and rank 15 scores 0.0139 — a ranking carrying almost no
information. K=60 is tuned for web-scale candidate lists. At K=10 the same
spread runs 0.091 to 0.038, and two questions moved their correct table into
first place.

**Shortening `embed_text` made recall worse.** `orders` (939 chars) is the
largest schema card and `accounts` (414) the smallest, so the hypothesis was
that long documents average out in embedding space and lose to short ones.
Embedding only the table name, purpose line and column names dropped recall
from 85.0% to 82.5% and broke two cases that previously passed. Reverted.

**Corpus drift is a silent failure.** The `instruments` card still described
sectors and exchanges from before the NSE mapping fix. Nothing errors — the
model reads `exchange: NASDAQ or NYSE`, filters on it, and returns zero rows.
In a retrieval system the corpus is as load-bearing as the code, and it has
no type checker.

### Not done

Execution accuracy is unmeasured. Recall says the right tables reach the
model; it does not say the model then writes correct SQL, and it is possible
the exemplars alone carry most of the benefit. That comparison needs a live
model across 40 questions in two configurations, and was cut for scope.
`run_agent()` takes a `schema_text` override so the two arms can be swapped
without touching the agent loop.
