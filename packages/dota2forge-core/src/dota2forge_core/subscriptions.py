"""Bounded, explicitly invoked subscription operations; no scheduler or message I/O."""

from dataclasses import replace
from datetime import date
from uuid import uuid4

from .domain.analysis import MatchAnalysisResult, MatchAnalysisUnavailable
from .domain.errors import DataSource, ProviderError, ProviderErrorCode, ValidationError
from .domain.identity import AccountId, PlatformIdentity, parse_account_id
from .domain.match_detail import (
    MatchDetail,
    MatchDetailResult,
    MatchDetailUnavailable,
    MatchId,
    parse_match_id,
)
from .domain.match_reports import MatchReport
from .domain.models import MatchSummary, PlayerProfile, RecentMatches
from .domain.subscription_reports import BEIJING, DailyCoverage, DailyReport, report_bounds
from .domain.subscriptions import (
    RankChange,
    Subscription,
    SubscriptionCheckpoint,
    SubscriptionEvent,
    SubscriptionKey,
    SubscriptionKind,
    SubscriptionPollResult,
    SubscriptionPollState,
    SubscriptionScope,
    require_subscription_id,
    require_subscription_limit,
)
from .ports import (
    Clock,
    MatchAnalysisProvider,
    MatchDetailProvider,
    MatchProvider,
    PlayerProvider,
    SubscriptionRepository,
)


