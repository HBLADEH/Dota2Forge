"""Dedicated SQLite subscription store, with transactional checkpoints and outbox."""

import math
import sqlite3
from collections.abc import Callable
from contextlib import closing
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from ..domain.errors import (
    SubscriptionCapacityError,
    SubscriptionRepositoryError,
    ValidationError,
)
from ..domain.identity import PlatformIdentity
from ..domain.models import require_aware_time
from ..domain.subscriptions import (
    Subscription,
    SubscriptionCheckpoint,
    SubscriptionEvent,
    SubscriptionKind,
    SubscriptionScope,
    require_subscription_id,
    require_subscription_limit,
)
from ._subscription_codec import (
    decode_event,
    decode_subscription,
    encode_checkpoint,
    encode_event,
)
from ._worker import run_storage

_APPLICATION_ID = 0x44325355
_SCHEMA_VERSION = 3
_COLUMNS = (
    "subscription_id, namespace, platform, bot_id, user_id, destination, "
    "account_id, match_id, source, kind, created_at, checkpoint, revision"
)
_LEGACY_COLUMNS = (
    "subscription_id, namespace, platform, bot_id, user_id, destination, "
    "account_id, source, kind, created_at, checkpoint, revision"
)
_OWNER = "namespace = ? AND platform = ? AND bot_id = ? AND user_id = ?"
_KEY = (
    _OWNER
    + " AND destination = ? AND account_id IS ? AND match_id IS ? AND source = ? AND kind = ?"
)
_JOIN = "subscription_events AS events JOIN subscriptions USING (subscription_id)"


