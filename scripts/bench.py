import asyncio
import statistics
import sys
import time

import httpx

BASE = "http://localhost:8000"
N = 200
CONCURRENCY = 10

SYMBOLS = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK"]
START = "2026-07-16T04:00:00Z"
END = "2026-07-16T04:05:00Z"


def pct(xs, p):
    xs = sorted(xs)
    k = int(len(xs) * p / 100)
    return xs[min(k, len(xs) - 1)]


def report(name, lat):
    print(f"\n{name}")
    print(f"n{len(lat)}")
    print(f"mean{statistics.mean(lat):7.2f} ms")
    print(f"p50{pct(lat, 50):7.2f} ms")
    print(f"p95{pct(lat, 95):7.2f} ms")
    print(f"p99{pct(lat, 99):7.2f} ms")
    print(f"max{max(lat):7.2f} ms")


async def hit(client, sym, sem, lat):
    async with sem:
        t0 = time.perf_counter()
        r = await client.get(
            f"{BASE}/ticks",
            params={"symbol": sym, "start": START, "end": END, "limit": 1000},
        )
        dt = (time.perf_counter() - t0) * 1000
        r.raise_for_status()
        lat.append(dt)
        return r.headers.get("X-Cache") == "HIT"


async def run(client, label):
    sem = asyncio.Semaphore(CONCURRENCY)
    lat = []
    tasks = [hit(client, SYMBOLS[i % len(SYMBOLS)], sem, lat) for i in range(N)]
    flags = await asyncio.gather(*tasks)
    hits = sum(flags)
    report(f"{label}  (cache hits {hits}/{len(flags)})", lat)
    return lat


async def main():
    async with httpx.AsyncClient(timeout=30) as client:
        await client.post(f"{BASE}/admin/flush")
        cold = await run(client, "COLD  (cache empty)")
        warm = await run(client, "WARM  (cache primed)")

    c50, w50 = pct(cold, 50), pct(warm, 50)
    c99, w99 = pct(cold, 99), pct(warm, 99)
    print(f"\nspeedup  p50 {c50/w50:.1f}x   p99 {c99/w99:.1f}x")


if __name__ == "__main__":
    asyncio.run(main())
