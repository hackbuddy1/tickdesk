from contextlib import asynccontextmanager
from datetime import datetime

import orjson
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import Response

from app import cache, db
from app.config import MAX_ROWS


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.disconnect()


app = FastAPI(
    title="TickDesk API",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    async with db.pool.acquire() as con:
        await con.fetchval("SELECT 1")
    await db.rds.ping()
    return {"status": "ok"}


@app.get("/symbols")
async def symbols():
    async def loader():
        async with db.pool.acquire() as con:
            rows = await con.fetch("SELECT DISTINCT symbol FROM ticks ORDER BY 1")
        return [r["symbol"] for r in rows]

    key = cache.make_key("symbols")
    value, hit = await cache.get_or_set(key, loader, ttl=3600)
    return {"symbols": value, "cached": hit}


@app.get("/ticks")
async def ticks(
    symbol: str = Query(..., min_length=1, max_length=20),
    start: datetime = Query(...),
    end: datetime = Query(...),
    limit: int = Query(1000, ge=1, le=MAX_ROWS),
):
    if end <= start:
        raise HTTPException(400, "end must be after start")

    async def loader():
        async with db.pool.acquire() as con:
            rows = await con.fetch(
                """
                SELECT ts, price, qty, bid, ask
                FROM ticks
                WHERE symbol = $1 AND ts >= $2 AND ts <= $3
                ORDER BY ts
                LIMIT $4
                """,
                symbol, start, end, limit,
            )
        return [
            {
                "ts": r["ts"].isoformat(),
                "price": r["price"],
                "qty": r["qty"],
                "bid": r["bid"],
                "ask": r["ask"],
            }
            for r in rows
        ]

    key = cache.make_key("ticks", s=symbol, a=start.isoformat(), b=end.isoformat(), l=limit)
    payload, hit = await cache.get_or_set_raw(key, loader)
    return Response(
        content=payload,
        media_type="application/json",
        headers={"X-Cache": "HIT" if hit else "MISS"},
    )


@app.get("/bars")
async def bars(
    symbol: str = Query(..., min_length=1, max_length=20),
    start: datetime = Query(...),
    end: datetime = Query(...),
    limit: int = Query(1000, ge=1, le=MAX_ROWS),
):
    if end <= start:
        raise HTTPException(400, "end must be after start")

    async def loader():
        async with db.pool.acquire() as con:
            rows = await con.fetch(
                """
                SELECT bucket, open, high, low, close, volume, vwap, n_ticks
                FROM bars_1s
                WHERE symbol = $1 AND bucket >= $2 AND bucket <= $3
                ORDER BY bucket
                LIMIT $4
                """,
                symbol, start, end, limit,
            )
        return [
            {
                "t": r["bucket"].isoformat(),
                "o": r["open"],
                "h": r["high"],
                "l": r["low"],
                "c": r["close"],
                "v": r["volume"],
                "vwap": r["vwap"],
                "n": r["n_ticks"],
            }
            for r in rows
        ]

    key = cache.make_key("bars", s=symbol, a=start.isoformat(), b=end.isoformat(), l=limit)
    value, hit = await cache.get_or_set(key, loader)
    return {"symbol": symbol, "count": len(value), "cached": hit, "bars": value}


@app.get("/stats/spread")
async def spread(start: datetime = Query(...), end: datetime = Query(...)):
    if end <= start:
        raise HTTPException(400, "end must be after start")

    async def loader():
        async with db.pool.acquire() as con:
            rows = await con.fetch(
                """
                SELECT symbol,
                       avg(ask - bid)              AS avg_spread,
                       avg((ask - bid) / price)    AS avg_rel_spread,
                       count(*)                    AS n
                FROM ticks
                WHERE ts >= $1 AND ts <= $2
                GROUP BY symbol
                ORDER BY avg_spread DESC
                """,
                start, end,
            )
        return [dict(r) for r in rows]

    key = cache.make_key("spread", a=start.isoformat(), b=end.isoformat())
    value, hit = await cache.get_or_set(key, loader)
    return {"cached": hit, "rows": value}


@app.post("/admin/flush")
async def flush():
    n = 0
    async for k in db.rds.scan_iter(match="td:*", count=500):
        await db.rds.delete(k)
        n += 1
    return {"flushed": n}
