"""Unit tests for small infrastructure helpers: the Redis client factory
and structured logging setup. `Redis.from_url()` is lazy (no I/O happens
until a command is actually sent), so these are safe to run with no Redis
server available."""

from __future__ import annotations

import logging

from redis.asyncio import Redis

from app.core.logging import configure_logging
from app.core.redis import get_redis


def test_get_redis_returns_a_redis_client():
    client = get_redis()
    assert isinstance(client, Redis)


def test_get_redis_is_cached_across_calls():
    """`@lru_cache` means the whole process shares one connection pool
    instead of opening a new one per call site."""
    assert get_redis() is get_redis()


def test_configure_logging_installs_a_single_json_handler():
    configure_logging("DEBUG")

    root = logging.getLogger()
    assert len(root.handlers) == 1
    assert root.level == logging.DEBUG


def test_configure_logging_quiets_noisy_third_party_loggers():
    configure_logging("INFO")

    assert logging.getLogger("uvicorn.access").level == logging.WARNING
    assert logging.getLogger("sqlalchemy.engine").level == logging.WARNING


def test_configure_logging_defaults_to_info_level_string():
    configure_logging()
    assert logging.getLogger().level == logging.INFO
