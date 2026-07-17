import os

DSN = os.getenv("DSN", "postgresql://tick:tick@localhost:5433/tickdesk")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

POOL_MIN = int(os.getenv("POOL_MIN", "5"))
POOL_MAX = int(os.getenv("POOL_MAX", "20"))

CACHE_TTL = int(os.getenv("CACHE_TTL", "60"))
MAX_ROWS = int(os.getenv("MAX_ROWS", "5000"))
