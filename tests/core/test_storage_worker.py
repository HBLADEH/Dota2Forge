"""Cancellation cannot abandon an already-started SQLite transaction thread."""

import asyncio
import threading

import pytest
from dota2forge_core.infrastructure._worker import run_storage
from dota2forge_core.infrastructure.sqlite import SQLiteBindingRepository
from dota2forge_core.infrastructure.subscriptions import SQLiteSubscriptionRepository


@pytest.mark.parametrize("repository_type", [SQLiteBindingRepository, SQLiteSubscriptionRepository])
def test_cancelled_initialization_waits_for_transaction_exit(
    tmp_path, run_async, monkeypatch, repository_type
):
    repository = repository_type(tmp_path / "synthetic.sqlite3")
    entered, release, exited = threading.Event(), threading.Event(), threading.Event()
    original = repository._run

    def delayed(*args, **kwargs):
        entered.set()
        assert release.wait(5)
        try:
            return original(*args, **kwargs)
        finally:
            exited.set()

    monkeypatch.setattr(repository, "_run", delayed)

    async def check():
        task = asyncio.create_task(repository.initialize())
        assert await asyncio.to_thread(entered.wait, 3)
        task.cancel()
        await asyncio.sleep(0)
        task.cancel()
        await asyncio.sleep(0)
        assert not task.done() and not exited.is_set()
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert exited.is_set()
        await repository.initialize()

    run_async(check())


def test_cancelled_worker_failure_is_retrieved_after_thread_exit(run_async):
    entered, release = threading.Event(), threading.Event()

    def failed():
        entered.set()
        assert release.wait(5)
        raise RuntimeError("synthetic-transaction-failure")

    async def check():
        task = asyncio.create_task(run_storage(failed))
        assert await asyncio.to_thread(entered.wait, 3)
        task.cancel()
        await asyncio.sleep(0)
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    run_async(check())
