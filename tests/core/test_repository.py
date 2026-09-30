import asyncio
import sqlite3
import traceback
from contextlib import closing
from dataclasses import replace
from datetime import timedelta

import pytest
from dota2forge_core import (
    AccountId,
    BindingConflictError,
    PlayerBinding,
    RepositoryError,
    ValidationError,
)
from dota2forge_core.infrastructure.sqlite import SQLiteBindingRepository


def test_bind_reopen_replace_delete_persist(repository, identity, metadata, tmp_path, run_async):
    first = PlayerBinding(identity, AccountId(123), metadata.fetched_at)
    assert run_async(repository.get(identity)) is None
    assert run_async(repository.save(first)) == first
    again = replace(first, bound_at=first.bound_at + timedelta(days=1))
    assert run_async(repository.save(again)) == first
    assert run_async(repository.save(again, replace=True)) == first

    reopened = SQLiteBindingRepository(tmp_path / "bindings.sqlite3")
    run_async(reopened.initialize())
    assert run_async(reopened.get(identity)) == first
    changed = replace(again, account_id=AccountId(456))
    with pytest.raises(BindingConflictError):
        run_async(reopened.save(changed))
    assert run_async(reopened.get(identity)) == first
    assert run_async(reopened.save(changed, replace=True)) == changed
    assert run_async(repository.get(identity)) == changed
    assert run_async(reopened.delete(identity)) is True
    assert run_async(repository.delete(identity)) is False
    assert run_async(repository.get(identity)) is None


@pytest.mark.parametrize("field", ["namespace", "platform", "bot_id", "user_id"])
def test_each_identity_component_is_an_isolation_boundary(
    repository, identity, metadata, run_async, field
):
    other = replace(identity, **{field: "another-value"})
    first = PlayerBinding(identity, AccountId(123), metadata.fetched_at)
    second = PlayerBinding(other, AccountId(456), metadata.fetched_at)
    run_async(repository.save(first))
    assert run_async(repository.get(other)) is None
    run_async(repository.save(second))
    assert run_async(repository.get(identity)) == first
    assert run_async(repository.get(other)) == second
    run_async(repository.delete(identity))
    assert run_async(repository.get(other)) == second


def test_keys_with_sql_or_delimiters_are_bound_as_values(repository, identity, metadata, run_async):
    identities = [
        replace(identity, bot_id="a:b", user_id="c"),
        replace(identity, bot_id="a", user_id="b:c"),
        replace(identity, user_id="';DROP/**/TABLE/**/bindings;--"),
    ]
    for number, target in enumerate(identities, start=1):
        run_async(repository.save(PlayerBinding(target, AccountId(number), metadata.fetched_at)))
    for number, target in enumerate(identities, start=1):
        assert run_async(repository.get(target)).account_id == AccountId(number)


def test_concurrent_conflicting_binds_have_one_winner(identity, metadata, tmp_path, run_async):
    async def race():
        repositories = [SQLiteBindingRepository(tmp_path / "race.sqlite3") for _ in range(2)]
        await asyncio.gather(*(repo.initialize() for repo in repositories))
        bindings = [
            PlayerBinding(identity, AccountId(value), metadata.fetched_at) for value in (123, 456)
        ]
        results = await asyncio.gather(
            *(repo.save(binding) for repo, binding in zip(repositories, bindings, strict=True)),
            return_exceptions=True,
        )
        winners = [result for result in results if isinstance(result, PlayerBinding)]
        assert len(winners) == 1
        assert sum(isinstance(result, BindingConflictError) for result in results) == 1
        assert await repositories[0].get(identity) == winners[0]

    run_async(race())


def test_concurrent_identical_binds_are_idempotent(repository, identity, metadata, run_async):
    first = PlayerBinding(identity, AccountId(123), metadata.fetched_at)

    async def race():
        results = await asyncio.gather(*(repository.save(first) for _ in range(6)))
        assert results == [first] * 6

    run_async(race())


