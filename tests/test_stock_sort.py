"""Unit tests for Aktier full-dataset sort helpers (SPEC 014)."""

from src.routes.stocks import (
    parse_sort,
    next_sort_direction,
    aria_sort_value,
    sort_stock_rows,
)


def _row(ticker, company="Co", heat=None, kors=None):
    return {
        "ticker": ticker,
        "company": company,
        "heat_score": heat,
        "kors": kors,
    }


def test_parse_sort_valid_and_invalid():
    assert parse_sort("trend", "desc") == ("trend", "desc")
    assert parse_sort("BOLAG", "ASC") == ("bolag", "asc")
    assert parse_sort("signal", "asc") == ("signal", "asc")
    assert parse_sort("price", "asc") == (None, None)
    assert parse_sort("trend", "sideways") == (None, None)
    assert parse_sort(None, "asc") == (None, None)
    assert parse_sort("trend", None) == (None, None)


def test_next_sort_direction_defaults_and_toggle():
    assert next_sort_direction("trend", None, None) == "desc"
    assert next_sort_direction("bolag", None, None) == "asc"
    assert next_sort_direction("signal", None, None) == "asc"
    assert next_sort_direction("trend", "trend", "desc") == "asc"
    assert next_sort_direction("trend", "trend", "asc") == "desc"
    assert next_sort_direction("bolag", "trend", "desc") == "asc"


def test_aria_sort_value():
    assert aria_sort_value("trend", "trend", "desc") == "descending"
    assert aria_sort_value("bolag", "bolag", "asc") == "ascending"
    assert aria_sort_value("signal", "trend", "desc") == "none"


def test_sort_trend_desc_nulls_last_first_click_default():
    rows = [
        _row("A", heat=1.0),
        _row("B", heat=None),
        _row("C", heat=2.0),
        _row("D", heat=-1.0),
    ]
    ordered = sort_stock_rows(rows, "trend", "desc")
    assert [r["ticker"] for r in ordered] == ["C", "A", "D", "B"]


def test_sort_trend_asc_nulls_last():
    rows = [
        _row("A", heat=1.0),
        _row("B", heat=None),
        _row("C", heat=2.0),
        _row("Z", heat=None),
    ]
    ordered = sort_stock_rows(rows, "trend", "asc")
    assert [r["ticker"] for r in ordered] == ["A", "C", "B", "Z"]


def test_sort_bolag_case_insensitive_secondary_ticker():
    rows = [
        _row("B", company="beta"),
        _row("A", company="Alpha"),
        _row("C", company="alpha"),
        _row("D", company="Zed"),
    ]
    ordered = sort_stock_rows(rows, "bolag", "asc")
    assert [r["ticker"] for r in ordered] == ["A", "C", "B", "D"]
    ordered_desc = sort_stock_rows(rows, "bolag", "desc")
    assert [r["ticker"] for r in ordered_desc] == ["D", "B", "A", "C"]


def test_sort_signal_death_golden_empty_secondary_ticker():
    rows = [
        _row("G2", kors="Golden"),
        _row("E1", kors=None),
        _row("D1", kors="Death"),
        _row("G1", kors="Golden"),
        _row("E0", kors=""),
        _row("D0", kors="Death"),
    ]
    ordered = sort_stock_rows(rows, "signal", "asc")
    assert [r["ticker"] for r in ordered] == ["D0", "D1", "G1", "G2", "E0", "E1"]
    ordered_desc = sort_stock_rows(rows, "signal", "desc")
    assert [r["ticker"] for r in ordered_desc] == ["E0", "E1", "G1", "G2", "D0", "D1"]


def test_sort_none_preserves_input_order_copy():
    rows = [_row("B"), _row("A")]
    ordered = sort_stock_rows(rows, None, None)
    assert [r["ticker"] for r in ordered] == ["B", "A"]
    assert ordered is not rows
