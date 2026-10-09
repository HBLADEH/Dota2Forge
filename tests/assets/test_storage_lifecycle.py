import asyncio
import subprocess
import sys
import threading

import pytest
from dota2forge_assets import AssetError
from dota2forge_assets.sources import CDN


def test_real_process_lease_is_exclusive_and_os_releases_on_exit(tmp_path, backend, run_async):
    code = """import sys
from pathlib import Path
from dota2forge_assets.store import Lease
lease = Lease(Path(sys.argv[1]) / '.lease')
lease.acquire()
print('locked', flush=True)
sys.stdin.read(1)
"""
    process = subprocess.Popen(
        [sys.executable, "-I", "-c", code, str(tmp_path)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout.readline().strip() == "locked"

        async def run():
            manager = backend.manager(tmp_path)
            await manager.open()
            assert manager.status().state == "busy"
            assert await manager.ensure() is None
            process.terminate()
            process.wait(timeout=10)
            await manager.open()
            assert manager.status().state == "checking" and manager.store.lease.stream
            await manager.close()

        run_async(run())
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=10)
        process.stdin.close()
        process.stdout.close()


@pytest.mark.parametrize("commit", [False, True])
def test_process_crash_either_side_of_pointer_leaves_verified_generation(
    tmp_path,
    backend,
    run_async,
    commit,
):
    async def prepare():
        manager = backend.manager(tmp_path)
        await manager.ensure()
        await manager.wait()
        path = manager.path
        await manager.close()
        return path

    original = run_async(prepare())
    name = "1" * 32
    code = """import json, os, shutil, sys
from pathlib import Path
from dota2forge_assets import AssetLimits
from dota2forge_assets.store import Store
root, source = map(Path, sys.argv[1:3])
store = Store(root, AssetLimits())
store.open()
name = '1' * 32
shutil.copytree(source, root / 'staging' / name)
manifest = json.loads((source / 'manifest.json').read_bytes())
generation = store.finalize(name, manifest)
if sys.argv[3] == 'True':
    store.commit(generation, True)
os._exit(0)
"""
    subprocess.run(
        [sys.executable, "-I", "-c", code, str(tmp_path), str(original), str(commit)],
        check=True,
        timeout=15,
    )

    async def reopen():
        manager = backend.manager(tmp_path)
        await manager.open()
        assert manager.status().state == "ready"
        assert manager.path.name == (name if commit else original.name)
        assert manager.store.current()[0] == manager.path
        await manager.close()

    run_async(reopen())


def test_close_waiter_cancellation_keeps_thread_and_lock_until_finished(
    tmp_path,
    backend,
    run_async,
    monkeypatch,
):
    entered, release = threading.Event(), threading.Event()

    async def run():
        manager = backend.manager(tmp_path)
        original = manager.store.write

        def write(path, data, **options):
            if path.suffix == ".png":
                entered.set()
                assert release.wait(10)
            original(path, data, **options)

        monkeypatch.setattr(manager.store, "write", write)
        await manager.ensure()
        for _ in range(5000):
            if entered.is_set():
                break
            await asyncio.sleep(0.001)
        assert entered.is_set()
        closer = asyncio.create_task(manager.close())
        await asyncio.sleep(0.01)
        closer.cancel()
        with pytest.raises(asyncio.CancelledError):
            await closer
        assert manager.store.lease.stream is not None and manager.store.io.tasks
        assert not (tmp_path / "current.json").exists()
        release.set()
        await manager.close()
        assert manager.store.lease.stream is None and manager.store.io.tasks == set()
        assert not (tmp_path / "current.json").exists()

    try:
        run_async(run())
    finally:
        release.set()


def test_budget_storage_failure_never_changes_current_and_cleans_job(
    tmp_path,
    backend,
    run_async,
    monkeypatch,
):
    async def run():
        manager = backend.manager(tmp_path)
        await manager.ensure()
        await manager.wait()
        pointer = (tmp_path / "current.json").read_bytes()
        backend.advance()
        backend.color = "blue"

        def exhausted(additional):
            raise AssetError("budget")

        monkeypatch.setattr(manager.store, "_check_budget", exhausted)
        await manager.update()
        await manager.wait()
        assert manager.status().state == "failed" and manager.status().error in {
            "budget",
            "storage",
        }
        assert (tmp_path / "current.json").read_bytes() == pointer
        assert not list((tmp_path / "staging").iterdir())
        assert all(client.is_closed for client in backend.clients)
        await manager.close()

    run_async(run())


def test_corrupt_cache_catalog_and_png_resume_from_verified_files(tmp_path, backend, run_async):
    async def run():
        # Interrupt before any generation is published; the file cache remains reusable.
        async def reject(path, commit):
            raise AssetError("renderer")

        manager = backend.manager(tmp_path, reject)
        await manager.ensure()
        await manager.wait()
        assert manager.path is None
        caches = list((tmp_path / "cache").glob("*/heroes/2.png"))
        assert len(caches) == 1
        caches[0].write_bytes(b"corrupted")
        (tmp_path / "cache/catalogs/heroes.json").write_bytes(b"corrupted")
        await manager.close()
        backend.advance()
        backend.calls.clear()
        resumed = backend.manager(tmp_path)
        await resumed.ensure()
        await resumed.wait()
        assert resumed.status().state == "ready"
        assert len(backend.calls) == 2
        assert any(str(req.url).startswith(f"{CDN}/heroes") for req in backend.calls)
        await resumed.close()

    run_async(run())


def test_job_deadline_does_not_claim_missing_or_complete_percentage(tmp_path, backend, run_async):
    async def run():
        backend.delay = 0.05
        manager = backend.manager(tmp_path, job_seconds=0.02)
        await manager.ensure()
        await manager.wait()
        assert manager.status().state == "failed"
        assert manager.status().total is None
        assert manager.status().counts["heroes"].missing_404 == 0
        assert manager.status().counts["heroes"].failed == 1
        assert not (tmp_path / "current.json").exists()
        await manager.close()

    run_async(run())


def test_deadline_during_last_file_is_partial_and_ensure_repairs_it(
    tmp_path,
    backend,
    run_async,
    monkeypatch,
):
    async def run():
        original = backend.request

        async def slow_last(request):
            if str(request.url).endswith("gold.png"):
                await asyncio.sleep(10)
            return await original(request)

        monkeypatch.setattr(backend, "request", slow_last)
        manager = backend.manager(tmp_path, job_seconds=5)
        await manager.ensure()
        await manager.wait()
        assert manager.status().state == "partial"
        assert manager.status().counts["ui"].failed == 1
        assert manager.status().completed == 16 and manager.status().total == 17
        assert manager.store.current()[2]["complete"] is False
        await manager.close()
        monkeypatch.setattr(backend, "request", original)
        backend.advance()
        backend.calls.clear()
        resumed = backend.manager(tmp_path)
        await resumed.ensure()
        await resumed.wait()
        assert resumed.status().state == "ready"
        assert len(backend.calls) == 1 and str(backend.calls[0].url).endswith("gold.png")
        await resumed.close()

    run_async(run())
