"""Unit tests for Aktier Kors freshness / display rules."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from src.services.cross_detection import CrossEvent, CrossPattern
from src.services.kors_display import select_kors_display


def _event(
    pattern: CrossPattern,
    crossover: date,
    *,
    ticker: str = "AAPL",
) -> CrossEvent:
    return CrossEvent(
        pattern=pattern,
        ticker=ticker,
        country="us",
        crossover_date=crossover,
        regime_start_date=crossover - timedelta(weeks=4),
        regime_weeks=4,
        convergence_first_gap=Decimal("8"),
        convergence_last_gap=Decimal("4"),
        sma_50=Decimal("105") if pattern is CrossPattern.GOLDEN else Decimal("95"),
        sma_200=Decimal("100"),
    )


def test_golden_on_latest_shows_golden() -> None:
    latest = date(2025, 3, 3)
    result = select_kors_display(
        [_event(CrossPattern.GOLDEN, latest)],
        latest,
    )
    assert result.kors == "Golden"
    assert result.kors_date == latest
    assert result.kors_title == "2025-03-03"


def test_golden_on_prior_week_is_empty() -> None:
    latest = date(2025, 3, 10)
    prior = date(2025, 3, 3)
    result = select_kors_display(
        [_event(CrossPattern.GOLDEN, prior)],
        latest,
    )
    assert result.kors is None
    assert result.kors_title == ""


def test_death_within_eight_weeks_shows_death() -> None:
    latest = date(2025, 3, 10)
    crossover = latest - timedelta(weeks=3)
    result = select_kors_display(
        [_event(CrossPattern.DEATH, crossover)],
        latest,
    )
    assert result.kors == "Death"
    assert result.kors_date == crossover
    assert result.kors_title == crossover.isoformat()


def test_death_older_than_eight_weeks_is_empty() -> None:
    latest = date(2025, 3, 10)
    crossover = latest - timedelta(weeks=8, days=1)
    result = select_kors_display(
        [_event(CrossPattern.DEATH, crossover)],
        latest,
    )
    assert result.kors is None
    assert result.kors_title == ""


def test_death_exactly_eight_weeks_inclusive_shows_death() -> None:
    latest = date(2025, 3, 10)
    crossover = latest - timedelta(weeks=8)
    result = select_kors_display(
        [_event(CrossPattern.DEATH, crossover)],
        latest,
    )
    assert result.kors == "Death"
    assert result.kors_date == crossover
    assert result.kors_title == crossover.isoformat()


def test_both_qualify_shows_more_recent_only() -> None:
    latest = date(2025, 3, 10)
    death = _event(CrossPattern.DEATH, latest - timedelta(weeks=2))
    golden = _event(CrossPattern.GOLDEN, latest)
    result = select_kors_display([death, golden], latest)
    assert result.kors == "Golden"
    assert result.kors_date == latest


def test_both_qualify_death_more_recent_wins() -> None:
    latest = date(2025, 3, 10)
    # Golden on latest would normally win, but Death also on latest is pathological;
    # when Death is more recent than an older golden that somehow still qualified —
    # use Death within window vs golden that does NOT qualify (prior week).
    # Here: Death on latest (qualifies) and Golden on prior (does not) → Death.
    death = _event(CrossPattern.DEATH, latest)
    stale_golden = _event(CrossPattern.GOLDEN, latest - timedelta(weeks=1))
    result = select_kors_display([stale_golden, death], latest)
    assert result.kors == "Death"
    assert result.kors_date == latest


def test_equal_date_golden_and_death_prefers_death() -> None:
    """Deterministic tie-break when both types share the same crossover_date."""
    latest = date(2025, 3, 10)
    golden = _event(CrossPattern.GOLDEN, latest)
    death = _event(CrossPattern.DEATH, latest)
    result = select_kors_display([golden, death], latest)
    assert result.kors == "Death"
    assert result.kors_title == latest.isoformat()


def test_incomplete_events_empty() -> None:
    latest = date(2025, 3, 10)
    result = select_kors_display([], latest)
    assert result.kors is None
    assert result.kors_date is None
    assert result.kors_title == ""


def test_none_latest_is_empty() -> None:
    result = select_kors_display(
        [_event(CrossPattern.GOLDEN, date(2025, 3, 10))],
        None,
    )
    assert result.kors is None
    assert result.kors_title == ""


def test_empty_kors_title_when_no_signal() -> None:
    latest = date(2025, 3, 10)
    result = select_kors_display(
        [_event(CrossPattern.GOLDEN, latest - timedelta(weeks=1))],
        latest,
    )
    assert result.kors_title == ""
