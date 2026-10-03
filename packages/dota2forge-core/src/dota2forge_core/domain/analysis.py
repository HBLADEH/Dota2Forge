"""Source-specific match economics with explicit metric semantics."""

from dataclasses import dataclass, field
from enum import StrEnum

from .errors import DataSource, ValidationError
from .identity import AccountId
from .match_detail import MatchId
from .models import DataMetadata, require_nonnegative


class MetricSemantic(StrEnum):
    NETWORTH_LEVEL = "networth_level"
    COLLECTED_GOLD = "collected_gold"
    EXPERIENCE_TOTAL = "experience_total"


@dataclass(frozen=True, slots=True)
class MetricSeries:
    name: str
    semantic: MetricSemantic
    values: tuple[int, ...]
    start_seconds: int = 0
    interval_seconds: int = 60

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name or len(self.name) > 64:
            raise ValidationError("Expected a bounded metric name")
        if not isinstance(self.semantic, MetricSemantic):
            raise ValidationError("Expected a known metric semantic")
        if not isinstance(self.values, tuple) or len(self.values) > 360:
            raise ValidationError("Expected a bounded immutable metric series")
        require_nonnegative(self.start_seconds)
        if type(self.interval_seconds) is not int or self.interval_seconds <= 0:
            raise ValidationError("Expected a positive metric interval")
        for value in self.values:
            require_nonnegative(value)


@dataclass(frozen=True, slots=True)
class PurchaseEvent:
    time_seconds: int
    item_id: int | None = None
    item_key: str | None = field(default=None, repr=False)
    charges: int | None = None

    def __post_init__(self) -> None:
        require_nonnegative(self.time_seconds)
        require_nonnegative(self.item_id)
        require_nonnegative(self.charges)
        if self.item_key is not None and (
            not isinstance(self.item_key, str) or not self.item_key or len(self.item_key) > 128
        ):
            raise ValidationError("Invalid purchase item key")
        if self.item_id is None and self.item_key is None:
            raise ValidationError("A purchase requires an item ID or key")


@dataclass(frozen=True, slots=True)
class ParticipantAnalysis:
    account_id: AccountId | None
    player_slot: int | None
    metrics: tuple[MetricSeries, ...] = ()
    purchases: tuple[PurchaseEvent, ...] | None = None

    def __post_init__(self) -> None:
        if self.account_id is not None and not isinstance(self.account_id, AccountId):
            raise ValidationError("Expected a validated analysis account")
        require_nonnegative(self.player_slot)
        if self.player_slot is not None and self.player_slot > 255:
            raise ValidationError("Analysis player slot exceeds the upstream byte range")
        if not isinstance(self.metrics, tuple) or len(
            {metric.name for metric in self.metrics}
        ) != len(self.metrics):
            raise ValidationError("Expected unique immutable analysis metrics")
        if not all(isinstance(metric, MetricSeries) for metric in self.metrics):
            raise ValidationError("Expected validated analysis metrics")
        if self.purchases is not None and (
            not isinstance(self.purchases, tuple)
            or len(self.purchases) > 1024
            or not all(isinstance(item, PurchaseEvent) for item in self.purchases)
        ):
            raise ValidationError("Expected bounded purchase events or missing data")


@dataclass(frozen=True, slots=True)
class MatchAnalysis:
    match_id: MatchId
    metadata: DataMetadata
    participants: tuple[ParticipantAnalysis, ...] | None

    def __post_init__(self) -> None:
        if not isinstance(self.match_id, MatchId) or not isinstance(self.metadata, DataMetadata):
            raise ValidationError("Expected validated analysis identity and metadata")
        if self.metadata.source not in {DataSource.STRATZ, DataSource.OPENDOTA}:
            raise ValidationError("Analysis requires a supported source")
        if self.participants is not None and (
            not isinstance(self.participants, tuple)
            or len(self.participants) > 10
            or not all(isinstance(player, ParticipantAnalysis) for player in self.participants)
        ):
            raise ValidationError("Expected up to ten analysis participants")
        slots = [player.player_slot for player in self.participants or ()]
        if None not in slots and len(set(slots)) != len(slots):
            raise ValidationError("Duplicate analysis participant slot")
        accounts = [
            player.account_id for player in self.participants or () if player.account_id is not None
        ]
        if len(set(accounts)) != len(accounts):
            raise ValidationError("Duplicate analysis participant account")

    @property
    def missing_fields(self) -> tuple[str, ...]:
        return () if self.participants is not None else ("participants",)


@dataclass(frozen=True, slots=True)
class MatchAnalysisUnavailable:
    match_id: MatchId
    metadata: DataMetadata

    def __post_init__(self) -> None:
        if not isinstance(self.match_id, MatchId) or not isinstance(self.metadata, DataMetadata):
            raise ValidationError("Expected validated analysis identity and metadata")


type MatchAnalysisResult = MatchAnalysis | MatchAnalysisUnavailable
