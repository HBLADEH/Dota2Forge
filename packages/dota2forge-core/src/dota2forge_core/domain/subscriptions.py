"""Immutable subscriptions and observations; delivery remains a host responsibility."""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import StrEnum

from .errors import DataSource, ProviderError, ValidationError
from .identity import AccountId, PlatformIdentity
from .match_detail import MatchId
from .match_reports import MatchReport
from .models import DataMetadata, MatchSummary, require_aware_time, require_nonnegative
from .subscription_reports import DailyReport, report_bounds


def require_subscription_id(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{32}", value):
        raise ValidationError("Expected an opaque subscription or event ID")


def require_subscription_limit(value: int) -> None:
    if type(value) is not int or not 1 <= value <= 100:
        raise ValidationError("Subscription page limits must be integers between 1 and 100")


class SubscriptionKind(StrEnum):
    NEW_MATCH = "new_match"
    RANK_CHANGE = "rank_change"
    DAILY_REPORT = "daily_report"
    MATCH_REPORT = "match_report"


class DeliveryOutcome(StrEnum):
    ACCEPTED = "accepted"
    NOT_ATTEMPTED = "not_attempted"
    UNCERTAIN = "uncertain"


@dataclass(frozen=True, slots=True)
class SubscriptionScope:
    namespace: str
    platform: str
    bot_id: str = field(repr=False)

    def __post_init__(self) -> None:
        PlatformIdentity(self.namespace, self.platform, self.bot_id, "scope")

    @classmethod
    def for_identity(cls, identity: PlatformIdentity) -> "SubscriptionScope":
        if not isinstance(identity, PlatformIdentity):
            raise ValidationError("Expected a trusted subscription owner")
        return cls(identity.namespace, identity.platform, identity.bot_id)


@dataclass(frozen=True, slots=True)
class SubscriptionKey:
    identity: PlatformIdentity = field(repr=False)
    destination: str = field(repr=False)
    account_id: AccountId | None = field(repr=False)
    source: DataSource
    kind: SubscriptionKind
    match_id: MatchId | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.identity, PlatformIdentity):
            raise ValidationError("Expected validated subscription identities")
        if (
            not isinstance(self.destination, str)
            or not 1 <= len(self.destination) <= 512
            or not self.destination.isprintable()
            or any(character.isspace() for character in self.destination)
        ):
            raise ValidationError("Expected a bounded opaque delivery destination")
        if not isinstance(self.source, DataSource) or not isinstance(self.kind, SubscriptionKind):
            raise ValidationError("Expected a subscription source and kind")
        if self.kind == SubscriptionKind.MATCH_REPORT:
            if self.account_id is not None or not isinstance(self.match_id, MatchId):
                raise ValidationError("A match subscription requires only a match ID")
        elif not isinstance(self.account_id, AccountId) or self.match_id is not None:
            raise ValidationError("A player subscription requires an account ID")


@dataclass(frozen=True, slots=True)
class SubscriptionCheckpoint:
    fetched_at: datetime | None = None
    match_started_at: datetime | None = None
    match_ids: tuple[int, ...] = ()
    rank_tier: int | None = None
    report_date: date | None = None
    match_reported: bool = False

    def __post_init__(self) -> None:
        for instant in (self.fetched_at, self.match_started_at):
            if instant is not None:
                require_aware_time(instant)
        if not isinstance(self.match_ids, tuple) or len(self.match_ids) > 100:
            raise ValidationError("Expected a bounded unique match frontier")
        for match_id in self.match_ids:
            MatchId(match_id)
        if len(set(self.match_ids)) != len(self.match_ids):
            raise ValidationError("Expected a bounded unique match frontier")
        require_nonnegative(self.rank_tier)
        if self.report_date is not None:
            report_bounds(self.report_date)
        if (self.match_started_at is None) != (not self.match_ids):
            raise ValidationError("A match frontier requires a timestamp and IDs")
        if self.fetched_at is None and (
            self.match_started_at is not None
            or self.rank_tier is not None
            or self.report_date is not None
            or self.match_reported
        ):
            raise ValidationError("A checkpoint requires a source fetch timestamp")
        if type(self.match_reported) is not bool:
            raise ValidationError("A match checkpoint requires a boolean completion state")


