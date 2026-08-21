import os
import redis.asyncio as aioredis

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0") 

redis_client: aioredis.Redis | None = None

async def init_redis():
    
    # Initialize the Redis client with the provided URL and set encoding options
    global redis_client
    redis_client = aioredis.from_url(
        REDIS_URL, 
        encoding="utf-8", 
        decode_responses=True
    )

async def close_redis():
    # Close the Redis client connection if it has been initialized
    global redis_client
    if redis_client:
        await redis_client.aclose()