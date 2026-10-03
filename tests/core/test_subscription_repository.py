import asyncio
import sqlite3
import traceback
from contextlib import closing
from dataclasses import replace
from datetime import datetime, timedelta
from uuid import uuid4

import pytest
from dota2forge_core import (
    AccountId,
    DataSource,
    MatchSummary,
    RankChange,
    SQLiteSubscriptionRepository,
    Subscription,
    SubscriptionCapacityError,
    SubscriptionCheckpoint,
    SubscriptionEvent,
    SubscriptionKey,
    SubscriptionKind,
    SubscriptionPollResult,
    SubscriptionPollState,
    SubscriptionRepositoryError,
    SubscriptionScope,
    ValidationError,
)


@pytest.fixture
def store(tmp_path, run_async):
    repository = SQLiteSubscriptionRepository(tmp_path / "subscriptions.sqlite3")
    run_async(repository.initialize())
    return repository


@pytest.fixture
def subscription(identity, metadata):
    return Subscription(
        uuid4().hex,
        SubscriptionKey(
            identity,
            "group:synthetic",
            AccountId(123),
            DataSource.FIXTURE,
            SubscriptionKind.NEW_MATCH,
        ),
        metadata.fetched_at,
    )


def transition(subscription, metadata, match_id=1):
    start = metadata.fetched_at - timedelta(minutes=10) + timedelta(seconds=match_id)
    checkpoint = SubscriptionCheckpoint(metadata.fetched_at, start, (match_id,))
    event = SubscriptionEvent(
        uuid4().hex,
        subscription.subscription_id,
        subscription.key,
        metadata.fetched_at,
        MatchSummary(match_id, subscription.key.account_id, start, metadata, is_win=False),
    )
    return checkpoint, event


def test_store_compare_and_swap_rollback_and_owner_isolation(
    store, subscription, identity, metadata, run_async
):
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        assert await store.save(subscription) == subscription
        checkpoint, event = transition(subscription, metadata)
        results = await asyncio.gather(
            store.commit(subscription, checkpoint, (event,)),
            store.commit(subscription, checkpoint, (event,)),
        )
        assert sorted(results) == [False, True]
        assert await store.pending(scope) == (event,)
        current = (await store.list(scope))[0]
        assert current.revision == 1
        other = replace(identity, user_id="another-user")
        assert not await store.pending(scope, owner=other)
        assert not await store.acknowledge(other, event.event_id)
        assert not await store.delete(other, subscription.subscription_id)
        assert await store.acknowledge(identity, event.event_id)
        assert not await store.pending(scope)
        assert await store.delete(identity, subscription.subscription_id)
        assert not await store.commit(current, checkpoint, ())
        assert not await store.delete(identity, subscription.subscription_id)

    run_async(scenario())


def test_storage_and_outbox_capacities_are_atomic(
    tmp_path, subscription, identity, metadata, run_async
):
    store = SQLiteSubscriptionRepository(
        tmp_path / "subscriptions.sqlite3", max_subscriptions=1, max_pending_events=1
    )
    scope = SubscriptionScope.for_identity(identity)

    async def scenario():
        await store.initialize()
        await store.save(subscription)
        duplicate = replace(
            subscription,
            subscription_id=uuid4().hex,
            created_at=metadata.fetched_at + timedelta(days=1),
        )
        assert await store.save(duplicate) == subscription
        another = replace(duplicate, key=replace(duplicate.key, destination="group:another"))
        with pytest.raises(SubscriptionCapacityError):
            await store.save(another)
        different_bot = replace(
            another, key=replace(another.key, identity=replace(identity, bot_id="another-bot"))
        )
        assert await store.save(different_bot) == different_bot
        first_checkpoint, first = transition(subscription, metadata, 1)
        second_checkpoint, second = transition(subscription, metadata, 2)
        with pytest.raises(SubscriptionCapacityError):
            await store.commit(subscription, second_checkpoint, (first, second))
        assert await store.list(scope) == (subscription,)
        assert not await store.pending(scope)
        assert await store.commit(subscription, first_checkpoint, (first,))
        current = (await store.list(scope))[0]
        with pytest.raises(SubscriptionCapacityError):
            await store.commit(current, second_checkpoint, (second,))
        assert await store.list(scope) == (current,)
        assert await store.pending(scope) == (first,)
        assert await store.acknowledge(identity, first.event_id)
        assert await store.commit(current, second_checkpoint, (second,))

    run_async(scenario())


