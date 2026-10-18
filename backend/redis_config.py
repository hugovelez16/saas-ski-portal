import logging
import os
import time

import redis

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

REDIS_BACKOFF_SECONDS = 30


class RedisManager:
    """
    Manages Redis connections and operations with failover support.
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")
        self._pool: redis.ConnectionPool | None = None
        self._client: redis.Redis | None = None
        # Tras un fallo no se reintenta hasta este instante (time.monotonic), para no esperar el timeout en cada llamada.
        self._down_until: float = 0.0

    def _in_backoff(self) -> bool:
        return time.monotonic() < self._down_until

    def _mark_down(self) -> None:
        self._down_until = time.monotonic() + REDIS_BACKOFF_SECONDS

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
        if self._in_backoff():
            return None
        try:
            client = self.client
            if client:
                return client.get(key)
        except Exception as e:
            self._mark_down()
            logger.error(f"Redis GET error for key {key}: {e}")
        return None

    def set(self, key: str, value: str, ex: int = 3600) -> bool:
        """
        Safely sets a value in Redis with an optional expiration (TTL).
        """
        if self._in_backoff():
            return False
        try:
            client = self.client
            if client:
                return client.set(key, value, ex=ex)
        except Exception as e:
            self._mark_down()
            logger.error(f"Redis SET error for key {key}: {e}")
        return False

    def delete(self, key: str) -> bool:
        """
        Safely deletes a key from Redis.
        """
        if self._in_backoff():
            return False
        try:
            client = self.client
            if client:
                return client.delete(key) > 0
        except Exception as e:
            self._mark_down()
            logger.error(f"Redis DELETE error for key {key}: {e}")
        return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Safely deletes keys matching a pattern from Redis.
        """
        deleted_count = 0
        if self._in_backoff():
            return deleted_count
        try:
            client = self.client
            if client:
                keys = list(client.scan_iter(match=pattern, count=100))
                if keys:
                    deleted_count = client.delete(*keys)
        except Exception as e:
            self._mark_down()
            logger.error(f"Redis DELETE_PATTERN error for pattern {pattern}: {e}")
        return deleted_count

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