class SQLiteSubscriptionRepository:
    """Explicit initialization; no persistent connections, timers or delivery workers."""

    def __init__(
        self,
        database: str | Path,
        *,
        timeout_seconds: float = 5.0,
        max_subscriptions: int = 1000,
        max_pending_events: int = 1000,
    ) -> None:
        if (
            not isinstance(database, (str, Path))
            or not str(database).strip()
            or str(database) == ":memory:"
        ):
            raise ValidationError("Subscription storage requires a dedicated persistent file")
        if (
            isinstance(timeout_seconds, bool)
            or not isinstance(timeout_seconds, (int, float))
            or not math.isfinite(timeout_seconds)
            or timeout_seconds <= 0
        ):
            raise ValidationError("SQLite timeout must be finite and positive")
        for capacity in (max_subscriptions, max_pending_events):
            if type(capacity) is not int or capacity < 1:
                raise ValidationError("Subscription capacities must be positive integers")
        self._database = Path(database).resolve()
        self._timeout = timeout_seconds
        self._max_subscriptions = max_subscriptions
        self._max_pending_events = max_pending_events

    async def initialize(self) -> None:
        await run_storage(lambda: self._run(self._initialize, write=True, initialize=True))

    async def save(self, subscription: Subscription) -> Subscription:
        if (
            not isinstance(subscription, Subscription)
            or subscription.revision != 0
            or (subscription.checkpoint != SubscriptionCheckpoint())
        ):
            raise ValidationError("Only a new subscription can be saved")
        key = subscription.key
        owner = self._owner(key.identity)
        values = (
            *owner,
            key.destination,
            None if key.account_id is None else key.account_id.value,
            None if key.match_id is None else key.match_id.value,
            key.source.value,
            key.kind.value,
        )

        def save(connection: sqlite3.Connection) -> Subscription:
            row = connection.execute(f"SELECT * FROM subscriptions WHERE {_KEY}", values).fetchone()
            if row is not None:
                return decode_subscription(row)
            count = connection.execute(
                "SELECT count(*) FROM subscriptions WHERE namespace = ? AND platform = ? "
                "AND bot_id = ?",
                owner[:3],
            ).fetchone()[0]
            if count >= self._max_subscriptions:
                raise SubscriptionCapacityError()
            connection.execute(
                f"INSERT INTO subscriptions ({_COLUMNS}) VALUES ({', '.join(['?'] * 13)})",
                (
                    subscription.subscription_id,
                    *values,
                    subscription.created_at.isoformat(),
                    encode_checkpoint(subscription.checkpoint),
                    subscription.revision,
                ),
            )
            return subscription

        return await run_storage(lambda: self._run(save, write=True))

    async def list(
        self,
        scope: SubscriptionScope,
        *,
        owner: PlatformIdentity | None = None,
        kind: SubscriptionKind | None = None,
        destination: str | None = None,
        limit: int = 20,
        after_id: str | None = None,
    ) -> tuple[Subscription, ...]:
        require_subscription_limit(limit)
        clause, values = self._filters(scope, owner)
        if destination is not None:
            if not isinstance(destination, str) or not destination or len(destination) > 512:
                raise ValidationError("Expected a bounded delivery destination")
            clause += " AND destination = ?"
            values += (destination,)
        if kind is not None:
            if not isinstance(kind, SubscriptionKind):
                raise ValidationError("Expected a subscription kind")
            clause += " AND kind = ?"
            values += (kind.value,)
        if after_id is not None:
            require_subscription_id(after_id)
            clause += " AND subscription_id > ?"
            values += (after_id,)

        def query(connection: sqlite3.Connection) -> tuple[Subscription, ...]:
            rows = connection.execute(
                f"SELECT * FROM subscriptions WHERE {clause} ORDER BY subscription_id LIMIT ?",
                (*values, limit),
            ).fetchall()
            return tuple(decode_subscription(row) for row in rows)

        return await run_storage(lambda: self._run(query))

    async def delete(self, identity: PlatformIdentity, subscription_id: str) -> bool:
        owner = self._owner(identity)
        require_subscription_id(subscription_id)

        def delete(connection: sqlite3.Connection) -> bool:
            row = connection.execute(
                f"SELECT * FROM subscriptions WHERE {_OWNER} AND subscription_id = ?",
                (*owner, subscription_id),
            ).fetchone()
            if row is None:
                return False
            decode_subscription(row)
            connection.execute(
                "DELETE FROM subscriptions WHERE subscription_id = ?", (subscription_id,)
            )
            return True

        return await run_storage(lambda: self._run(delete, write=True))

    async def commit(
        self,
        previous: Subscription,
        checkpoint: SubscriptionCheckpoint,
        events: tuple[SubscriptionEvent, ...],
    ) -> bool:
        if not isinstance(previous, Subscription) or not isinstance(
            checkpoint, SubscriptionCheckpoint
        ):
            raise ValidationError("Expected a validated subscription transition")
        current = replace(previous, checkpoint=checkpoint, revision=previous.revision + 1)
        old = previous.checkpoint
        if checkpoint.fetched_at is None or (
            old.fetched_at is not None and checkpoint.fetched_at < old.fetched_at
        ):
            raise ValidationError("Subscription observations cannot move backwards")
        if old.match_started_at is not None and (
            checkpoint.match_started_at is None
            or checkpoint.match_started_at < old.match_started_at
            or (
                checkpoint.match_started_at == old.match_started_at
                and not set(old.match_ids).issubset(checkpoint.match_ids)
            )
        ):
            raise ValidationError("A match frontier cannot be cleared or moved backwards")
        if old.report_date is not None and (
            checkpoint.report_date is None or checkpoint.report_date < old.report_date
        ):
            raise ValidationError("A daily report cursor cannot be cleared or moved backwards")
        if old.match_reported and not checkpoint.match_reported:
            raise ValidationError("A completed match cannot be reopened")
        if not isinstance(events, tuple) or len(events) > 100:
            raise ValidationError("Expected a bounded immutable event batch")
        for event in events:
            if (
                not isinstance(event, SubscriptionEvent)
                or event.subscription_id != previous.subscription_id
                or event.key != previous.key
            ):
                raise ValidationError("Events must belong to their subscription")
        if len({event.event_id for event in events}) != len(events):
            raise ValidationError("Event IDs must be unique")

        def commit(connection: sqlite3.Connection) -> bool:
            row = connection.execute(
                "SELECT * FROM subscriptions WHERE subscription_id = ?", (previous.subscription_id,)
            ).fetchone()
            if row is None or decode_subscription(row) != previous:
                return False
            count = connection.execute(
                "SELECT count(*) FROM subscription_events WHERE subscription_id = ?",
                (previous.subscription_id,),
            ).fetchone()[0]
            if count + len(events) > self._max_pending_events:
                raise SubscriptionCapacityError()
            for event in events:
                connection.execute(
                    "INSERT INTO subscription_events "
                    "(event_id, subscription_id, detected_at, payload) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        event.event_id,
                        event.subscription_id,
                        event.detected_at.isoformat(),
                        encode_event(event),
                    ),
                )
            connection.execute(
                "UPDATE subscriptions SET checkpoint = ?, revision = ? WHERE subscription_id = ?",
                (encode_checkpoint(current.checkpoint), current.revision, current.subscription_id),
            )
            return True

        return await run_storage(lambda: self._run(commit, write=True))

    async def pending(
        self,
        scope: SubscriptionScope,
        *,
        owner: PlatformIdentity | None = None,
        limit: int = 20,
    ) -> tuple[SubscriptionEvent, ...]:
        require_subscription_limit(limit)
        clause, values = self._filters(scope, owner)

        def query(connection: sqlite3.Connection) -> tuple[SubscriptionEvent, ...]:
            rows = connection.execute(
                f"SELECT * FROM {_JOIN} WHERE {clause} ORDER BY sequence LIMIT ?", (*values, limit)
            ).fetchall()
            return tuple(decode_event(row) for row in rows)

        return await run_storage(lambda: self._run(query))

    async def acknowledge(self, identity: PlatformIdentity, event_id: str) -> bool:
        owner = self._owner(identity)
        require_subscription_id(event_id)

        def acknowledge(connection: sqlite3.Connection) -> bool:
            row = connection.execute(
                f"SELECT * FROM {_JOIN} WHERE {_OWNER} AND event_id = ?", (*owner, event_id)
            ).fetchone()
            if row is None:
                return False
            decode_event(row)
            connection.execute("DELETE FROM subscription_events WHERE event_id = ?", (event_id,))
            return True

        return await run_storage(lambda: self._run(acknowledge, write=True))

    @staticmethod
    def _owner(identity: PlatformIdentity) -> tuple[str, str, str, str]:
        SubscriptionScope.for_identity(identity)
        return identity.namespace, identity.platform, identity.bot_id, identity.user_id

    async def delete_all(self, identity: PlatformIdentity) -> int:
        owner = self._owner(identity)

        def delete(connection: sqlite3.Connection) -> int:
            return connection.execute(
                "DELETE FROM subscriptions WHERE namespace = ? AND platform = ? "
                "AND bot_id = ? AND user_id = ?",
                owner,
            ).rowcount

        return await run_storage(lambda: self._run(delete, write=True))

    async def scopes(
        self, namespace: str, *, after: SubscriptionScope | None = None
    ) -> tuple[SubscriptionScope, ...]:
        PlatformIdentity(namespace, "validation", "validation", "validation")
        if after is not None and (
            not isinstance(after, SubscriptionScope) or after.namespace != namespace
        ):
            raise ValidationError("Invalid scope cursor")

        def query(connection: sqlite3.Connection) -> tuple[SubscriptionScope, ...]:
            rows = connection.execute(
                "SELECT DISTINCT namespace, platform, bot_id FROM subscriptions "
                "WHERE namespace = ? "
                + ("AND (platform, bot_id) > (?, ?) " if after is not None else "")
                + "ORDER BY platform, bot_id LIMIT 1",
                (namespace, after.platform, after.bot_id) if after is not None else (namespace,),
            ).fetchall()
            return tuple(SubscriptionScope(row[0], row[1], row[2]) for row in rows)

        return await run_storage(lambda: self._run(query))

    async def deliverable(
        self, scope: SubscriptionScope, *, limit: int = 20, after_sequence: int = 0
    ) -> tuple[SubscriptionEvent, ...]:
        require_subscription_limit(limit)
        if type(after_sequence) is not int or not 0 <= after_sequence < 2**63:
            raise ValidationError("Invalid delivery sequence cursor")
        clause, values = self._filters(scope, None)

        def query(connection: sqlite3.Connection) -> tuple[SubscriptionEvent, ...]:
            rows = connection.execute(
                f"SELECT * FROM {_JOIN} WHERE {clause} AND sequence > ? AND NOT EXISTS "
                "(SELECT 1 FROM subscription_attempts WHERE event_id = events.event_id) "
                "ORDER BY sequence LIMIT ?",
                (*values, after_sequence, limit),
            ).fetchall()
            return tuple(decode_event(row) for row in rows)

        return await run_storage(lambda: self._run(query))

    async def event_sequence(self, scope: SubscriptionScope, event_id: str) -> int | None:
        require_subscription_id(event_id)
        clause, values = self._filters(scope, None)

        def query(connection: sqlite3.Connection) -> int | None:
            row = connection.execute(
                f"SELECT sequence FROM {_JOIN} WHERE {clause} AND event_id = ?",
                (*values, event_id),
            ).fetchone()
            return int(row[0]) if row is not None else None

        return await run_storage(lambda: self._run(query))

    async def claim(
        self, identity: PlatformIdentity, event_id: str, attempted_at: datetime
    ) -> SubscriptionEvent | None:
        owner = self._owner(identity)
        require_subscription_id(event_id)
        require_aware_time(attempted_at)

        def claim(connection: sqlite3.Connection) -> SubscriptionEvent | None:
            row = connection.execute(
                f"SELECT * FROM {_JOIN} WHERE {_OWNER} AND event_id = ?", (*owner, event_id)
            ).fetchone()
            if row is None:
                return None
            event = decode_event(row)
            changed = connection.execute(
                "INSERT INTO subscription_attempts (event_id, attempted_at) VALUES (?, ?) "
                "ON CONFLICT(event_id) DO NOTHING",
                (event_id, attempted_at.isoformat()),
            ).rowcount
            return event if changed else None

        return await run_storage(lambda: self._run(claim, write=True))

    async def release(self, identity: PlatformIdentity, event_id: str) -> bool:
        owner = self._owner(identity)
        require_subscription_id(event_id)

        def release(connection: sqlite3.Connection) -> bool:
            row = connection.execute(
                f"SELECT * FROM {_JOIN} WHERE {_OWNER} AND event_id = ?", (*owner, event_id)
            ).fetchone()
            if row is None:
                return False
            decode_event(row)
            return (
                connection.execute(
                    "DELETE FROM subscription_attempts WHERE event_id = ?", (event_id,)
                ).rowcount
                > 0
            )

        return await run_storage(lambda: self._run(release, write=True))

    @classmethod
    def _filters(
        cls, scope: SubscriptionScope, owner: PlatformIdentity | None
    ) -> tuple[str, tuple[str, ...]]:
        if not isinstance(scope, SubscriptionScope):
            raise ValidationError("Expected a trusted bot subscription scope")
        if owner is not None:
            if SubscriptionScope.for_identity(owner) != scope:
                raise ValidationError("Subscription owner is outside this bot scope")
            return _OWNER, cls._owner(owner)
        return "namespace = ? AND platform = ? AND bot_id = ?", (
            scope.namespace,
            scope.platform,
            scope.bot_id,
        )

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
                connection.execute(
                    "PRAGMA foreign_keys = OFF" if initialize else "PRAGMA foreign_keys = ON"
                )
                with connection:
                    if write:
                        connection.execute("BEGIN IMMEDIATE")
                    if not initialize:
                        self._check_schema(connection)
                    return operation(connection)
        except (sqlite3.Error, OSError, ValueError, TypeError, KeyError, IndexError, OverflowError):
            raise SubscriptionRepositoryError() from None

    @classmethod
    def _initialize(cls, connection: sqlite3.Connection) -> None:
        application_id = connection.execute("PRAGMA application_id").fetchone()[0]
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if application_id == _APPLICATION_ID and version == _SCHEMA_VERSION:
            cls._check_schema(connection)
            return
        if application_id == _APPLICATION_ID and version in {1, 2}:
            cls._check_schema(connection, version=version)
            for row in connection.execute("SELECT * FROM subscriptions"):
                subscription = decode_subscription(row)
                if version == 1 and subscription.key.kind == SubscriptionKind.DAILY_REPORT:
                    raise SubscriptionRepositoryError()
            for row in connection.execute(f"SELECT * FROM {_JOIN}"):
                decode_event(row)
            if version == 2:
                cls._check_schema(connection, version=2)
            cls._migrate_targets(connection)
            if version == 1:
                cls._create_attempts(connection)
            connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
            cls._check_schema(connection)
            return
        has_tables = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' LIMIT 1"
        ).fetchone()
        if application_id != 0 or version != 0 or has_tables:
            raise SubscriptionRepositoryError()
        connection.execute(
            "CREATE TABLE subscriptions (subscription_id TEXT NOT NULL PRIMARY KEY, "
            "namespace TEXT NOT NULL, platform TEXT NOT NULL, bot_id TEXT NOT NULL, "
            "user_id TEXT NOT NULL, destination TEXT NOT NULL, account_id INTEGER, "
            "match_id INTEGER, "
            "source TEXT NOT NULL, kind TEXT NOT NULL, created_at TEXT NOT NULL, "
            "checkpoint TEXT NOT NULL, revision INTEGER NOT NULL, "
            "UNIQUE(namespace, platform, bot_id, user_id, destination, account_id, source, kind), "
            "UNIQUE(namespace, platform, bot_id, user_id, destination, account_id, match_id, "
            "source, kind))"
        )
        connection.execute(
            "CREATE TABLE subscription_events (sequence INTEGER PRIMARY KEY AUTOINCREMENT, "
            "event_id TEXT NOT NULL UNIQUE, subscription_id TEXT NOT NULL "
            "REFERENCES subscriptions(subscription_id) ON DELETE CASCADE, "
            "detected_at TEXT NOT NULL, payload TEXT NOT NULL)"
        )
        connection.execute(f"PRAGMA application_id = {_APPLICATION_ID}")
        cls._create_attempts(connection)
        connection.execute(f"PRAGMA user_version = {_SCHEMA_VERSION}")
        cls._check_schema(connection)

    @staticmethod
    def _check_schema(connection: sqlite3.Connection, *, version: int = _SCHEMA_VERSION) -> None:
        if (
            connection.execute("PRAGMA application_id").fetchone()[0] != _APPLICATION_ID
            or connection.execute("PRAGMA user_version").fetchone()[0] != version
        ):
            raise SubscriptionRepositoryError()
        legacy = version in {1, 2}
        expected_columns = _LEGACY_COLUMNS.split(", ") if legacy else _COLUMNS.split(", ")
        expected: dict[str, list[tuple[str, str, int, int]]] = {
            "subscriptions": [
                (
                    name,
                    "INTEGER" if name in {"account_id", "match_id", "revision"} else "TEXT",
                    1 if legacy or name not in {"account_id", "match_id"} else 0,
                    int(name == "subscription_id"),
                )
                for name in expected_columns
            ],
            "subscription_events": [
                ("sequence", "INTEGER", 0, 1),
                ("event_id", "TEXT", 1, 0),
                ("subscription_id", "TEXT", 1, 0),
                ("detected_at", "TEXT", 1, 0),
                ("payload", "TEXT", 1, 0),
            ],
        }
        if version in {2, 3}:
            expected["subscription_attempts"] = [
                ("event_id", "TEXT", 1, 1),
                ("attempted_at", "TEXT", 1, 0),
            ]
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if tables != set(expected):
            raise SubscriptionRepositoryError()
        for table, expected_table_columns in expected.items():
            actual = [
                (row["name"], row["type"], row["notnull"], row["pk"])
                for row in connection.execute(f"PRAGMA table_info({table})")
            ]
            if actual != expected_table_columns:
                raise SubscriptionRepositoryError()
        expected_unique: dict[str, set[tuple[str, ...]]] = {
            "subscriptions": {
                ("subscription_id",),
                (
                    "namespace",
                    "platform",
                    "bot_id",
                    "user_id",
                    "destination",
                    "account_id",
                    "source",
                    "kind",
                ),
            },
            "subscription_events": {("event_id",)},
        }
        if version == 3:
            expected_unique["subscriptions"].add(
                (
                    "namespace",
                    "platform",
                    "bot_id",
                    "user_id",
                    "destination",
                    "account_id",
                    "match_id",
                    "source",
                    "kind",
                )
            )
        for table, indexes in expected_unique.items():
            actual_indexes = {
                tuple(
                    row["name"]
                    for row in connection.execute(
                        "SELECT name FROM pragma_index_info(?) ORDER BY seqno", (index["name"],)
                    )
                )
                for index in connection.execute(f"PRAGMA index_list({table})")
                if index["unique"] and not index["partial"]
            }
            if actual_indexes != indexes:
                raise SubscriptionRepositoryError()
        if version in {2, 3}:
            attempts = connection.execute(
                "PRAGMA foreign_key_list(subscription_attempts)"
            ).fetchall()
            if len(attempts) != 1 or (
                attempts[0]["table"],
                attempts[0]["from"],
                attempts[0]["to"],
                attempts[0]["on_delete"],
            ) != ("subscription_events", "event_id", "event_id", "CASCADE"):
                raise SubscriptionRepositoryError()
        foreign_keys = connection.execute("PRAGMA foreign_key_list(subscription_events)").fetchall()
        if len(foreign_keys) != 1 or (
            foreign_keys[0]["table"],
            foreign_keys[0]["from"],
            foreign_keys[0]["to"],
            foreign_keys[0]["on_delete"],
        ) != ("subscriptions", "subscription_id", "subscription_id", "CASCADE"):
            raise SubscriptionRepositoryError()
        if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
            raise SubscriptionRepositoryError()

    @staticmethod
    def _create_attempts(connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE TABLE subscription_attempts (event_id TEXT NOT NULL PRIMARY KEY "
            "REFERENCES subscription_events(event_id) ON DELETE CASCADE, "
            "attempted_at TEXT NOT NULL)"
        )

    @staticmethod
    def _migrate_targets(connection: sqlite3.Connection) -> None:
        connection.execute(
            "CREATE TABLE subscriptions_new (subscription_id TEXT NOT NULL PRIMARY KEY, "
            "namespace TEXT NOT NULL, platform TEXT NOT NULL, bot_id TEXT NOT NULL, "
            "user_id TEXT NOT NULL, destination TEXT NOT NULL, account_id INTEGER, "
            "match_id INTEGER, source TEXT NOT NULL, kind TEXT NOT NULL, created_at TEXT NOT NULL, "
            "checkpoint TEXT NOT NULL, revision INTEGER NOT NULL, "
            "UNIQUE(namespace, platform, bot_id, user_id, destination, account_id, source, kind), "
            "UNIQUE(namespace, platform, bot_id, user_id, destination, account_id, match_id, "
            "source, kind))"
        )
        connection.execute(
            "INSERT INTO subscriptions_new (subscription_id, namespace, platform, bot_id, user_id, "
            "destination, account_id, match_id, source, kind, created_at, checkpoint, revision) "
            "SELECT subscription_id, namespace, platform, bot_id, user_id, destination, "
            "account_id, "
            "NULL, source, kind, created_at, checkpoint, revision FROM subscriptions"
        )
        connection.execute("DROP TABLE subscriptions")
        connection.execute("ALTER TABLE subscriptions_new RENAME TO subscriptions")
