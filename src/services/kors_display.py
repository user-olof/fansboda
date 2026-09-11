"""Aktier Kors display freshness rules over completed RFC-013 CrossEvents.

Product rules (not part of RFC-013 emission):
- Golden: show only when crossover_date == latest_trading_date
- Death: show when latest_trading_date - 8 weeks <= crossover_date <= latest
  (inclusive, via timedelta(weeks=8))
- If both qualify, the more recent crossover_date wins
- Equal-date Golden+Death (pathological): prefer Death deterministically
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Sequence

from src.services.cross_detection import CrossEvent, CrossPattern

DEATH_FRESHNESS_WEEKS = 8


@dataclass(frozen=True)
class KorsDisplay:
    """Cache-safe Kors cell payload for Aktier rows."""

    kors: str | None
    kors_date: date | None
    kors_title: str

    @property
    def kors_date_iso(self) -> str:
        return self.kors_date.isoformat() if self.kors_date is not None else ""


_EMPTY = KorsDisplay(kors=None, kors_date=None, kors_title="")


def _pattern_label(pattern: CrossPattern) -> str:
    if pattern is CrossPattern.GOLDEN:
        return "Golden"
    return "Death"


def _qualifies_golden(event: CrossEvent, latest_trading_date: date) -> bool:
    return (
        event.pattern is CrossPattern.GOLDEN
        and event.crossover_date == latest_trading_date
    )


def _qualifies_death(event: CrossEvent, latest_trading_date: date) -> bool:
    if event.pattern is not CrossPattern.DEATH:
        return False
    window_start = latest_trading_date - timedelta(weeks=DEATH_FRESHNESS_WEEKS)
    return window_start <= event.crossover_date <= latest_trading_date


def select_kors_display(
    events: Sequence[CrossEvent],
    latest_trading_date: date | None,
) -> KorsDisplay:
    """Pick at most one display signal from completed cross events."""
    if latest_trading_date is None:
        return _EMPTY

    candidates: list[CrossEvent] = []
    for event in events:
        if _qualifies_golden(event, latest_trading_date) or _qualifies_death(
            event, latest_trading_date
        ):
            candidates.append(event)

    if not candidates:
        return _EMPTY

    # More recent crossover wins. Equal dates: prefer Death (deterministic).
    def _rank(event: CrossEvent) -> tuple[date, int]:
        death_prefer = 1 if event.pattern is CrossPattern.DEATH else 0
        return (event.crossover_date, death_prefer)

    chosen = max(candidates, key=_rank)
    iso = chosen.crossover_date.isoformat()
    return KorsDisplay(
        kors=_pattern_label(chosen.pattern),
        kors_date=chosen.crossover_date,
        kors_title=iso,
    )
