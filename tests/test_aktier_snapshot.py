"""SPEC 033: prepared Aktier börs snapshots."""

from datetime import date, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import event

from src import db
from src.models.indices import Indice
from src.models.metrics import Metric
from src.models.ticker import Ticker
from src.routes import stocks
from src.services import aktier_snapshot

DATA_TABLES = ("metrics", "tickers", "indices")


def _seed_nyse(app, count=30):
    trading_day = date.today() - timedelta(days=7)
    with app.app_context():
        for index in range(1, count + 1):
            symbol = f"P{index:02d}"
            db.session.add(
                Ticker(
                    symbol=symbol,
                    company=f"Paged Co {index:02d}",
                    market="us_market",
                    exchange_name="NYSE",
                    sector="Technology" if index % 2 else "Energy",
                )
            )
            db.session.add(
                Metric(
                    ticker=symbol,
                    company=f"Paged Co {index:02d}",
                    trading_date=trading_day,
                    current_price=float(index),
                    currency="USD",
                    z_score=index / 10,
                )
            )
        for ticker, sector in (("US-IDX", "NYSE & Nasdaq"), ("US-IDX-TECHNOLOGY", "Technology")):
            db.session.add(
                Indice(
                    ticker=ticker,
                    sector=sector,
                    country="us",
                    trading_date=trading_day,
                    ticker_count=count,
                    current_price=100,
                    currency="USD",
                    pct_uptrend=Decimal("50"),
                    z_score=0,
                )
            )
        db.session.commit()
    return trading_day


class _StatementCounter:
    def __init__(self, engine):
        self.engine = engine
        self.statements = []

    def __enter__(self):
        event.listen(self.engine, "before_cursor_execute", self._record)
        return self

    def __exit__(self, *exc):
        event.remove(self.engine, "before_cursor_execute", self._record)

    def _record(self, conn, cursor, statement, *args):
        self.statements.append(statement)

    def data_statements(self):
        return [
            s for s in self.statements
            if any(table in s.lower() for table in DATA_TABLES)
        ]


def test_snapshot_rows_equal_page_row_builders(app):
    _seed_nyse(app)
    with app.app_context():
        snapshot = aktier_snapshot.build_snapshot("nyse")
        symbols, metric_model, ticker_model, _ = stocks._matching_symbols_with_metrics("nyse")
        expected_rows = stocks._build_page_rows(
            symbols, metric_model, ticker_model, country="us"
        )
        expected_sectors = stocks._load_sector_rows("us")

    assert snapshot["stock_rows"] == expected_rows
    assert [row["ticker"] for row in snapshot["stock_rows"]] == sorted(symbols)
    assert snapshot["sector_rows"] == expected_sectors
    assert snapshot["industry_options"] == stocks.industry_options(
        expected_rows, exclude_labels=stocks._market_index_labels(expected_sectors)
    )
    assert snapshot["sector_labels"] == ["Technology"]
    assert snapshot["exchange_key"] == "nyse"


def test_snapshot_holds_no_user_data(app):
    _seed_nyse(app, count=3)
    with app.app_context():
        snapshot = aktier_snapshot.build_snapshot("nyse")
    text = repr(snapshot).lower()
    assert "user" not in text
    assert "@" not in text


def test_second_get_reads_no_data_tables(app):
    _seed_nyse(app)
    app.config["AKTIER_VERSION_PROBE_SECONDS"] = 600
    try:
        with app.app_context():
            first = aktier_snapshot.get_snapshot("nyse")
            with _StatementCounter(db.engine) as counter:
                second = aktier_snapshot.get_snapshot("nyse")
        assert counter.data_statements() == []
        assert second == first
    finally:
        app.config["AKTIER_VERSION_PROBE_SECONDS"] = 0


def test_new_trading_date_builds_new_version(app):
    trading_day = _seed_nyse(app, count=3)
    with app.app_context():
        first = aktier_snapshot.get_snapshot("nyse")
        db.session.add(
            Metric(
                ticker="P01",
                company="Paged Co 01",
                trading_date=trading_day + timedelta(days=7),
                current_price=999.0,
                currency="USD",
                z_score=0,
            )
        )
        db.session.commit()
        second = aktier_snapshot.get_snapshot("nyse")
    assert second["version"] != first["version"]
    assert second["stock_rows"][0]["current_price"] == 999.0


def test_missing_snapshot_is_built_in_request(app):
    _seed_nyse(app, count=3)
    with app.app_context():
        aktier_snapshot.clear()
        snapshot = aktier_snapshot.get_snapshot("nyse")
    assert len(snapshot["stock_rows"]) == 3


def test_warm_all_builds_then_up_to_date(app):
    _seed_nyse(app, count=3)
    with app.app_context():
        first = aktier_snapshot.warm_all()
        second = aktier_snapshot.warm_all()
    assert set(first) == {"nasdaq", "nyse", "omx_stockholm", "ftse"}
    assert first["nyse"][:2] == ("built", 3)
    assert second["nyse"][:2] == ("up to date", 3)
    assert all(status == "up to date" for status, _rows, _s in second.values())


def test_cli_aktier_warm(app):
    _seed_nyse(app, count=3)
    result = app.test_cli_runner().invoke(args=["aktier-warm"])
    assert result.exit_code == 0
    assert "nyse: built 3 rows" in result.output
    assert "nasdaq: built 0 rows" in result.output


def test_cli_aktier_warm_reports_failure(app, monkeypatch):
    def boom(_exchange_key):
        raise RuntimeError("down")

    monkeypatch.setattr(aktier_snapshot, "warm", boom)
    result = app.test_cli_runner().invoke(args=["aktier-warm"])
    assert result.exit_code == 1
    assert "nyse: failed: RuntimeError" in result.output


@pytest.mark.parametrize("exchange_key", ["nasdaq", "nyse", "omx_stockholm", "ftse"])
def test_empty_bors_snapshot(app, exchange_key):
    with app.app_context():
        snapshot = aktier_snapshot.build_snapshot(exchange_key)
    assert snapshot["stock_rows"] == []
    assert snapshot["sector_rows"] == []
