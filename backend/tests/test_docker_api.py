import asyncio
import contextlib

import pytest

from app.api import docker_api


@pytest.mark.asyncio
async def test_container_inventory_does_not_wait_for_slow_stats(monkeypatch):
    stats_release = asyncio.Event()
    container = (
        "abc123|web|example/web:latest|Up 2 hours|running|"
        "127.0.0.1:8080->80/tcp|2026-08-19 00:00:00 +0000 UTC"
    )

    async def fake_run(cmd: list[str]) -> tuple[int, str]:
        if cmd[1] == "ps":
            assert cmd[-1] == docker_api._PS_FORMAT
            return 0, container
        await stats_release.wait()
        return 0, ""

    monkeypatch.setattr(docker_api, "_run", fake_run)
    docker_api._STATS_CACHE = {}
    docker_api._STATS_CACHE_TS = 0.0
    docker_api._stats_task = None

    result = await asyncio.wait_for(docker_api.list_containers(None), timeout=0.1)

    assert len(result) == 1
    assert result[0].name == "web"
    assert result[0].stats_available is False
    assert docker_api._stats_task is not None
    assert not docker_api._stats_task.done()

    docker_api._stats_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await docker_api._stats_task
