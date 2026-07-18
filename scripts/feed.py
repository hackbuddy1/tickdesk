import asyncio
import os
import random
import signal
import time

import orjson
import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CHANNEL = "td:feed"
RATE = int(os.getenv("FEED_RATE", "2000"))

SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "SBIN", "BHARTIARTL", "ITC", "LT", "KOTAKBANK",
]

BASE = {
    "RELIANCE": 1420.0, "TCS": 3180.0, "HDFCBANK": 1680.0,
    "INFY": 1540.0, "ICICIBANK": 1180.0, "SBIN": 820.0,
    "BHARTIARTL": 1960.0, "ITC": 440.0, "LT": 3620.0, "KOTAKBANK": 1780.0,
}

stop = False


def handle_stop(*_):
    global stop
    stop = True


async def main():
    signal.signal(signal.SIGINT, handle_stop)
    signal.signal(signal.SIGTERM, handle_stop)

    rds = aioredis.from_url(REDIS_URL)
    await rds.ping()

    px = dict(BASE)
    batch_size = 50
    interval = batch_size / RATE
    sent = 0
    t_report = time.perf_counter()

    print(f"feed -> {CHANNEL} at ~{RATE}/s (ctrl-c to stop)", flush=True)

    while not stop:
        t0 = time.perf_counter()
        pipe = rds.pipeline()
        for _ in range(batch_size):
            sym = random.choice(SYMBOLS)
            px[sym] *= 1.0 + random.gauss(0, 8e-5)
            p = round(px[sym], 2)
            half = round(p * 2.5e-5 + 0.005, 3)
            msg = {
                "ts": time.time(),
                "symbol": sym,
                "price": p,
                "qty": random.randint(1, 500),
                "bid": round(p - half, 2),
                "ask": round(p + half, 2),
            }
            pipe.publish(CHANNEL, orjson.dumps(msg))
        await pipe.execute()
        sent += batch_size

        now = time.perf_counter()
        if now - t_report >= 5:
            print(f"  sent {sent:,}  ({sent / (now - t_report):.0f}/s)", flush=True)
            sent = 0
            t_report = now

        lag = interval - (time.perf_counter() - t0)
        if lag > 0:
            await asyncio.sleep(lag)

    await rds.aclose()
    print("feed stopped")


if __name__ == "__main__":
    asyncio.run(main())
