"""Strict source-specific mapping for economic series and purchase events."""

from collections.abc import Callable

from ..domain.analysis import (
    MatchAnalysis,
    MatchAnalysisResult,
    MatchAnalysisUnavailable,
    MetricSemantic,
    MetricSeries,
    ParticipantAnalysis,
    PurchaseEvent,
)
from ..domain.errors import ProviderError, ProviderErrorCode, ValidationError
from ..domain.identity import MAX_ACCOUNT_ID, AccountId
from ..domain.match_detail import MatchId
from ..domain.models import DataMetadata
from ._opendota_http import failure as opendota_failure
from ._opendota_mapping import integer as opendota_integer
from ._opendota_mapping import object_value as opendota_object
from ._stratz_http import failure as stratz_failure
from ._stratz_mapping import field, integer, object_value

type Failure = Callable[[ProviderErrorCode], ProviderError]


def _account(value: object, failure: Failure) -> AccountId | None:
    if value is None:
        return None
    if type(value) is not int:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    number = value
    if number in {0, MAX_ACCOUNT_ID + 1}:
        return None
    if number < 1 or number > MAX_ACCOUNT_ID:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    return AccountId(number)


def _series(
    name: str, semantic: MetricSemantic, values: object, failure: Failure
) -> MetricSeries | None:
    if values is None:
        return None
    if not isinstance(values, list) or len(values) > 360:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    try:
        lead = semantic in {
            MetricSemantic.RADIANT_NETWORTH_LEAD,
            MetricSemantic.RADIANT_EXPERIENCE_LEAD,
        }
        parsed = tuple(
            value
            if type(value) is int and (lead or value >= 0)
            else (_ for _ in ()).throw(ValueError())
            for value in values
        )
        return MetricSeries(name, semantic, parsed, -60 if lead else 0)
    except (ValidationError, ValueError):
        raise failure(ProviderErrorCode.INVALID_RESPONSE) from None


def _purchase_events(values: object, failure: Failure) -> tuple[PurchaseEvent, ...] | None:
    if values is None:
        return None
    if not isinstance(values, list) or len(values) > 1024:
        raise failure(ProviderErrorCode.INVALID_RESPONSE)
    events: list[PurchaseEvent] = []
    for value in values:
        if not isinstance(value, dict):
            raise failure(ProviderErrorCode.INVALID_RESPONSE)
        row = value
        raw_time = row.get("time")
        if type(raw_time) is not int:
            raise failure(ProviderErrorCode.INVALID_RESPONSE)
        raw_id = row.get("itemId", row.get("item_id"))
        item_id = None if raw_id is None else raw_id if type(raw_id) is int and raw_id > 0 else None
        if raw_id is not None and item_id is None:
            raise failure(ProviderErrorCode.INVALID_RESPONSE)
        raw_key = row.get("key", row.get("item_key"))
        if raw_key is not None and not isinstance(raw_key, str):
            raise failure(ProviderErrorCode.INVALID_RESPONSE)
        raw_charges = row.get("charges")
        charges = None if raw_charges is None else raw_charges if type(raw_charges) is int else None
        if raw_charges is not None and (charges is None or charges < 0):
            raise failure(ProviderErrorCode.INVALID_RESPONSE)
        try:
            events.append(PurchaseEvent(raw_time, item_id, raw_key, charges))
        except ValidationError:
            raise failure(ProviderErrorCode.INVALID_RESPONSE) from None
    return tuple(events)


def stratz_analysis(
    payload: object, match_id: MatchId, metadata: DataMetadata
) -> MatchAnalysisResult:
    try:
        envelope = object_value(payload)
        if "errors" in envelope and envelope["errors"] != []:
            raise stratz_failure(ProviderErrorCode.INVALID_RESPONSE)
        raw_match = field(object_value(field(envelope, "data")), "match")
        if raw_match is None:
            return MatchAnalysisUnavailable(match_id, metadata)
        match = object_value(raw_match)
        if integer(field(match, "id"), minimum=1) != match_id.value:
            raise stratz_failure(ProviderErrorCode.INVALID_RESPONSE)
        team_metrics = tuple(
            series
            for name, semantic in (
                ("radiantNetworthLeads", MetricSemantic.RADIANT_NETWORTH_LEAD),
                ("radiantExperienceLeads", MetricSemantic.RADIANT_EXPERIENCE_LEAD),
            )
            if (series := _series(name, semantic, match.get(name), stratz_failure)) is not None
        )
        players = field(match, "players")
        if players is None:
            return MatchAnalysis(match_id, metadata, None, team_metrics)
        if not isinstance(players, list) or len(players) > 10:
            raise stratz_failure(ProviderErrorCode.INVALID_RESPONSE)
        result = []
        for raw in players:
            row = object_value(raw)
            account = _account(field(row, "steamAccountId"), stratz_failure)
            slot = field(row, "playerSlot")
            if slot is not None and (type(slot) is not int or not 0 <= slot <= 255):
                raise stratz_failure(ProviderErrorCode.INVALID_RESPONSE)
            stats = field(row, "stats")
            if stats is None:
                result.append(ParticipantAnalysis(account, slot, (), None))
                continue
            stats_row = object_value(stats)
            series = _series(
                "networthPerMinute",
                MetricSemantic.NETWORTH_LEVEL,
                field(stats_row, "networthPerMinute"),
                stratz_failure,
            )
            purchases = _purchase_events(field(stats_row, "itemPurchases"), stratz_failure)
            result.append(
                ParticipantAnalysis(account, slot, () if series is None else (series,), purchases)
            )
        return MatchAnalysis(match_id, metadata, tuple(result), team_metrics)
    except (ValidationError, ValueError, TypeError, KeyError):
        raise stratz_failure(ProviderErrorCode.INVALID_RESPONSE) from None


def opendota_analysis(
    payload: object, match_id: MatchId, metadata: DataMetadata
) -> MatchAnalysisResult:
    try:
        if payload is None:
            return MatchAnalysisUnavailable(match_id, metadata)
        match = opendota_object(payload)
        if opendota_integer(match.get("match_id"), 1) != match_id.value:
            raise opendota_failure(ProviderErrorCode.INVALID_RESPONSE)
        players = match.get("players")
        if players is None:
            return MatchAnalysis(match_id, metadata, None)
        if not isinstance(players, list) or len(players) > 10:
            raise opendota_failure(ProviderErrorCode.INVALID_RESPONSE)
        result = []
        for raw in players:
            row = opendota_object(raw)
            account = _account(row.get("account_id"), opendota_failure)
            slot = row.get("player_slot")
            if slot is not None and (type(slot) is not int or not 0 <= slot <= 255):
                raise opendota_failure(ProviderErrorCode.INVALID_RESPONSE)
            gold = _series(
                "gold_t", MetricSemantic.COLLECTED_GOLD, row.get("gold_t"), opendota_failure
            )
            experience = _series(
                "xp_t", MetricSemantic.EXPERIENCE_TOTAL, row.get("xp_t"), opendota_failure
            )
            metrics = tuple(metric for metric in (gold, experience) if metric is not None)
            purchases = _purchase_events(row.get("purchase_log"), opendota_failure)
            result.append(ParticipantAnalysis(account, slot, metrics, purchases))
        return MatchAnalysis(match_id, metadata, tuple(result))
    except (ValidationError, ValueError, TypeError, KeyError):
        raise opendota_failure(ProviderErrorCode.INVALID_RESPONSE) from None
