import json
import logging
from typing import Any, Optional

import redis.asyncio as redis

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Async Redis client for caching.
    """

    _instance: Optional["RedisClient"] = None
    _redis: Optional[redis.Redis] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
        return cls._instance

    async def connect(self, redis_url: str):
        """Initialize the Redis connection."""
        if self._redis is None:
            try:
                self._redis = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                await self._redis.ping()
                logger.info("Successfully connected to Redis.")
            except Exception as e:
                logger.error(f"Failed to connect to Redis at {redis_url}: {e}")
                self._redis = None
                raise

    async def get(self, key: str) -> Optional[Any]:
        """Get a value from Redis."""
        if not self._redis:
            return None
        try:
            value = await self._redis.get(key)
            if value:
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    return value
            return None
        except Exception as e:
            logger.error(f"Error getting key {key} from Redis: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set a value in Redis with an optional TTL (seconds)."""
        if not self._redis:
            return
        try:
            serialized_value = json.dumps(value) if not isinstance(value, str) else value
            await self._redis.set(key, serialized_value, ex=ttl)
        except Exception as e:
            logger.error(f"Error setting key {key} in Redis: {e}")

    async def delete(self, key: str):
        """Delete a key from Redis."""
        if not self._redis:
            return
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.error(f"Error deleting key {key} from Redis: {e}")

    async def close(self):
        """Close the Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            logger.info("Redis connection closed.")


# Global instance
redis_client = RedisClient()
