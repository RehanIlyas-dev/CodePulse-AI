import hashlib
import json
from typing import Optional, Dict, Any
from app.core import redis as redis_module

def _client():
    return redis_module.redis_client

class CacheService:
    @staticmethod
    def generate_code_hash(code: str, language: str) -> str:
        
        # Generate a SHA-256 hash based on the normalized code and language to use as a cache key
        normalized_code = code.strip()
        normalized_lang = language.lower().strip()
        
        payload = f"{normalized_lang}:{normalized_code}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    async def get_cached_analysis(code_hash: str, key_prefix: str = "analysis:") -> Optional[Dict[str, Any]]:
       
        # Queries Redis for an existing analysis payload matching the SHA-256 code_hash.
        # Returns a parsed dictionary on a cache hit, or None on a cache miss.
        client = _client()
        if client is None:
            return None

        cached_json = await client.get(f"{key_prefix}{code_hash}")
        if cached_json:
            return json.loads(cached_json)
        
        return None

    @staticmethod
    async def set_cached_analysis(
        code_hash: str, 
        data: Dict[str, Any], 
        ttl_seconds: int = 86400,
        key_prefix: str = "analysis:"
    ) -> None:
        """
        Stores the analysis result dictionary in Redis serialized as JSON.
        Sets a Time-To-Live (TTL) in seconds (default: 24 hours).
        """
        if _client() is not None:
            serialized_data = json.dumps(data)
            await _client().set(
                name=f"{key_prefix}{code_hash}",
                value=serialized_data,
                ex=ttl_seconds
            )