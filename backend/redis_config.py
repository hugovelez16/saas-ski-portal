import logging
import os

import redis

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RedisManager:
    """
    Manages Redis connections and operations with failover support.
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self._pool: redis.ConnectionPool | None = None
        self._client: redis.Redis | None = None

    @property
    def client(self) -> redis.Redis:
        """
        Lazy-loads the Redis client with a connection pool.
        """
        if self._client is None:
            try:
                logger.info(f"Initializing Redis connection pool to {self.redis_url}")
                self._pool = redis.ConnectionPool.from_url(
                    self.redis_url,
                    decode_responses=True,
                    socket_timeout=2.0,
                    socket_connect_timeout=2.0,
                    retry_on_timeout=True,
                )
                self._client = redis.Redis(connection_pool=self._pool)
            except Exception as e:
                logger.error(f"Failed to initialize Redis client: {e}")
                # We return a dummy client or handle it in the methods
        return self._client

    def get(self, key: str) -> str | None:
        """
        Safely gets a value from Redis. Returns None on failure or miss.
        """
        try:
            client = self.client
            if client:
                return client.get(key)
        except Exception as e:
            logger.error(f"Redis GET error for key {key}: {e}")
        return None

    def set(self, key: str, value: str, ex: int = 3600) -> bool:
        """
        Safely sets a value in Redis with an optional expiration (TTL).
        """
        try:
            client = self.client
            if client:
                return client.set(key, value, ex=ex)
        except Exception as e:
            logger.error(f"Redis SET error for key {key}: {e}")
        return False

    def delete(self, key: str) -> bool:
        """
        Safely deletes a key from Redis.
        """
        try:
            client = self.client
            if client:
                return client.delete(key) > 0
        except Exception as e:
            logger.error(f"Redis DELETE error for key {key}: {e}")
        return False

    def ping(self) -> bool:
        """
        Checks if Redis is alive.
        """
        try:
            return self.client.ping()
        except Exception:
            return False


# Global instance
redis_manager = RedisManager()
