"""Backoff de RedisManager tras un fallo (PR-03.2, linea 331 del plan).

Tras una excepcion en una operacion, `get` no vuelve a llamar al cliente durante
30 segundos. El reloj se controla parcheando `time` dentro de `redis_config`.
"""

import types

import pytest
import redis_config
from redis_config import RedisManager

from tests.fakes import FakeRedisClient

BACKOFF_SECONDS = 30
START = 1000.0


class _CountingFailingRedis(FakeRedisClient):
    """FakeRedisClient que falla siempre y cuenta las llamadas a `get`."""

    def __init__(self):
        super().__init__(raise_errors=True)
        self.get_calls = 0

    def get(self, key):
        self.get_calls += 1
        return super().get(key)


class _FakeClock:
    def __init__(self, now: float):
        self.now = now

    def __call__(self) -> float:
        return self.now


@pytest.fixture
def clock(monkeypatch) -> _FakeClock:
    fake_clock = _FakeClock(START)
    monkeypatch.setattr(
        redis_config,
        "time",
        types.SimpleNamespace(monotonic=fake_clock),
        raising=False,
    )
    return fake_clock


@pytest.fixture
def failing_client() -> _CountingFailingRedis:
    return _CountingFailingRedis()


@pytest.fixture
def manager(failing_client) -> RedisManager:
    instance = RedisManager()
    instance._client = failing_client
    return instance


def test_get_returns_none_after_failure(manager, clock):
    assert manager.get("access:u:c") is None


def test_get_does_not_call_client_again_during_30_seconds_after_failure(
    manager, clock, failing_client
):
    manager.get("access:u:c")
    assert failing_client.get_calls == 1

    clock.now = START + BACKOFF_SECONDS - 0.001
    assert manager.get("access:u:c") is None

    assert failing_client.get_calls == 1


def test_get_retries_client_after_30_seconds(manager, clock, failing_client):
    manager.get("access:u:c")
    assert failing_client.get_calls == 1

    clock.now = START + BACKOFF_SECONDS + 0.5
    assert manager.get("access:u:c") is None

    assert failing_client.get_calls == 2


def test_failed_retry_reopens_the_30_second_window(manager, clock, failing_client):
    manager.get("access:u:c")
    clock.now = START + BACKOFF_SECONDS + 0.5
    manager.get("access:u:c")
    assert failing_client.get_calls == 2

    clock.now = START + BACKOFF_SECONDS + 0.5 + BACKOFF_SECONDS - 0.001
    manager.get("access:u:c")

    assert failing_client.get_calls == 2
