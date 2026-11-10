"""Prepared Aktier börs snapshots, shared by all gunicorn workers (spec 033).

A snapshot holds everything the Aktier page shows for one börs — index rows,
every stock row in symbol order (Signal included), and the Industri choices —
built with the same row functions the page used before. Requests sort, filter,
and slice it in memory instead of reading the whole börs from Neon per press.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

from cachelib.file import FileSystemCache
from flask import current_app, g
from sqlalchemy import func, select

from src import db
from src.models.indices import Indice

_caches: dict[str, FileSystemCache] = {}
_versions: dict[str, tuple[str, float]] = {}


def _cache() -> FileSystemCache:
    directory = current_app.config["AKTIER_SNAPSHOT_DIR"]
    cache = _caches.get(directory)
    if cache is None:
        cache = FileSystemCache(
            directory,
            threshold=50,
            default_timeout=current_app.config["AKTIER_SNAPSHOT_TTL"],
        )
        _caches[directory] = cache
    return cache


def clear() -> None:
    """Drop every snapshot and the version memo (tests, manual reset)."""
    _versions.clear()
    _cache().clear()


def _add_db_ms(started: float) -> None:
    g.aktier_db_ms = g.get("aktier_db_ms", 0.0) + (time.perf_counter() - started) * 1000


def db_ms() -> float:
    """Milliseconds this request / app context spent probing or building."""
    return g.get("aktier_db_ms", 0.0)


def current_version(market: str) -> str:
    """Latest metrics and index trading dates for a market (`us` / `se` / `uk`).

    One query; memoized per process for AKTIER_VERSION_PROBE_SECONDS.
    """
    from src.routes.stocks import _indices_country, _tables_for_country

    probe_seconds = current_app.config["AKTIER_VERSION_PROBE_SECONDS"]
    now = time.monotonic()
    memo = _versions.get(market)
    if memo is not None and probe_seconds > 0 and now - memo[1] < probe_seconds:
        return memo[0]

    metric_model, _ticker_model, _market_model = _tables_for_country(market)
    started = time.perf_counter()
    latest_metric, latest_index = db.session.execute(
        select(
            select(func.max(metric_model.trading_date)).scalar_subquery(),
            select(func.max(Indice.trading_date))
            .where(Indice.country == _indices_country(market))
            .scalar_subquery(),
        )
    ).one()
    _add_db_ms(started)
    version = f"{latest_metric}|{latest_index}"
    _versions[market] = (version, now)
    return version


def build_snapshot(exchange_key: str, version: str | None = None) -> dict:
    """Read the whole börs once and return its snapshot (see data-model.md)."""
    from src.routes import stocks

    market = stocks.EXCHANGE_COUNTRY[exchange_key]
    if version is None:
        version = current_version(market)
    symbols, metric_model, ticker_model, _market_model = (
        stocks._matching_symbols_with_metrics(exchange_key)
    )
    stock_rows = stocks._build_page_rows(
        symbols, metric_model, ticker_model, country=market
    )
    sector_rows = stocks._load_sector_rows(market)
    return {
        "exchange_key": exchange_key,
        "version": version,
        "built_at": datetime.now(timezone.utc).isoformat(),
        "sector_rows": sector_rows,
        "stock_rows": stock_rows,
        "industry_options": stocks.industry_options(
            stock_rows, exclude_labels=stocks._market_index_labels(sector_rows)
        ),
        "sector_labels": stocks._sector_index_labels(sector_rows),
    }


def _key(exchange_key: str, version: str) -> str:
    return f"aktier_snapshot:{exchange_key}:{version}"


def get_snapshot(exchange_key: str) -> dict:
    """Snapshot for the current data version; built in-request when missing."""
    from src.routes.stocks import EXCHANGE_COUNTRY

    version = current_version(EXCHANGE_COUNTRY[exchange_key])
    key = _key(exchange_key, version)
    snapshot = _cache().get(key)
    if snapshot is None:
        started = time.perf_counter()
        snapshot = build_snapshot(exchange_key, version)
        _add_db_ms(started)
        _cache().set(key, snapshot)
    return snapshot


def warm(exchange_key: str) -> tuple[str, int]:
    """Build the snapshot for the current version unless it exists."""
    from src.routes.stocks import EXCHANGE_COUNTRY

    version = current_version(EXCHANGE_COUNTRY[exchange_key])
    key = _key(exchange_key, version)
    existing = _cache().get(key)
    if existing is not None:
        return "up to date", len(existing["stock_rows"])
    snapshot = build_snapshot(exchange_key, version)
    _cache().set(key, snapshot)
    return "built", len(snapshot["stock_rows"])


def warm_all() -> dict[str, tuple[str, int, float]]:
    """Warm every börs; a failure is reported per börs, not raised."""
    from src.routes.stocks import EXCHANGE_COUNTRY

    results: dict[str, tuple[str, int, float]] = {}
    for exchange_key in EXCHANGE_COUNTRY:
        started = time.perf_counter()
        try:
            status, rows = warm(exchange_key)
        except Exception as exc:  # noqa: BLE001 — reported, CLI exits 1
            db.session.rollback()
            status, rows = f"failed: {exc.__class__.__name__}", 0
        results[exchange_key] = (status, rows, time.perf_counter() - started)
    return results
