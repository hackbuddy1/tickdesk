import asyncio
import time
import websockets

URL = "ws://localhost:8000/ws/feed"
CLIENTS = 50
DURATION = 10


async def client(idx, counts):
    try:
        async with websockets.connect(URL) as ws:
            t_end = time.perf_counter() + DURATION
            n = 0
            while time.perf_counter() < t_end:
                await asyncio.wait_for(ws.recv(), timeout=2)
                n += 1
            counts[idx] = n
    except Exception:
        counts[idx] = -1


async def main():
    counts = [0] * CLIENTS
    t0 = time.perf_counter()
    await asyncio.gather(*(client(i, counts) for i in range(CLIENTS)))
    dt = time.perf_counter() - t0
    ok = [c for c in counts if c >= 0]
    total = sum(ok)
    print(f"clients      {len(ok)}/{CLIENTS} connected")
    print(f"duration     {dt:.1f}s")
    print(f"msgs total   {total:,}")
    print(f"msgs/client  {total // max(len(ok), 1):,}")
    print(f"fanout rate  {total / dt:,.0f} msg/s delivered")


if __name__ == "__main__":
    asyncio.run(main())
