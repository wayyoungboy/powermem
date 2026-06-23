import asyncio
import time

import pytest

from server.models.response import DependencyStatus
from server.utils import health_check


@pytest.mark.asyncio
async def test_dependency_status_timeout_does_not_block_event_loop(monkeypatch):
    health_check._DEPENDENCY_STATUS_CACHE.clear()
    health_check._DEPENDENCY_STATUS_LOCKS.clear()

    def slow_database_probe():
        time.sleep(0.2)
        return DependencyStatus(name="database", status="healthy")

    def fast_llm_probe():
        return DependencyStatus(name="llm", status="disabled")

    monkeypatch.setattr(health_check, "_check_database_sync", slow_database_probe)
    monkeypatch.setattr(health_check, "_check_llm_sync", fast_llm_probe)

    start = time.monotonic()
    dependencies = await health_check.check_all_dependencies(
        timeout_seconds=0.05,
        cache_ttl_seconds=0.0,
    )
    elapsed = time.monotonic() - start

    assert elapsed < 0.15
    assert dependencies["database"].status == "degraded"
    assert "timed out" in dependencies["database"].error_message
    assert dependencies["llm"].status == "disabled"


@pytest.mark.asyncio
async def test_dependency_status_uses_short_ttl_cache(monkeypatch):
    health_check._DEPENDENCY_STATUS_CACHE.clear()
    health_check._DEPENDENCY_STATUS_LOCKS.clear()
    calls = {"database": 0, "llm": 0}

    def database_probe():
        calls["database"] += 1
        return DependencyStatus(name="database", status="healthy")

    def llm_probe():
        calls["llm"] += 1
        return DependencyStatus(name="llm", status="disabled")

    monkeypatch.setattr(health_check, "_check_database_sync", database_probe)
    monkeypatch.setattr(health_check, "_check_llm_sync", llm_probe)

    await health_check.check_all_dependencies(
        timeout_seconds=0.1,
        cache_ttl_seconds=60.0,
    )
    await health_check.check_all_dependencies(
        timeout_seconds=0.1,
        cache_ttl_seconds=60.0,
    )

    assert calls == {"database": 1, "llm": 1}


@pytest.mark.asyncio
async def test_dependency_status_coalesces_concurrent_same_dependency(monkeypatch):
    health_check._DEPENDENCY_STATUS_CACHE.clear()
    health_check._DEPENDENCY_STATUS_LOCKS.clear()
    calls = {"database": 0}

    def database_probe():
        calls["database"] += 1
        time.sleep(0.03)
        return DependencyStatus(name="database", status="healthy")

    monkeypatch.setattr(health_check, "_check_database_sync", database_probe)

    results = await asyncio.gather(
        *[
            health_check.check_database(
                timeout_seconds=0.2,
                cache_ttl_seconds=60.0,
            )
            for _ in range(10)
        ]
    )

    assert calls == {"database": 1}
    assert {result.status for result in results} == {"healthy"}