def test_sql_failure_rolls_back_event_and_checkpoint(
    store, subscription, identity, metadata, tmp_path, run_async
):
    scope = SubscriptionScope.for_identity(identity)
    run_async(store.save(subscription))
    checkpoint, event = transition(subscription, metadata)
    with closing(sqlite3.connect(tmp_path / "subscriptions.sqlite3")) as connection, connection:
        connection.execute(
            "CREATE TRIGGER fail_checkpoint BEFORE UPDATE ON subscriptions "
            "BEGIN SELECT RAISE(ABORT, 'synthetic-secret'); END"
        )
    with pytest.raises(SubscriptionRepositoryError) as failure:
        run_async(store.commit(subscription, checkpoint, (event,)))
    assert "synthetic-secret" not in "".join(traceback.format_exception(failure.value))
    assert run_async(store.list(scope)) == (subscription,)
    assert not run_async(store.pending(scope))


@pytest.mark.parametrize(
    "field",
    ["namespace", "platform", "bot_id", "user_id", "destination", "account_id", "source", "kind"],
)
def test_subscription_unique_key_preserves_all_partitions(
    store, subscription, identity, field, run_async
):
    if field in {"namespace", "platform", "bot_id", "user_id"}:
        key = replace(subscription.key, identity=replace(identity, **{field: "another"}))
    else:
        values = {
            "destination": "group:another",
            "account_id": AccountId(456),
            "source": DataSource.STRATZ,
            "kind": SubscriptionKind.RANK_CHANGE,
        }
        key = replace(subscription.key, **{field: values[field]})
    other = replace(subscription, subscription_id=uuid4().hex, key=key)
    assert run_async(store.save(subscription)) == subscription
    assert run_async(store.save(other)) == other
    original_scope = SubscriptionScope.for_identity(identity)
    other_scope = SubscriptionScope.for_identity(key.identity)
    if original_scope != other_scope:
        assert run_async(store.list(original_scope)) == (subscription,)
        assert run_async(store.list(other_scope)) == (other,)
    else:
        assert len(run_async(store.list(original_scope))) == 2


@pytest.mark.parametrize(
    "change", ["version", "application", "column", "extra_table", "foreign_key"]
)
def test_storage_rejects_schema_drift(store, identity, tmp_path, change, run_async):
    with closing(sqlite3.connect(tmp_path / "subscriptions.sqlite3")) as connection, connection:
        if change == "version":
            connection.execute("PRAGMA user_version = 99")
        elif change == "application":
            connection.execute("PRAGMA application_id = 99")
        elif change == "column":
            connection.execute("ALTER TABLE subscriptions ADD COLUMN extra TEXT")
        elif change == "extra_table":
            connection.execute("CREATE TABLE unexpected (value TEXT)")
        else:
            connection.execute("DROP TABLE subscription_events")
            connection.execute(
                "CREATE TABLE subscription_events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
                "event_id TEXT NOT NULL UNIQUE, subscription_id TEXT NOT NULL, "
                "detected_at TEXT NOT NULL, payload TEXT NOT NULL)"
            )
    with pytest.raises(SubscriptionRepositoryError):
        run_async(store.initialize())
    with pytest.raises(SubscriptionRepositoryError):
        run_async(store.list(SubscriptionScope.for_identity(identity)))


@pytest.mark.parametrize(
    "case", ["foreign", "binding", "not_database", "missing_parent", "uninitialized"]
)
def test_initialize_never_migrates_foreign_or_binding_files(tmp_path, case, identity, run_async):
    path = tmp_path / "foreign.sqlite3"
    if case == "foreign":
        with closing(sqlite3.connect(path)) as connection, connection:
            connection.execute("CREATE TABLE unknown (value TEXT)")
    elif case == "binding":
        from dota2forge_core.infrastructure.sqlite import SQLiteBindingRepository

        run_async(SQLiteBindingRepository(path).initialize())
    elif case == "not_database":
        path.write_text("synthetic invalid database", encoding="utf-8")
    elif case == "missing_parent":
        path = tmp_path / "absent" / "private.sqlite3"
    store = SQLiteSubscriptionRepository(path)
    with pytest.raises(SubscriptionRepositoryError):
        if case == "uninitialized":
            run_async(store.list(SubscriptionScope.for_identity(identity)))
        else:
            run_async(store.initialize())
    if case == "binding":
        run_async(SQLiteBindingRepository(path).initialize())


