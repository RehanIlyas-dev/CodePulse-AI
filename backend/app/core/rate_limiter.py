import time
from fastapi import HTTPException, Request, status
from app.core import redis as redis_module

class RateLimiter:
    def __init__(self, requests_per_minute: int = 10):
        self.requests_per_minute = requests_per_minute

    async def __call__(self, request: Request):
       
        # FastAPI dependency that checks the number of requests from a client IP in the current minute.
        client = redis_module.redis_client
        if client is None:
            return

        client_ip = request.client.host if request.client else "127.0.0.1"
        current_minute = int(time.time()) // 60 # Get the current minute timestamp
        rate_key = f"rate_limit:{client_ip}:{current_minute}"

        request_count = await client.incr(rate_key)
        
        if request_count == 1:
            await client.expire(rate_key, 60)

        # Reject request if limits are exceeded
        if request_count > self.requests_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {self.requests_per_minute} requests allowed per minute."
            )