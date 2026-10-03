"""JSON-only persistence for validated subscription observations; never pickle."""

import json
import sqlite3
from datetime import date, datetime
from typing import Any, cast

from ..domain.analysis import (
    MatchAnalysis,
    MatchAnalysisUnavailable,
    MetricSemantic,
    MetricSeries,
    ParticipantAnalysis,
    PurchaseEvent,
)
from ..domain.errors import DataSource, ValidationError
from ..domain.identity import AccountId, PlatformIdentity
from ..domain.match_detail import MatchDetail, MatchDetailUnavailable, MatchId, MatchParticipant
from ..domain.match_reports import MatchReport
from ..domain.models import DataMetadata, MatchSummary
from ..domain.subscription_reports import DailyCoverage, DailyReport
from ..domain.subscriptions import (
    RankChange,
    Subscription,
    SubscriptionCheckpoint,
    SubscriptionEvent,
    SubscriptionKey,
    SubscriptionKind,
)

_STATS = (
    "hero_id",
    "duration_seconds",
    "kills",
    "deaths",
    "assists",
    "gold_per_minute",
    "experience_per_minute",
)


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValidationError("Expected a stored JSON object")
    return cast(dict[str, object], value)


def _list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValidationError("Expected stored JSON list")
    return value


def _row_value(row: sqlite3.Row, name: str) -> object | None:
    try:
        value: Any = row[name]
        return cast(object, value)
    except IndexError:
        return None


def _text(value: object) -> str:
    if not isinstance(value, str):
        raise ValidationError("Expected stored text")
    return value


def _integer(value: object) -> int:
    if type(value) is not int:
        raise ValidationError("Expected a stored integer")
    return value


def _optional_integer(value: object) -> int | None:
    return None if value is None else _integer(value)


def _optional_bool(value: object) -> bool | None:
    if value is not None and type(value) is not bool:
        raise ValidationError("Expected a stored boolean or missing value")
    return value


def _stored_bool(value: object) -> bool:
    if type(value) is not bool:
        raise ValidationError("Expected a stored boolean")
    return value


def _time(value: object) -> datetime:
    return datetime.fromisoformat(_text(value))


def _optional_time(value: object) -> datetime | None:
    return None if value is None else _time(value)


def _json(value: object) -> dict[str, object]:
    text = _text(value)
    if len(text) > 65536:
        raise ValidationError("Stored observations exceed their size bound")
    return _object(json.loads(text))


def encode_checkpoint(value: SubscriptionCheckpoint) -> str:
    return json.dumps(
        {
            "fetched_at": value.fetched_at.isoformat() if value.fetched_at else None,
            "match_started_at": value.match_started_at.isoformat()
            if value.match_started_at
            else None,
            "match_ids": value.match_ids,
            "rank_tier": value.rank_tier,
            "report_date": value.report_date.isoformat() if value.report_date else None,
            "match_reported": value.match_reported,
        },
        sort_keys=True,
    )


def decode_subscription(row: sqlite3.Row) -> Subscription:
    checkpoint = _json(row["checkpoint"])
    ids = checkpoint["match_ids"]
    if not isinstance(ids, list):
        raise ValidationError("Expected stored frontier IDs")
    return Subscription(
        row["subscription_id"],
        SubscriptionKey(
            PlatformIdentity(row["namespace"], row["platform"], row["bot_id"], row["user_id"]),
            row["destination"],
            None if row["account_id"] is None else AccountId(row["account_id"]),
            DataSource(row["source"]),
            SubscriptionKind(row["kind"]),
            None
            if _row_value(row, "match_id") is None
            else MatchId(_integer(_row_value(row, "match_id"))),
        ),
        _time(row["created_at"]),
        SubscriptionCheckpoint(
            _optional_time(checkpoint["fetched_at"]),
            _optional_time(checkpoint["match_started_at"]),
            tuple(_integer(value) for value in ids),
            _optional_integer(checkpoint["rank_tier"]),
            date.fromisoformat(_text(checkpoint["report_date"]))
            if checkpoint.get("report_date") is not None
            else None,
            _stored_bool(checkpoint.get("match_reported", False)),
        ),
        row["revision"],
    )


def _metadata(value: DataMetadata) -> dict[str, object]:
    return {
        "source": value.source.value,
        "fetched_at": value.fetched_at.isoformat(),
        "observed_at": value.observed_at.isoformat() if value.observed_at else None,
        "patch": value.patch,
    }


def _decode_metadata(value: object) -> DataMetadata:
    raw = _object(value)
    patch = raw["patch"]
    return DataMetadata(
        DataSource(_text(raw["source"])),
        _time(raw["fetched_at"]),
        _optional_time(raw["observed_at"]),
        None if patch is None else _text(patch),
    )


