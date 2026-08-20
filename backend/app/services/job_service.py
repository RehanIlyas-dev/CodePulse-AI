import json
from typing import Optional, Dict, Any
from app.core import redis as redis_module

def _client():
    return redis_module.redis_client

class JobService:
    @staticmethod
    async def create_job(job_id: str) -> None:
        # Initialize a new job entry in Redis with default status and progress.
        client = _client()
        if client:
            initial_state = {
                "status": "PENDING", 
                "progress": 0, 
                "data": None
            }
            # Key format: "job:<job_id>", Expire in 1 hour (3600 seconds)
            await client.set(f"job:{job_id}", json.dumps(initial_state), ex=3600)

    @staticmethod
    async def update_job(
        job_id: str, 
        status: str, 
        progress: int, 
        data: Optional[Dict[str, Any]] = None
    ) -> None:
      # Updates the status of an existing job in Redis, including progress percentage and any additional data.
        client = _client()
        if client:
            updated_state = {
                "status": status, 
                "progress": progress, 
                "data": data
            }
            await client.set(f"job:{job_id}", json.dumps(updated_state), ex=3600)

    @staticmethod
    async def get_job(job_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves current job state from Redis."""
        client = _client()
        if client:
            raw_data = await client.get(f"job:{job_id}")
            if raw_data:
                return json.loads(raw_data)
        return None