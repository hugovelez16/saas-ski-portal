"""Dobles de prueba para dependencias externas del backend."""

from fnmatch import fnmatchcase

import redis


class FakeRedisClient:
    """Sustituto en memoria de `redis.Redis` con la interfaz que usa `RedisManager`.

    Si `raise_errors` es True, todas las operaciones lanzan `redis.ConnectionError`
    para simular un Redis caido.
    """

    def __init__(self, raise_errors: bool = False):
        self.store: dict = {}
        self.ttl: dict = {}
        self.raise_errors = raise_errors

    def _check(self) -> None:
        if self.raise_errors:
            raise redis.ConnectionError("Redis no disponible (fake)")

    def get(self, key):
        self._check()
        return self.store.get(key)

    def set(self, key, value, ex=None, nx=False):
        self._check()
        if nx and key in self.store:
            return None
        self.store[key] = value
        if ex is not None:
            self.ttl[key] = ex
        else:
            self.ttl.pop(key, None)
        return True

    def delete(self, *keys) -> int:
        self._check()
        deleted = 0
        for key in keys:
            if key in self.store:
                del self.store[key]
                self.ttl.pop(key, None)
                deleted += 1
        return deleted

    def scan_iter(self, match=None, count=None):
        self._check()
        keys = list(self.store.keys())
        if match is not None:
            keys = [key for key in keys if fnmatchcase(key, match)]
        yield from keys

    def incr(self, key) -> int:
        self._check()
        value = int(self.store.get(key, 0)) + 1
        self.store[key] = str(value)
        return value

    def expire(self, key, seconds) -> bool:
        self._check()
        if key not in self.store:
            return False
        self.ttl[key] = seconds
        return True

    def ping(self) -> bool:
        self._check()
        return True
