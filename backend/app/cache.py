import hashlib
import orjson

from app.config import CACHE_TTL
from app import db

def make_key(prefix: str, **parts) -> str:
    raw = orjson.dumps(parts, option=orjson.OPT_SORT_KEYS)
    h = hashlib.sha1(raw).hexdigest()[:16]
    return f"td:{prefix}:{h}"

async def get_or_set(key: str, loader, ttl: int = CACHE_TTL):
    hit = await db.rds.get(key)
    if hit is not None:
        return orjson.loads(hit), True
    value = await loader()
    await db.rds.setex(key, ttl, orjson.dumps(value))
    return value, False

async def get_or_set_raw(key: str, loader, ttl: int = CACHE_TTL) -> tuple[bytes, bool]:
    hit = await db.rds.get(key)
    if hit is not None:
        return hit, True
    payload = orjson.dumps(await loader())
    await db.rds.setex(key, ttl, payload)
    return payload, False
