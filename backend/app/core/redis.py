import logging
import os
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

redis_client: aioredis.Redis | None = None

async def init_redis():

    # Initialize the Redis client and VERIFY connectivity. redis-py is lazy:
    # from_url() never dials the server, so without an explicit ping a dead
    # URL yields a client object that raises ConnectionError on first use.
    # On failure we set the client to None so every `if client:` guard in the
    # codebase degrades gracefully (cache/jobs/rate-limit simply no-op).
    global redis_client
    try:
        client = aioredis.from_url(
            REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
        await client.ping()
        redis_client = client
        logger.info("Redis connected at %s", REDIS_URL)
    except Exception as exc:
        logger.warning("Redis unavailable (%s) — caching, job tracking and rate limiting are disabled.", exc)
        redis_client = None

async def close_redis():
    # Close the Redis client connection if it has been initialized
    global redis_client
    if redis_client:
        await redis_client.aclose()
        redis_client = None