@dataclass(frozen=True, slots=True)
class Subscription:
    subscription_id: str
    key: SubscriptionKey = field(repr=False)
    created_at: datetime
    checkpoint: SubscriptionCheckpoint = field(default_factory=SubscriptionCheckpoint)
    revision: int = 0

    def __post_init__(self) -> None:
        require_subscription_id(self.subscription_id)
        require_aware_time(self.created_at)
        if not isinstance(self.key, SubscriptionKey) or not isinstance(
            self.checkpoint, SubscriptionCheckpoint
        ):
            raise ValidationError("Expected a validated subscription key and checkpoint")
        require_nonnegative(self.revision)
        if type(self.revision) is not int:
            raise ValidationError("Expected a subscription revision")
        if self.key.kind == SubscriptionKind.NEW_MATCH:
            if (
                self.checkpoint.rank_tier is not None
                or self.checkpoint.report_date is not None
                or self.checkpoint.match_reported
            ):
                raise ValidationError("A match subscription cannot store a rank checkpoint")
        elif self.key.kind == SubscriptionKind.RANK_CHANGE:
            if (
                self.checkpoint.match_started_at is not None
                or self.checkpoint.report_date is not None
                or self.checkpoint.match_reported
            ):
                raise ValidationError("A rank subscription cannot store another checkpoint kind")
        elif self.key.kind == SubscriptionKind.DAILY_REPORT:
            if (
                self.checkpoint.match_started_at is not None
                or self.checkpoint.rank_tier is not None
                or self.checkpoint.match_reported
            ):
                raise ValidationError("A daily subscription cannot store another checkpoint kind")
        elif self.key.kind == SubscriptionKind.MATCH_REPORT:
            if (
                self.checkpoint.match_started_at is not None
                or self.checkpoint.rank_tier is not None
                or self.checkpoint.report_date is not None
            ):
                raise ValidationError("A match subscription cannot store another checkpoint kind")
        elif self.checkpoint.match_started_at is not None or self.checkpoint.rank_tier is not None:
            raise ValidationError("A daily subscription cannot store another checkpoint kind")
        if self.checkpoint.fetched_at is not None and self.checkpoint.fetched_at < self.created_at:
            raise ValidationError("A checkpoint cannot predate its subscription")


@dataclass(frozen=True, slots=True)
class RankChange:
    previous_rank: int
    current_rank: int
    metadata: DataMetadata

    def __post_init__(self) -> None:
        for rank in (self.previous_rank, self.current_rank):
            require_nonnegative(rank)
            if type(rank) is not int:
                raise ValidationError("Rank changes require two known ranks")
        if self.previous_rank == self.current_rank or not isinstance(self.metadata, DataMetadata):
            raise ValidationError("Expected a rank change with source metadata")


@dataclass(frozen=True, slots=True)
class SubscriptionEvent:
    event_id: str
    subscription_id: str
    key: SubscriptionKey = field(repr=False)
    detected_at: datetime
    payload: MatchSummary | RankChange | DailyReport | MatchReport = field(repr=False)

    def __post_init__(self) -> None:
        require_subscription_id(self.event_id)
        require_subscription_id(self.subscription_id)
        require_aware_time(self.detected_at)
        if not isinstance(self.key, SubscriptionKey):
            raise ValidationError("Expected an event subscription key")
        if isinstance(self.payload, MatchReport):
            valid = self.key.kind in {SubscriptionKind.NEW_MATCH, SubscriptionKind.MATCH_REPORT}
            if self.key.kind == SubscriptionKind.MATCH_REPORT:
                valid = valid and self.key.match_id == self.payload.match_id
            if self.key.kind == SubscriptionKind.NEW_MATCH:
                valid = valid and self.payload.tracked_account_id == self.key.account_id
        elif isinstance(self.payload, MatchSummary):
            valid = (
                self.key.kind == SubscriptionKind.NEW_MATCH
                and self.payload.account_id == self.key.account_id
                and self.payload.is_win is not None
            )
            MatchId(self.payload.match_id)
        elif isinstance(self.payload, RankChange):
            valid = self.key.kind == SubscriptionKind.RANK_CHANGE
        elif isinstance(self.payload, DailyReport):
            valid = (
                self.key.kind == SubscriptionKind.DAILY_REPORT
                and self.payload.account_id == self.key.account_id
            )
        else:
            raise ValidationError("Expected a match or rank event payload")
        if not valid or self.payload.metadata.source != self.key.source:
            raise ValidationError("Inconsistent subscription event observation")


class SubscriptionPollState(StrEnum):
    BASELINED = "baselined"
    UNCHANGED = "unchanged"
    EVENTS = "events"
    EMPTY = "empty"
    UNKNOWN = "unknown"
    STALE = "stale"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class SubscriptionPollResult:
    subscription: Subscription = field(repr=False)
    state: SubscriptionPollState
    events: tuple[SubscriptionEvent, ...] = field(default=(), repr=False)
    coverage_gap: bool = False
    failure: ProviderError | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.subscription, Subscription) or not isinstance(
            self.state, SubscriptionPollState
        ):
            raise ValidationError("Expected a subscription poll classification")
        if type(self.coverage_gap) is not bool or not isinstance(self.events, tuple):
            raise ValidationError("Expected immutable events and an explicit coverage flag")
        for event in self.events:
            if (
                not isinstance(event, SubscriptionEvent)
                or event.subscription_id != self.subscription.subscription_id
                or event.key != self.subscription.key
            ):
                raise ValidationError("Poll events must belong to their subscription")
        if (self.state == SubscriptionPollState.EVENTS) != bool(self.events):
            raise ValidationError("Event classification must match the poll events")
        if self.state == SubscriptionPollState.FAILED:
            if not isinstance(self.failure, ProviderError) or (
                self.failure.source != self.subscription.key.source
            ):
                raise ValidationError("Failed polls require a classified source error")
        elif self.failure is not None:
            raise ValidationError("Only failed polls can contain an error")