@pytest.mark.parametrize(
    "setup",
    [
        "PRAGMA user_version = 2",
        "PRAGMA application_id = 1",
        "CREATE TABLE foreign_data (value TEXT)",
    ],
)
def test_refuses_unknown_or_foreign_database_without_overwriting(tmp_path, run_async, setup):
    database = tmp_path / "foreign.sqlite3"
    with closing(sqlite3.connect(database)) as connection, connection:
        connection.execute(setup)
    before = database.read_bytes()
    with pytest.raises(RepositoryError):
        run_async(SQLiteBindingRepository(database).initialize())
    assert database.read_bytes() == before


def test_rejects_corrupt_stored_values_instead_of_reporting_unbound(
    repository, identity, metadata, tmp_path, run_async
):
    run_async(repository.save(PlayerBinding(identity, AccountId(123), metadata.fetched_at)))
    with closing(sqlite3.connect(tmp_path / "bindings.sqlite3")) as connection, connection:
        connection.execute("UPDATE bindings SET bound_at = ?", ("invalid-private-content",))
    with pytest.raises(RepositoryError) as caught:
        run_async(repository.get(identity))
    assert "invalid-private-content" not in "".join(traceback.format_exception(caught.value))


def test_corrupt_schema_and_uninitialized_database_fail_closed(tmp_path, identity, run_async):
    repository = SQLiteBindingRepository(tmp_path / "schema.sqlite3")
    with pytest.raises(RepositoryError):
        run_async(repository.get(identity))
    run_async(repository.initialize())
    with closing(sqlite3.connect(tmp_path / "schema.sqlite3")) as connection, connection:
        connection.execute("ALTER TABLE bindings ADD COLUMN unexpected TEXT")
    with pytest.raises(RepositoryError):
        run_async(repository.initialize())
    with pytest.raises(RepositoryError):
        run_async(repository.get(identity))


def test_io_failure_is_sanitized_and_does_not_create_directories(tmp_path, run_async):
    database = tmp_path / "private-directory" / "bindings.sqlite3"
    with pytest.raises(RepositoryError) as caught:
        run_async(SQLiteBindingRepository(database).initialize())
    assert not database.parent.exists()
    assert str(database) not in "".join(traceback.format_exception(caught.value))
    assert caught.value.__suppress_context__


def test_locked_database_reports_failure_then_recovers(
    repository, identity, metadata, tmp_path, run_async
):
    limited = SQLiteBindingRepository(tmp_path / "bindings.sqlite3", timeout_seconds=0.01)
    binding = PlayerBinding(identity, AccountId(123), metadata.fetched_at)
    with closing(sqlite3.connect(tmp_path / "bindings.sqlite3")) as connection, connection:
        connection.execute("BEGIN IMMEDIATE")
        with pytest.raises(RepositoryError):
            run_async(limited.save(binding))
        assert run_async(repository.get(identity)) is None
    assert run_async(limited.save(binding)) == binding


@pytest.mark.parametrize("timeout", [0, -1, True, float("inf"), float("nan"), "5"])
def test_invalid_timeouts(tmp_path, timeout):
    with pytest.raises(ValidationError):
        SQLiteBindingRepository(tmp_path / "unused.sqlite3", timeout_seconds=timeout)


@pytest.mark.parametrize("path", [None, 123, "", " ", ":memory:"])
def test_invalid_database_paths(path):
    with pytest.raises(ValidationError):
        SQLiteBindingRepository(path)


def test_repository_rejects_unvalidated_objects(repository, identity, metadata, run_async):
    for operation in (repository.get, repository.delete, repository.save):
        with pytest.raises(ValidationError):
            run_async(operation("invalid-private-identity"))
    with pytest.raises(ValidationError):
        run_async(
            repository.save(PlayerBinding(identity, AccountId(123), metadata.fetched_at), replace=1)
        )