@pytest.mark.parametrize(
    "column,value",
    [
        ("checkpoint", "not-json"),
        ("checkpoint", "[]"),
        (
            "checkpoint",
            '{"fetched_at":null,"match_started_at":null,"match_ids":null,"rank_tier":null}',
        ),
        pytest.param("checkpoint", "x" * 65537, id="oversized-checkpoint"),
        ("source", "unknown"),
        ("account_id", 0),
        ("created_at", "2026-10-02T00:00:00"),
        ("revision", -1),
        ("kind", "unsupported_kind"),
    ],
)
def test_corrupt_subscription_is_safe_failure(
    store, subscription, identity, tmp_path, column, value, run_async
):
    run_async(store.save(subscription))
    with closing(sqlite3.connect(tmp_path / "subscriptions.sqlite3")) as connection, connection:
        connection.execute(f"UPDATE subscriptions SET {column} = ?", (value,))
    with pytest.raises(SubscriptionRepositoryError) as failure:
        run_async(store.list(SubscriptionScope.for_identity(identity)))
    display = "".join(traceback.format_exception(failure.value))
    assert identity.user_id not in display
    assert str(tmp_path) not in display


@pytest.mark.parametrize(
    "column,value",
    [
        ("payload", "[]"),
        ("payload", "{}"),
        ("payload", "invalid-json"),
        ("event_id", "F" * 32),
        ("detected_at", "2026-10-02"),
    ],
)
def test_corrupt_event_is_not_acknowledged(
    store, subscription, identity, metadata, tmp_path, column, value, run_async
):
    run_async(store.save(subscription))
    checkpoint, event = transition(subscription, metadata)
    run_async(store.commit(subscription, checkpoint, (event,)))
    with closing(sqlite3.connect(tmp_path / "subscriptions.sqlite3")) as connection, connection:
        connection.execute(f"UPDATE subscription_events SET {column} = ?", (value,))
    with pytest.raises(SubscriptionRepositoryError):
        run_async(store.pending(SubscriptionScope.for_identity(identity)))
    if column != "event_id":
        with pytest.raises(SubscriptionRepositoryError):
            run_async(store.acknowledge(identity, event.event_id))
    else:
        with pytest.raises(ValidationError):
            run_async(store.acknowledge(identity, value))


@pytest.mark.parametrize(
    "changes",
    [
        {"timeout_seconds": 0},
        {"timeout_seconds": True},
        {"timeout_seconds": float("inf")},
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": "1"},
        {"max_pending_events": 0},
        {"max_pending_events": True},
        {"max_subscriptions": -1},
    ],
)
def test_repository_config_rejects_bad_values(tmp_path, changes):
    with pytest.raises(ValidationError):
        SQLiteSubscriptionRepository(tmp_path / "unused.sqlite3", **changes)
    assert not (tmp_path / "unused.sqlite3").exists()


@pytest.mark.parametrize("path", [None, 123, "", " ", ":memory:"])
def test_repository_requires_file(path):
    with pytest.raises(ValidationError):
        SQLiteSubscriptionRepository(path)


@pytest.mark.parametrize(
    "change",
    [
        {"identity": None},
        {"account_id": 123},
        {"source": "fixture"},
        {"kind": "new_match"},
        {"destination": ""},
        {"destination": "has space"},
        {"destination": "bad\nvalue"},
        {"destination": "x" * 513},
    ],
)
def test_key_validation_and_privacy(subscription, change):
    with pytest.raises(ValidationError):
        replace(subscription.key, **change)
    assert subscription.key.identity.user_id not in repr(subscription)
    assert subscription.key.destination not in repr(subscription)


@pytest.mark.parametrize(
    "change",
    [
        {"match_ids": []},
        {"match_ids": (1, 1)},
        {"match_ids": (True,)},
        {"match_ids": (0,)},
        {"match_ids": ([],)},
        {"match_ids": tuple(range(1, 102))},
        {"match_ids": ()},
        {"match_started_at": None},
        {"fetched_at": None},
        {"fetched_at": datetime(2026, 10, 2)},
        {"rank_tier": False},
    ],
)
def test_checkpoint_validation(subscription, metadata, change):
    checkpoint, _ = transition(subscription, metadata)
    with pytest.raises(ValidationError):
        replace(checkpoint, **change)


@pytest.mark.parametrize(
    "change",
    [
        {"subscription_id": "invalid"},
        {"subscription_id": "A" * 32},
        {"key": None},
        {"checkpoint": None},
        {"revision": None},
        {"revision": True},
        {"created_at": datetime(2026, 10, 2)},
    ],
)
def test_subscription_validation(subscription, change):
    with pytest.raises(ValidationError):
        replace(subscription, **change)


