import asyncio
import os
from datetime import datetime, timedelta, timezone

import asyncpg
import numpy as np

DSN = os.getenv("DSN", "postgresql://tick:tick@localhost:5433/tickdesk")

SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "SBIN", "BHARTIARTL", "ITC", "LT", "KOTAKBANK",
    "AXISBANK", "HINDUNILVR", "BAJFINANCE", "MARUTI", "SUNPHARMA",
    "TITAN", "WIPRO", "NESTLEIND", "ULTRACEMCO", "TATAMOTORS",
]

TICKS_PER_SYMBOL = 250_000
SESSION_START = datetime(2026, 7, 16, 3, 45, tzinfo=timezone.utc)
SESSION_SECONDS = 22_500


def make_rows(symbol, seed):
    rng = np.random.default_rng(seed)
    n = TICKS_PER_SYMBOL

    offsets = np.sort(rng.uniform(0, SESSION_SECONDS, n))
    log_ret = rng.normal(0, 1e-4, n)
    start = rng.uniform(150, 3200)
    price = np.round(start * np.exp(np.cumsum(log_ret)), 2)

    half_spread = np.round(price * 2.5e-5 + 0.005, 3)
    bid = np.round(price - half_spread, 2)
    ask = np.round(price + half_spread, 2)
    qty = rng.integers(1, 500, n)

    for i in range(n):
        yield (
            SESSION_START + timedelta(seconds=float(offsets[i])),
            symbol,
            float(price[i]),
            int(qty[i]),
            float(bid[i]),
            float(ask[i]),
        )


async def main():
    conn = await asyncpg.connect(DSN)
    cols = ["ts", "symbol", "price", "qty", "bid", "ask"]
    total = 0
    for i, sym in enumerate(SYMBOLS):
        await conn.copy_records_to_table(
            "ticks", records=make_rows(sym, seed=1000 + i), columns=cols
        )
        total += TICKS_PER_SYMBOL
        print(f"{sym:<12} loaded  ({total:,} total)")
    await conn.close()
    print("done")


if __name__ == "__main__":
    asyncio.run(main())
