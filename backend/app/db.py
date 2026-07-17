import asyncpg
import redis.asyncio as aioredis

from app.config import DSN, POOL_MAX, POOL_MIN, REDIS_URL

pool: asyncpg.Pool | None = None
rds: aioredis.Redis | None = None


async def connect():
    global pool, rds
    pool = await asyncpg.create_pool(
        DSN,
        min_size=POOL_MIN,
        max_size=POOL_MAX,
        command_timeout=10,
    )
    rds = aioredis.from_url(REDIS_URL, decode_responses=False)
    await rds.ping()


async def disconnect():
    if pool:
        await pool.close()
    if rds:
        await rds.aclose()
