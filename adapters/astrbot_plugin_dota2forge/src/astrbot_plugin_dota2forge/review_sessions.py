"""Minimal trusted native-session anchors; never store chat text or model judgments."""

from collections import OrderedDict
from collections.abc import Callable, Hashable
from dataclasses import dataclass
from time import monotonic

from dota2forge_core import PlayerBinding, ReviewEvidence, ValidationError


@dataclass(repr=False)
class Anchor:
    match_id: int
    hero_name: str | None
    binding: PlayerBinding | None
    generation: object
    created: float
    active: float
    evidence: ReviewEvidence | None = None
    evidence_at: float = 0
    history_count: int = 0


class ReviewSessionStore:
    def __init__(self, clock: Callable[[], float] = monotonic) -> None:
        self._clock = clock
        self._values: OrderedDict[Hashable, Anchor] = OrderedDict()

    def _prune(self) -> None:
        now = self._clock()
        for key, entry in tuple(self._values.items()):
            if now - entry.active >= 1800 or now - entry.created >= 7200:
                del self._values[key]
            elif now - entry.evidence_at >= 600:
                entry.evidence = None

    def peek(
        self, key: Hashable, generation: object, history_count: int | None = None
    ) -> Anchor | None:
        if isinstance(key, tuple):
            for old in tuple(self._values):
                if isinstance(old, tuple) and old[:-1] == key[:-1] and old != key:
                    del self._values[old]
        entry = self._values.get(key)
        return (
            None
            if entry is None
            else self.get(key, generation, entry.binding, history_count=history_count)
        )

    def get(
        self,
        key: Hashable,
        generation: object,
        binding: PlayerBinding | None,
        *,
        history_count: int | None = None,
    ) -> Anchor | None:
        self._prune()
        entry = self._values.get(key)
        if entry is None:
            return None
        now = self._clock()
        if (
            entry.generation != generation
            or entry.binding != binding
            or now - entry.active >= 1800
            or now - entry.created >= 7200
            or (history_count == 0 and entry.history_count > 0)
        ):
            del self._values[key]
            return None
        if history_count is not None:
            entry.history_count = history_count
        return entry

    def remember(
        self,
        key: Hashable,
        generation: object,
        binding: PlayerBinding | None,
        match_id: int,
        hero_name: str | None,
        evidence: ReviewEvidence,
    ) -> Anchor:
        if not isinstance(evidence, ReviewEvidence) or evidence.detail.match_id.value != match_id:
            raise ValidationError("Invalid review anchor evidence")
        previous = self.get(key, generation, binding)
        now = self._clock()
        created = (
            previous.created
            if previous is not None
            and previous.match_id == match_id
            and previous.hero_name == hero_name
            else now
        )
        evidence_at = (
            previous.evidence_at if previous is not None and previous.evidence is evidence else now
        )
        entry = Anchor(
            match_id,
            hero_name,
            binding,
            generation,
            created,
            now,
            evidence,
            evidence_at,
            0 if previous is None else previous.history_count,
        )
        self._values[key] = entry
        self._values.move_to_end(key)
        while len(self._values) > 128:
            self._values.popitem(last=False)
        return entry

    def evidence(self, entry: Anchor) -> ReviewEvidence | None:
        return entry.evidence if self._clock() - entry.evidence_at < 600 else None

    def invalidate(self, identity: object) -> None:
        for key in tuple(self._values):
            if isinstance(key, tuple) and key and key[0] == identity:
                del self._values[key]

    def clear(self) -> None:
        self._values.clear()