def test_kind_specific_checkpoints_and_event_invariants(subscription, metadata):
    checkpoint, event = transition(subscription, metadata)
    with pytest.raises(ValidationError):
        replace(subscription, checkpoint=replace(checkpoint, rank_tier=65))
    rank_key = replace(subscription.key, kind=SubscriptionKind.RANK_CHANGE)
    with pytest.raises(ValidationError):
        replace(subscription, key=rank_key, checkpoint=checkpoint)
    with pytest.raises(ValidationError):
        replace(
            subscription,
            created_at=metadata.fetched_at + timedelta(seconds=1),
            checkpoint=checkpoint,
        )
    for changes in [
        {"event_id": "invalid"},
        {"payload": None},
        {"key": None},
        {"key": replace(event.key, account_id=AccountId(456))},
        {"key": replace(event.key, source=DataSource.STRATZ)},
        {"payload": replace(event.payload, is_win=None)},
        {"payload": RankChange(65, 64, metadata)},
    ]:
        with pytest.raises(ValidationError):
            replace(event, **changes)
    for values in [(None, 64), (False, 64), (65, 65)]:
        with pytest.raises(ValidationError):
            RankChange(*values, metadata)
    rank_payload = RankChange(65, 64, metadata)
    assert replace(event, key=rank_key, payload=rank_payload).payload == rank_payload


def test_poll_classification_validation(subscription, metadata):
    _, event = transition(subscription, metadata)
    result = SubscriptionPollResult(subscription, SubscriptionPollState.EVENTS, (event,))
    for changes in [
        {"subscription": None},
        {"state": "events"},
        {"events": []},
        {"events": ()},
        {"coverage_gap": 1},
        {"events": (None,)},
        {"state": SubscriptionPollState.FAILED, "events": ()},
        {"failure": RuntimeError("synthetic")},
    ]:
        with pytest.raises(ValidationError):
            replace(result, **changes)


def test_invalid_storage_operations_fail_before_transactions(
    store, subscription, identity, metadata, run_async
):
    scope = SubscriptionScope.for_identity(identity)
    checkpoint, event = transition(subscription, metadata)
    for coroutine in [
        store.save(None),
        store.save(replace(subscription, revision=1)),
        store.list(None),
        store.list(scope, owner=replace(identity, bot_id="another-bot")),
        store.list(scope, kind="new_match"),
        store.list(scope, after_id="invalid"),
        store.delete(None, subscription.subscription_id),
        store.delete(identity, "invalid"),
        store.pending(scope, limit=0),
        store.acknowledge(None, event.event_id),
        store.commit(None, checkpoint, ()),
        store.commit(subscription, None, ()),
        store.commit(subscription, SubscriptionCheckpoint(), ()),
        store.commit(subscription, checkpoint, []),
        store.commit(subscription, checkpoint, (None,)),
        store.commit(subscription, checkpoint, (event, event)),
    ]:
        with pytest.raises(ValidationError):
            run_async(coroutine)
    assert not run_async(store.list(scope))


def test_monotonic_checkpoint_rejects_unsafe_transitions(
    store, subscription, identity, metadata, run_async
):
    run_async(store.save(subscription))
    checkpoint, event = transition(subscription, metadata)
    run_async(store.commit(subscription, checkpoint, (event,)))
    current = run_async(store.list(SubscriptionScope.for_identity(identity)))[0]
    for invalid in [
        replace(checkpoint, match_started_at=None, match_ids=()),
        replace(checkpoint, match_started_at=checkpoint.match_started_at - timedelta(seconds=1)),
        replace(checkpoint, match_ids=(2,)),
        replace(checkpoint, fetched_at=metadata.fetched_at - timedelta(seconds=1)),
    ]:
        with pytest.raises(ValidationError):
            run_async(store.commit(current, invalid, ()))


def test_busy_database_fails_without_leaking_paths(store, subscription, tmp_path, run_async):
    limited = SQLiteSubscriptionRepository(tmp_path / "subscriptions.sqlite3", timeout_seconds=0.01)
    with closing(sqlite3.connect(tmp_path / "subscriptions.sqlite3")) as connection:
        connection.execute("BEGIN EXCLUSIVE")
        with pytest.raises(SubscriptionRepositoryError):
            run_async(limited.save(subscription))


@pytest.mark.parametrize("drift", ["unique", "orphan"])
def test_unique_and_foreign_key_integrity_are_required(
    store, subscription, identity, metadata, tmp_path, drift, run_async
):
    run_async(store.save(subscription))
    checkpoint, event = transition(subscription, metadata)
    run_async(store.commit(subscription, checkpoint, (event,)))
    with closing(sqlite3.connect(tmp_path / "subscriptions.sqlite3")) as connection, connection:
        if drift == "unique":
            connection.execute("CREATE UNIQUE INDEX wrong_uniqueness ON subscriptions(destination)")
        else:
            connection.execute("UPDATE subscription_events SET subscription_id = ?", (uuid4().hex,))
    with pytest.raises(SubscriptionRepositoryError):
        run_async(store.pending(SubscriptionScope.for_identity(identity)))
