import asyncio
import json

import httpx
import pytest
from dota2forge_assets import AssetError
from dota2forge_assets.sources import CDN, MIRROR
from dota2forge_assets.validation import validate_manifest


def test_first_download_single_job_complete_and_restart_without_http(tmp_path, backend, run_async):
    async def run():
        manager = backend.manager(tmp_path)
        assert not tmp_path.joinpath(".lease").exists()
        first = await manager.ensure()
        assert first and await manager.ensure() == first
        await manager.wait()
        status = manager.status()
        assert status.state == "ready" and status.completed == status.total == 17
        assert status.counts["heroes"].available == 1
        assert 1 <= backend.maximum <= 4
        assert all(c.is_closed for c in backend.clients)
        assert manager.path is not None
        manifest = validate_manifest(manager.path, manager.limits)
        assert manifest["heroes"]["2"]["sha256"]
        assert manifest["ui"]["gold"]["mirror"] == "OpenDota"
        with pytest.raises(TypeError):
            status.counts["heroes"] = None
        await manager.close()
        backend.calls.clear()
        second = backend.manager(tmp_path)
        await second.open()
        assert second.path == manager.path
        assert await second.ensure(automatic=True) is None
        assert second.status().state == "ready" and backend.calls == []
        await second.close()

    run_async(run())


def test_ui_failure_publishes_heroes_and_resumes_after_persisted_cooldown(
    tmp_path, backend, run_async
):
    async def run():
        backend.fail[MIRROR] = 503
        manager = backend.manager(tmp_path)
        await manager.ensure(automatic=True)
        await manager.wait()
        assert manager.status().state == "partial"
        assert manager.status().counts["heroes"].available == 1
        assert manager.status().counts["ranks"].failed == 9
        assert manager.path is not None
        old_path = manager.path
        old = json.loads((old_path / "manifest.json").read_bytes())["heroes"]["2"]
        assert json.loads((old_path / "manifest.json").read_bytes())["ranks"] == {}
        await manager.close()
        backend.fail.clear()
        backend.calls.clear()
        resumed = backend.manager(tmp_path)
        assert await resumed.ensure(automatic=True) is None
        assert resumed.status().retry_after_seconds == 1800
        backend.advance(31)
        assert await resumed.ensure()
        await resumed.wait()
        assert resumed.status().state == "ready" and resumed.path != old_path
        assert len(backend.calls) == 15  # no catalog or good hero/item requests
        assert all(str(r.url).startswith(MIRROR) for r in backend.calls)
        assert json.loads((resumed.path / "manifest.json").read_bytes())["heroes"]["2"] == old
        await resumed.close()

    run_async(run())


def test_404_is_missing_but_forbidden_network_and_corruption_are_failures(
    tmp_path, backend, run_async
):
    async def run():
        backend.fail[f"{CDN}/items"] = 404
        backend.fail[f"{MIRROR}/gold"] = 403
        manager = backend.manager(tmp_path)
        await manager.ensure()
        await manager.wait()
        assert manager.status().counts["items"].missing_404 == 1
        assert manager.status().counts["ui"].failed == 1
        assert manager.path is not None
        original = json.loads((manager.path / "manifest.json").read_bytes())["heroes"]["2"]
        backend.advance()
        backend.fail[f"{CDN}/heroes"] = httpx.ConnectError("private transport detail")
        backend.fail.pop(f"{MIRROR}/gold")
        backend.color = "blue"
        await manager.update()
        await manager.wait()
        assert manager.status().state == "partial"
        current = json.loads((manager.path / "manifest.json").read_bytes())
        assert current["heroes"]["2"] == original  # preserve time and bytes on failure
        assert current["items"]["1"]["reason"] == "http_404"
        assert "private" not in repr(manager.status())
        await manager.close()

    run_async(run())


def test_update_atomic_pointer_keep_two_generations_and_candidate_rejection(
    tmp_path, backend, run_async
):
    async def run():
        reject = False

        async def activate(path, commit):
            assert path.joinpath("manifest.json").exists()
            validate_manifest(path, manager.limits)
            if reject:
                raise AssetError("renderer")
            await commit()

        manager = backend.manager(tmp_path, activate)
        for color in ("red", "blue", "green"):
            backend.color = color
            await manager.update()
            await manager.wait()
            backend.advance()
            assert manager.status().state == "ready"
        assert len(list((tmp_path / "generations").iterdir())) == 2
        pointer = (tmp_path / "current.json").read_bytes()
        previous = manager.path
        reject = True
        backend.color = "purple"
        await manager.update()
        await manager.wait()
        assert manager.status().state == "failed"
        assert manager.path == previous and (tmp_path / "current.json").read_bytes() == pointer
        await manager.close()

    run_async(run())


def test_process_lease_busy_and_release(tmp_path, backend, run_async):
    async def run():
        first, second = backend.manager(tmp_path), backend.manager(tmp_path)
        await first.open()
        await second.open()
        assert second.status().state == "busy"
        assert second.path is None and await second.update() is None and backend.calls == []
        await first.close()
        assert await second.ensure()
        await second.wait()
        assert second.status().state == "ready"
        await second.close()

    run_async(run())


def test_cancel_waits_for_requests_prevents_publish_and_releases_lease(
    tmp_path, backend, run_async
):
    async def run():
        backend.delay = 10
        manager = backend.manager(tmp_path)
        await manager.ensure()
        for _ in range(1000):
            if backend.active:
                break
            await asyncio.sleep(0.001)
        assert backend.active
        await manager.close()
        assert backend.active == 0 and all(c.is_closed for c in backend.clients)
        assert not (tmp_path / "current.json").exists()
        assert manager.store.lease.stream is None and await manager.update() is None
        assert not list((tmp_path / "staging").iterdir())
        await manager.close()

    run_async(run())