def encode_event(event: SubscriptionEvent) -> str:
    payload = event.payload
    raw: dict[str, object] = {"metadata": _metadata(payload.metadata)}
    if isinstance(payload, MatchSummary):
        raw.update({name: getattr(payload, name) for name in _STATS})
        raw.update(
            {
                "match_id": payload.match_id,
                "account_id": payload.account_id.value,
                "started_at": payload.started_at.isoformat(),
                "is_win": payload.is_win,
            }
        )
    elif isinstance(payload, MatchReport):
        raw.update(
            {
                "report_type": "match_report",
                "match_id": payload.match_id.value,
                "tracked_account_id": (
                    None if payload.tracked_account_id is None else payload.tracked_account_id.value
                ),
                "summary": None if payload.summary is None else summary_dict(payload.summary),
                "detail": detail_dict(payload.detail),
                "analysis": analysis_dict(payload.analysis),
            }
        )
    elif isinstance(payload, DailyReport):
        raw.update(
            {
                "account_id": payload.account_id.value,
                "report_date": payload.report_date.isoformat(),
                "coverage": payload.coverage.value,
                "matches": [summary_dict(match) for match in payload.matches],
            }
        )
    else:
        raw.update({"previous_rank": payload.previous_rank, "current_rank": payload.current_rank})
    return json.dumps(raw, sort_keys=True)


def decode_event(row: sqlite3.Row) -> SubscriptionEvent:
    subscription = decode_subscription(row)
    raw = _json(row["payload"])
    metadata = _decode_metadata(raw["metadata"])
    payload: MatchSummary | RankChange | DailyReport | MatchReport
    if subscription.key.kind in {SubscriptionKind.NEW_MATCH, SubscriptionKind.MATCH_REPORT} and (
        "report_type" in raw
    ):
        payload = MatchReport(
            MatchId(_integer(raw["match_id"])),
            metadata,
            None
            if raw["tracked_account_id"] is None
            else AccountId(_integer(raw["tracked_account_id"])),
            None if raw["summary"] is None else decode_summary(raw["summary"]),
            decode_detail(raw["detail"]),
            decode_analysis(raw["analysis"]),
        )
    elif subscription.key.kind == SubscriptionKind.NEW_MATCH:
        outcome = raw["is_win"]
        if type(outcome) is not bool:
            raise ValidationError("Stored match events require a known outcome")
        stats = {name: _optional_integer(raw[name]) for name in _STATS}
        payload = MatchSummary(
            _integer(raw["match_id"]),
            AccountId(_integer(raw["account_id"])),
            _time(raw["started_at"]),
            metadata,
            is_win=outcome,
            **stats,
        )
    elif subscription.key.kind == SubscriptionKind.DAILY_REPORT:
        rows = raw["matches"]
        if not isinstance(rows, list) or len(rows) > 100:
            raise ValidationError("Expected bounded stored daily matches")
        payload = DailyReport(
            AccountId(_integer(raw["account_id"])),
            date.fromisoformat(_text(raw["report_date"])),
            metadata,
            tuple(decode_summary(value) for value in rows),
            DailyCoverage(_text(raw["coverage"])),
        )
    else:
        payload = RankChange(
            _integer(raw["previous_rank"]),
            _integer(raw["current_rank"]),
            metadata,
        )
    return SubscriptionEvent(
        row["event_id"],
        subscription.subscription_id,
        subscription.key,
        _time(row["detected_at"]),
        payload,
    )


def summary_dict(match: MatchSummary) -> dict[str, object]:
    raw = {name: getattr(match, name) for name in _STATS}
    raw.update(
        {
            "match_id": match.match_id,
            "account_id": match.account_id.value,
            "started_at": match.started_at.isoformat(),
            "is_win": match.is_win,
            "metadata": _metadata(match.metadata),
        }
    )
    return raw


def decode_summary(value: object) -> MatchSummary:
    raw = _object(value)
    outcome = raw["is_win"]
    if outcome is not None and type(outcome) is not bool:
        raise ValidationError("Expected a stored match outcome or missing value")
    stats = {name: _optional_integer(raw[name]) for name in _STATS}
    return MatchSummary(
        _integer(raw["match_id"]),
        AccountId(_integer(raw["account_id"])),
        _time(raw["started_at"]),
        _decode_metadata(raw["metadata"]),
        is_win=outcome,
        **stats,
    )


def detail_dict(value: object) -> dict[str, object]:
    if isinstance(value, MatchDetailUnavailable):
        return {
            "unavailable": True,
            "match_id": value.match_id.value,
            "metadata": _metadata(value.metadata),
        }
    if not isinstance(value, MatchDetail):
        raise ValidationError("Expected a match detail result")
    return {
        "unavailable": False,
        "match_id": value.match_id.value,
        "metadata": _metadata(value.metadata),
        "started_at": None if value.started_at is None else value.started_at.isoformat(),
        "duration_seconds": value.duration_seconds,
        "did_radiant_win": value.did_radiant_win,
        "game_mode": value.game_mode,
        "game_version_id": value.game_version_id,
        "has_stats": value.has_stats,
        "parsed_at": None if value.parsed_at is None else value.parsed_at.isoformat(),
        "parse_version": value.parse_version,
        "players": None
        if value.players is None
        else [
            {
                "player_slot": player.player_slot,
                "account_id": None if player.account_id is None else player.account_id.value,
                "display_name": player.display_name,
                "is_anonymous": player.is_anonymous,
                "is_radiant": player.is_radiant,
                "hero_id": player.hero_id,
                "kills": player.kills,
                "deaths": player.deaths,
                "assists": player.assists,
                "gold_per_minute": player.gold_per_minute,
                "experience_per_minute": player.experience_per_minute,
                "item_ids": player.item_ids,
            }
            for player in value.players
        ],
    }