class SubscriptionService:
    def __init__(
        self,
        repository: SubscriptionRepository,
        players: PlayerProvider,
        matches: MatchProvider,
        clock: Clock,
        details: MatchDetailProvider | None = None,
        analysis: MatchAnalysisProvider | None = None,
    ) -> None:
        if not isinstance(players.source, DataSource) or not isinstance(matches.source, DataSource):
            raise ValidationError("Subscription providers require known sources")
        self._repository = repository
        self._players = players
        self._matches = matches
        self._clock = clock
        self._details = details
        self._analysis = analysis

    async def subscribe(
        self,
        identity: PlatformIdentity,
        account_id: int | str,
        destination: str,
        *,
        kind: SubscriptionKind = SubscriptionKind.NEW_MATCH,
    ) -> Subscription:
        if not isinstance(kind, SubscriptionKind):
            raise ValidationError("Expected a subscription kind")
        source = (
            self._players.source if kind == SubscriptionKind.RANK_CHANGE else self._matches.source
        )
        key = SubscriptionKey(identity, destination, parse_account_id(account_id), source, kind)
        return await self._repository.save(Subscription(uuid4().hex, key, self._clock.now()))

    async def subscribe_match(
        self, identity: PlatformIdentity, match_id: int | str, destination: str
    ) -> Subscription:
        if self._details is None:
            raise ValidationError("Match subscriptions require a detail provider")
        target = parse_match_id(match_id)
        key = SubscriptionKey(
            identity,
            destination,
            None,
            self._details.source,
            SubscriptionKind.MATCH_REPORT,
            target,
        )
        return await self._repository.save(Subscription(uuid4().hex, key, self._clock.now()))

    async def list_subscriptions(
        self,
        identity: PlatformIdentity,
        *,
        limit: int = 20,
        after_id: str | None = None,
        destination: str | None = None,
    ) -> tuple[Subscription, ...]:
        return await self._repository.list(
            SubscriptionScope.for_identity(identity),
            owner=identity,
            limit=limit,
            after_id=after_id,
            destination=destination,
        )

    async def unsubscribe(self, identity: PlatformIdentity, subscription_id: str) -> bool:
        SubscriptionScope.for_identity(identity)
        require_subscription_id(subscription_id)
        return await self._repository.delete(identity, subscription_id)

    async def pending_events(
        self, identity: PlatformIdentity, *, limit: int = 20
    ) -> tuple[SubscriptionEvent, ...]:
        return await self._repository.pending(
            SubscriptionScope.for_identity(identity), owner=identity, limit=limit
        )

    async def acknowledge(self, identity: PlatformIdentity, event_id: str) -> bool:
        SubscriptionScope.for_identity(identity)
        require_subscription_id(event_id)
        return await self._repository.acknowledge(identity, event_id)

    async def unsubscribe_all(self, identity: PlatformIdentity) -> int:
        SubscriptionScope.for_identity(identity)
        return await self._repository.delete_all(identity)

    async def claim_event(
        self, identity: PlatformIdentity, event_id: str
    ) -> SubscriptionEvent | None:
        return await self._repository.claim(identity, event_id, self._clock.now())

    async def retry_event(self, identity: PlatformIdentity, event_id: str) -> bool:
        return await self._repository.release(identity, event_id)

    async def poll_daily_reports(
        self,
        scope: SubscriptionScope,
        report_date: date,
        *,
        limit: int = 20,
        after_id: str | None = None,
        match_limit: int = 100,
    ) -> tuple[SubscriptionPollResult, ...]:
        report_bounds(report_date)
        if report_date >= self._clock.now().astimezone(BEIJING).date():
            raise ValidationError("Daily observations require a completed Beijing calendar day")
        require_subscription_limit(match_limit)
        return await self._poll(
            scope, SubscriptionKind.DAILY_REPORT, limit, after_id, match_limit, report_date
        )

    async def poll_match_reports(
        self, scope: SubscriptionScope, *, limit: int = 20, after_id: str | None = None
    ) -> tuple[SubscriptionPollResult, ...]:
        if self._details is None:
            raise ValidationError("Match subscriptions require a detail provider")
        subscriptions = await self._repository.list(
            scope, kind=SubscriptionKind.MATCH_REPORT, limit=limit, after_id=after_id
        )
        results: list[SubscriptionPollResult] = []
        for subscription in subscriptions:
            if subscription.checkpoint.match_reported:
                results.append(
                    SubscriptionPollResult(subscription, SubscriptionPollState.UNCHANGED)
                )
                continue
            try:
                detail = await self._details.get_match_detail(subscription.key.match_id)  # type: ignore[arg-type]
            except ProviderError as error:
                results.append(
                    SubscriptionPollResult(
                        subscription, SubscriptionPollState.FAILED, failure=error
                    )
                )
                continue
            if not isinstance(detail, MatchDetail) or (
                detail.duration_seconds is None or detail.did_radiant_win is None
            ):
                results.append(
                    SubscriptionPollResult(subscription, SubscriptionPollState.UNCHANGED)
                )
                continue
            report = await self._make_report(None, detail, None)
            if isinstance(report, ProviderError):
                results.append(
                    SubscriptionPollResult(
                        subscription, SubscriptionPollState.FAILED, failure=report
                    )
                )
                continue
            checkpoint = replace(
                subscription.checkpoint,
                fetched_at=detail.metadata.fetched_at,
                match_reported=True,
            )
            event = SubscriptionEvent(
                uuid4().hex,
                subscription.subscription_id,
                subscription.key,
                self._clock.now(),
                report,
            )
            if not await self._repository.commit(subscription, checkpoint, (event,)):
                results.append(SubscriptionPollResult(subscription, SubscriptionPollState.STALE))
            else:
                results.append(
                    SubscriptionPollResult(
                        replace(
                            subscription, checkpoint=checkpoint, revision=subscription.revision + 1
                        ),
                        SubscriptionPollState.EVENTS,
                        (event,),
                    )
                )
        return tuple(results)

    async def poll_new_matches(
        self,
        scope: SubscriptionScope,
        *,
        limit: int = 20,
        after_id: str | None = None,
        match_limit: int = 20,
    ) -> tuple[SubscriptionPollResult, ...]:
        require_subscription_limit(match_limit)
        return await self._poll(scope, SubscriptionKind.NEW_MATCH, limit, after_id, match_limit)

    async def poll_rank_changes(
        self, scope: SubscriptionScope, *, limit: int = 20, after_id: str | None = None
    ) -> tuple[SubscriptionPollResult, ...]:
        return await self._poll(scope, SubscriptionKind.RANK_CHANGE, limit, after_id, 20)

    async def _poll(
        self,
        scope: SubscriptionScope,
        kind: SubscriptionKind,
        limit: int,
        after_id: str | None,
        match_limit: int,
        report_date: date | None = None,
    ) -> tuple[SubscriptionPollResult, ...]:
        subscriptions = await self._repository.list(
            scope, kind=kind, limit=limit, after_id=after_id
        )
        observations: dict[AccountId, RecentMatches | PlayerProfile | ProviderError] = {}
        results: list[SubscriptionPollResult] = []
        source = (
            self._players.source if kind == SubscriptionKind.RANK_CHANGE else self._matches.source
        )
        for subscription in subscriptions:
            key = subscription.key
            assert key.account_id is not None
            if report_date is not None:
                if subscription.checkpoint.report_date is not None and (
                    subscription.checkpoint.report_date >= report_date
                ):
                    results.append(
                        SubscriptionPollResult(subscription, SubscriptionPollState.UNCHANGED)
                    )
                    continue
                if report_date < subscription.created_at.astimezone(BEIJING).date():
                    daily_checkpoint = replace(
                        subscription.checkpoint,
                        report_date=report_date,
                        fetched_at=self._clock.now(),
                    )
                    saved = await self._repository.commit(subscription, daily_checkpoint, ())
                    results.append(
                        SubscriptionPollResult(
                            replace(
                                subscription,
                                checkpoint=daily_checkpoint,
                                revision=subscription.revision + 1,
                            )
                            if saved
                            else subscription,
                            SubscriptionPollState.BASELINED
                            if saved
                            else SubscriptionPollState.STALE,
                        )
                    )
                    continue
            if key.source != source:
                observation: RecentMatches | PlayerProfile | ProviderError = ProviderError(
                    ProviderErrorCode.INVALID_RESPONSE, key.source
                )
            else:
                if key.account_id not in observations:
                    observations[key.account_id] = await self._observe(key, match_limit)
                observation = observations[key.account_id]
            if isinstance(observation, ProviderError):
                results.append(
                    SubscriptionPollResult(
                        subscription, SubscriptionPollState.FAILED, failure=observation
                    )
                )
                if observation.code in {
                    ProviderErrorCode.RATE_LIMITED,
                    ProviderErrorCode.AUTHENTICATION,
                }:
                    break
                continue
            checkpoint = subscription.checkpoint
            if observation.metadata.fetched_at < (checkpoint.fetched_at or subscription.created_at):
                results.append(SubscriptionPollResult(subscription, SubscriptionPollState.STALE))
                continue
            payloads: list[MatchSummary | RankChange | DailyReport | MatchReport]
            if isinstance(observation, RecentMatches) and report_date is not None:
                start, end = report_bounds(report_date)
                if observation.metadata.fetched_at < end:
                    results.append(
                        SubscriptionPollResult(subscription, SubscriptionPollState.STALE)
                    )
                    continue
                daily_matches = tuple(
                    match for match in observation.matches if start <= match.started_at < end
                )
                coverage = DailyCoverage.BOUNDED
                if not observation.matches:
                    coverage = DailyCoverage.EMPTY
                elif observation.matches[-1].started_at < start:
                    coverage = DailyCoverage.WINDOW_SPANNED
                elif len(observation.matches) == match_limit:
                    coverage = DailyCoverage.TRUNCATED
                payloads = [
                    DailyReport(
                        key.account_id, report_date, observation.metadata, daily_matches, coverage
                    )
                ]
                new_checkpoint = replace(
                    checkpoint, fetched_at=observation.metadata.fetched_at, report_date=report_date
                )
                state, gap = SubscriptionPollState.EVENTS, coverage != DailyCoverage.WINDOW_SPANNED
            elif isinstance(observation, RecentMatches):
                new_checkpoint, state, payloads, gap = self._match_changes(
                    subscription, observation
                )
            else:
                new_checkpoint = replace(checkpoint, fetched_at=observation.metadata.fetched_at)
                payloads = []
                gap = False
                rank = observation.rank_tier
                if rank is None:
                    state = SubscriptionPollState.UNKNOWN
                else:
                    new_checkpoint = replace(new_checkpoint, rank_tier=rank)
                    if checkpoint.rank_tier is None:
                        state = SubscriptionPollState.BASELINED
                    elif rank == checkpoint.rank_tier:
                        state = SubscriptionPollState.UNCHANGED
                    else:
                        state = SubscriptionPollState.EVENTS
                        payloads.append(
                            RankChange(checkpoint.rank_tier, rank, observation.metadata)
                        )
            if state == SubscriptionPollState.STALE:
                results.append(SubscriptionPollResult(subscription, state, coverage_gap=gap))
                continue
            events_list: list[SubscriptionEvent] = []
            for payload in payloads:
                if isinstance(payload, MatchSummary) and self._details is not None:
                    report = await self._make_report(payload, None, key.account_id)
                    if isinstance(report, ProviderError):
                        results.append(
                            SubscriptionPollResult(
                                subscription, SubscriptionPollState.FAILED, failure=report
                            )
                        )
                        events_list = []
                        break
                    payload = report
                events_list.append(
                    SubscriptionEvent(
                        uuid4().hex, subscription.subscription_id, key, self._clock.now(), payload
                    )
                )
            if not events_list and payloads:
                continue
            events = tuple(events_list)
            if not await self._repository.commit(subscription, new_checkpoint, events):
                results.append(SubscriptionPollResult(subscription, SubscriptionPollState.STALE))
                continue
            current = replace(
                subscription, checkpoint=new_checkpoint, revision=subscription.revision + 1
            )
            results.append(SubscriptionPollResult(current, state, events, gap))
        return tuple(results)

    async def _make_report(
        self,
        summary: MatchSummary | None,
        detail: MatchDetailResult | None,
        tracked_account_id: AccountId | None,
    ) -> MatchReport | ProviderError:
        if detail is None:
            assert summary is not None and self._details is not None
            try:
                result = await self._details.get_match_detail(MatchId(summary.match_id))
            except ProviderError as error:
                return error
            detail = result
        assert detail is not None
        if isinstance(detail, MatchDetailUnavailable):
            analysis: MatchAnalysisResult = MatchAnalysisUnavailable(
                detail.match_id, detail.metadata
            )
        elif self._analysis is None:
            analysis = MatchAnalysisUnavailable(detail.match_id, detail.metadata)
        else:
            try:
                analysis = await self._analysis.get_match_analysis(detail.match_id)
            except ProviderError as error:
                return error
        return MatchReport(
            detail.match_id,
            detail.metadata,
            tracked_account_id,
            summary,
            detail,
            analysis,
        )

    async def _observe(
        self, key: SubscriptionKey, match_limit: int
    ) -> RecentMatches | PlayerProfile | ProviderError:
        result: RecentMatches | PlayerProfile
        try:
            if key.kind != SubscriptionKind.RANK_CHANGE:
                assert key.account_id is not None
                result = await self._matches.get_recent_matches(key.account_id, match_limit)
                if not isinstance(result, RecentMatches) or len(result.matches) > match_limit:
                    raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, key.source)
                for match in result.matches:
                    try:
                        MatchId(match.match_id)
                    except ValidationError:
                        raise ProviderError(
                            ProviderErrorCode.INVALID_RESPONSE, key.source
                        ) from None
            else:
                assert key.account_id is not None
                result = await self._players.get_player(key.account_id)
                if not isinstance(result, PlayerProfile):
                    raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, key.source)
            if result.account_id != key.account_id or result.metadata.source != key.source:
                raise ProviderError(ProviderErrorCode.INVALID_RESPONSE, key.source)
            return result
        except ProviderError as failure:
            if failure.source != key.source:
                return ProviderError(ProviderErrorCode.INVALID_RESPONSE, key.source)
            return failure

    @staticmethod
    def _match_changes(
        subscription: Subscription, recent: RecentMatches
    ) -> tuple[
        SubscriptionCheckpoint,
        SubscriptionPollState,
        list[MatchSummary | RankChange | DailyReport | MatchReport],
        bool,
    ]:
        previous = subscription.checkpoint
        checkpoint = replace(previous, fetched_at=recent.metadata.fetched_at)
        if not recent.matches:
            return checkpoint, SubscriptionPollState.EMPTY, [], False
        frontier = previous.match_started_at
        gap = frontier is not None and not any(
            match.match_id in previous.match_ids for match in recent.matches
        )
        newest = recent.matches[0].started_at
        if frontier is not None and newest < frontier:
            return previous, SubscriptionPollState.STALE, [], gap
        candidates = [
            match
            for match in recent.matches
            if frontier is None
            or match.started_at > frontier
            or (match.started_at == frontier and match.match_id not in previous.match_ids)
        ]
        if any(match.is_win is None for match in candidates):
            return checkpoint, SubscriptionPollState.UNKNOWN, [], gap
        ids = {match.match_id for match in recent.matches if match.started_at == newest}
        if newest == frontier:
            ids.update(previous.match_ids)
        checkpoint = replace(checkpoint, match_started_at=newest, match_ids=tuple(sorted(ids)))
        if frontier is None:
            return checkpoint, SubscriptionPollState.BASELINED, [], False
        ordered = sorted(candidates, key=lambda match: (match.started_at, match.match_id))
        payloads: list[MatchSummary | RankChange | DailyReport | MatchReport] = list(ordered)
        state = SubscriptionPollState.EVENTS if payloads else SubscriptionPollState.UNCHANGED
        return checkpoint, state, payloads, gap
