"""File-backed binding storage with atomic writes and per-operation connections."""

from __future__ import annotations

import math
import sqlite3
from collections.abc import Callable
from contextlib import closing
from datetime import datetime
from pathlib import Path

from ..domain.errors import BindingConflictError, RepositoryError, ValidationError
from ..domain.identity import AccountId, PlatformIdentity
from ..domain.models import PlayerBinding
from ._worker import run_storage

_APPLICATION_ID = 0x44324647
_SCHEMA_VERSION = 1
_COLUMNS = "namespace, platform, bot_id, user_id, account_id, bound_at"
_KEY = "namespace = ? AND platform = ? AND bot_id = ? AND user_id = ?"


class SQLiteBindingRepository:
    """Use a dedicated database and call initialize before use.

    No connection survives an operation. Cancellation waits for its worker to exit;
    an already-running transaction may still commit. Re-read before retrying
    an ambiguous replacement. Identical binds and repeated deletes are idempotent.
    """

    def __init__(self, database: str | Path, *, timeout_seconds: float = 5.0) -> None:
        if not isinstance(database, (str, Path)) or not str(database).strip():
            raise ValidationError("Expected a SQLite database file path")
        if str(database) == ":memory:":
            raise ValidationError("Binding storage requires a persistent file")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValidationError("SQLite timeout must be finite and positive")
        self._database = Path(database).resolve()
        self._timeout = timeout_seconds

    async def initialize(self) -> None:
        await run_storage(lambda: self._run(self._initialize, write=True, initialize=True))

    async def get(self, identity: PlatformIdentity) -> PlayerBinding | None:
        key = self._identity_key(identity)

        def query(connection: sqlite3.Connection) -> PlayerBinding | None:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM bindings WHERE {_KEY}", key
            ).fetchone()
            return self._decode(row) if row is not None else None

        return await run_storage(lambda: self._run(query))

    async def save(self, binding: PlayerBinding, *, replace: bool = False) -> PlayerBinding:
        if not isinstance(binding, PlayerBinding) or type(replace) is not bool:
            raise ValidationError("Expected a binding and an explicit replacement flag")
        key = self._identity_key(binding.identity)

        def write(connection: sqlite3.Connection) -> PlayerBinding:
            row = connection.execute(
                f"SELECT {_COLUMNS} FROM bindings WHERE {_KEY}", key
            ).fetchone()
            if row is not None:
                previous = self._decode(row)
                if previous.account_id == binding.account_id:
                    return previous
                if not replace:
                    raise BindingConflictError()
            connection.execute(
                f"INSERT INTO bindings ({_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?) "
                "ON CONFLICT(namespace, platform, bot_id, user_id) DO UPDATE SET "
                "account_id = excluded.account_id, bound_at = excluded.bound_at",
                (*key, binding.account_id.value, binding.bound_at.isoformat()),
            )
            return binding

        return await run_storage(lambda: self._run(write, write=True))

    async def delete(self, identity: PlatformIdentity) -> bool:
        key = self._identity_key(identity)

        def delete(connection: sqlite3.Connection) -> bool:
            return connection.execute(f"DELETE FROM bindings WHERE {_KEY}", key).rowcount > 0

        return await run_storage(lambda: self._run(delete, write=True))

    def _run[T](
        self,
        operation: Callable[[sqlite3.Connection], T],
        *,
        write: bool = False,
        initialize: bool = False,
    ) -> T:
        try:
            with closing(sqlite3.connect(self._database, timeout=self._timeout)) as connection:
                connection.row_factory = sqlite3.Row
                with connection:
                    if write:
                        connection.execute("BEGIN IMMEDIATE")
                    if not initialize:
                        self._check_schema(connection)
                    return operation(connection)
        except (sqlite3.Error, OSError):
            raise RepositoryError() from None

    @staticmethod
    def _initialize(connection: sqlite3.Connection) -> None:
        application_id = connection.execute("PRAGMA application_id").fetchone()[0]
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if application_id == _APPLICATION_ID and version == _SCHEMA_VERSION:
            SQLiteBindingRepository._check_schema(connection)
            return
        has_tables = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' LIMIT 1"
        ).fetchone()
        if application_id != 0 or version != 0 or has_tables:
            raise RepositoryError()
        connection.execute(
            "CREATE TABLE bindings ("
            "namespace TEXT NOT NULL, platform TEXT NOT NULL, bot_id TEXT NOT NULL, "
            "user_id TEXT NOT NULL, "
            "account_id INTEGER NOT NULL CHECK(account_id BETWEEN 1 AND 4294967294), "
            "bound_at TEXT NOT NULL, PRIMARY KEY(namespace, platform, bot_id, user_id))"
        )
        connection.execute(f"PRAGMA application_id = {_APPLICATION_ID}")
        connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")

    @staticmethod
    def _check_schema(connection: sqlite3.Connection) -> None:
        application_id = connection.execute("PRAGMA application_id").fetchone()[0]
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        columns = connection.execute("PRAGMA table_info(bindings)").fetchall()
        expected = [
            ("namespace", "TEXT", 1, 1),
            ("platform", "TEXT", 1, 2),
            ("bot_id", "TEXT", 1, 3),
            ("user_id", "TEXT", 1, 4),
            ("account_id", "INTEGER", 1, 0),
            ("bound_at", "TEXT", 1, 0),
        ]
        actual = [(row["name"], row["type"], row["notnull"], row["pk"]) for row in columns]
        if application_id != _APPLICATION_ID or version != _SCHEMA_VERSION or actual != expected:
            raise RepositoryError()

    @staticmethod
    def _identity_key(identity: PlatformIdentity) -> tuple[str, str, str, str]:
        if not isinstance(identity, PlatformIdentity):
            raise ValidationError("Expected a validated platform identity")
        return identity.namespace, identity.platform, identity.bot_id, identity.user_id

    @staticmethod
    def _decode(row: sqlite3.Row) -> PlayerBinding:
        try:
            return PlayerBinding(
                PlatformIdentity(row["namespace"], row["platform"], row["bot_id"], row["user_id"]),
                AccountId(row["account_id"]),
                datetime.fromisoformat(row["bound_at"]),
            )
        except (ValueError, TypeError):
            raise RepositoryError() from None
