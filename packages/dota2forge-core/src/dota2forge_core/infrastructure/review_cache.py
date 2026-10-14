"""Explicit in-memory review observations, separate from native chat history."""

from ..domain.analysis import MatchAnalysisResult
from ..domain.match_detail import MatchDetailResult, MatchId
from ..ports import MatchAnalysisProvider, MatchDetailProvider
from ._feature_cache import ObservationCache


class ReviewObservationProvider:
    def __init__(self, details: MatchDetailProvider, analysis: MatchAnalysisProvider) -> None:
        self.source = details.source
        self._details, self._analysis = details, analysis
        # A short conservative TTL also bounds partial/unparsed observations.
        self._detail_cache = ObservationCache[MatchDetailResult](ttl=300)
        self._analysis_cache = ObservationCache[MatchAnalysisResult](ttl=300)

    async def get_match_detail(self, match_id: MatchId) -> MatchDetailResult:
        return await self._detail_cache.get(
            str(match_id.value), lambda: self._details.get_match_detail(match_id)
        )

    async def get_match_analysis(self, match_id: MatchId) -> MatchAnalysisResult:
        return await self._analysis_cache.get(
            str(match_id.value), lambda: self._analysis.get_match_analysis(match_id)
        )

    async def close(self) -> None:
        await self._detail_cache.close()
        await self._analysis_cache.close()