def decode_detail(value: object) -> MatchDetail | MatchDetailUnavailable:
    raw = _object(value)
    match_id = MatchId(_integer(raw["match_id"]))
    metadata = _decode_metadata(raw["metadata"])
    if raw["unavailable"] is True:
        return MatchDetailUnavailable(match_id, metadata)
    players = raw["players"]
    if players is not None and not isinstance(players, list):
        raise ValidationError("Expected stored match participants")
    parsed_players = (
        None
        if players is None
        else tuple(
            MatchParticipant(
                player_slot=_optional_integer(row["player_slot"]),
                account_id=None
                if row["account_id"] is None
                else AccountId(_integer(row["account_id"])),
                display_name=None if row["display_name"] is None else _text(row["display_name"]),
                is_anonymous=_optional_bool(row["is_anonymous"]),
                is_radiant=_optional_bool(row["is_radiant"]),
                hero_id=_optional_integer(row["hero_id"]),
                kills=_optional_integer(row["kills"]),
                deaths=_optional_integer(row["deaths"]),
                assists=_optional_integer(row["assists"]),
                gold_per_minute=_optional_integer(row["gold_per_minute"]),
                experience_per_minute=_optional_integer(row["experience_per_minute"]),
                item_ids=tuple(_optional_integer(item) for item in _list(row["item_ids"])),
            )
            for row_value in players
            for row in (_object(row_value),)
        )
    )
    return MatchDetail(
        match_id,
        metadata,
        _optional_time(raw["started_at"]),
        _optional_integer(raw["duration_seconds"]),
        _optional_bool(raw["did_radiant_win"]),
        None if raw["game_mode"] is None else _text(raw["game_mode"]),
        _optional_integer(raw["game_version_id"]),
        _optional_bool(raw["has_stats"]),
        _optional_time(raw["parsed_at"]),
        parsed_players,
        _optional_integer(raw["parse_version"]),
    )


def analysis_dict(value: object) -> dict[str, object]:
    if isinstance(value, MatchAnalysisUnavailable):
        return {
            "unavailable": True,
            "match_id": value.match_id.value,
            "metadata": _metadata(value.metadata),
        }
    if not isinstance(value, MatchAnalysis):
        raise ValidationError("Expected a match analysis result")
    return {
        "unavailable": False,
        "match_id": value.match_id.value,
        "metadata": _metadata(value.metadata),
        "participants": None
        if value.participants is None
        else [
            {
                "account_id": None if player.account_id is None else player.account_id.value,
                "player_slot": player.player_slot,
                "metrics": [
                    {
                        "name": metric.name,
                        "semantic": metric.semantic.value,
                        "values": metric.values,
                        "start_seconds": metric.start_seconds,
                        "interval_seconds": metric.interval_seconds,
                    }
                    for metric in player.metrics
                ],
                "purchases": None
                if player.purchases is None
                else [
                    {
                        "time_seconds": item.time_seconds,
                        "item_id": item.item_id,
                        "item_key": item.item_key,
                        "charges": item.charges,
                    }
                    for item in player.purchases
                ],
            }
            for player in value.participants
        ],
    }


def decode_analysis(value: object) -> MatchAnalysis | MatchAnalysisUnavailable:
    raw = _object(value)
    match_id = MatchId(_integer(raw["match_id"]))
    metadata = _decode_metadata(raw["metadata"])
    if raw["unavailable"] is True:
        return MatchAnalysisUnavailable(match_id, metadata)
    participants = raw["participants"]
    if participants is not None and not isinstance(participants, list):
        raise ValidationError("Expected stored analysis participants")
    parsed = (
        None
        if participants is None
        else tuple(
            ParticipantAnalysis(
                None if row["account_id"] is None else AccountId(_integer(row["account_id"])),
                _optional_integer(row["player_slot"]),
                tuple(
                    MetricSeries(
                        _text(metric["name"]),
                        MetricSemantic(_text(metric["semantic"])),
                        tuple(_integer(item) for item in _list(metric["values"])),
                        _integer(metric["start_seconds"]),
                        _integer(metric["interval_seconds"]),
                    )
                    for metric_value in _list(row["metrics"])
                    for metric in (_object(metric_value),)
                ),
                None
                if row["purchases"] is None
                else tuple(
                    PurchaseEvent(
                        _integer(item["time_seconds"]),
                        None if item["item_id"] is None else _integer(item["item_id"]),
                        None if item["item_key"] is None else _text(item["item_key"]),
                        None if item["charges"] is None else _integer(item["charges"]),
                    )
                    for item_value in _list(row["purchases"])
                    for item in (_object(item_value),)
                ),
            )
            for row_value in participants
            for row in (_object(row_value),)
        )
    )
    return MatchAnalysis(match_id, metadata, parsed)
