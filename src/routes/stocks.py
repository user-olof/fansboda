# src/routes/stocks.py
import math
from datetime import date, timedelta

from flask import Blueprint, jsonify, render_template, request, session, url_for
from flask_login import current_user

from src import cache, db
from src.access_control import role_required
from src.models.market_metrics import MarketMetric
from src.models.metrics import Metric
from src.models.swe_market_metrics import SweMarketMetric
from src.models.swe_metrics import SweMetric
from src.models.swe_ticker import SweTicker
from src.models.ticker import Ticker
from src.models.user import Role

stocks_bp = Blueprint("stocks", __name__)

EXCHANGE_QUERY = {
    "nasdaq": "NASDAQ",
    "nyse": "NYSE",
    "omx_stockholm": "OMX Stockholm",
}

EXCHANGE_COUNTRY = {
    "nasdaq": "us",
    "nyse": "us",
    "omx_stockholm": "se",
}

PAGE_SIZE = 25
AKTIER_CACHE_TIMEOUT = 3600


def _to_float(value):
    return float(value) if value is not None else None


# σ landmarks: negative z is blue, positive z is red (polarity flipped from 009).
_HEAT_STOPS = (
    (-2.0, (0x1D, 0x4E, 0xD8)),
    (-1.0, (0x3B, 0x82, 0xF6)),
    (-0.5, (0x93, 0xC5, 0xFD)),
    (0.0, (0xFE, 0xF9, 0xC3)),
    (0.5, (0xFB, 0x92, 0x3C)),
    (1.0, (0xDC, 0x26, 0x26)),
    (2.0, (0x99, 0x1B, 0x1B)),
)


def _standard_normal_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _rgb_to_hex(rgb):
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def heat_color_from_z(z):
    """Diverging colors around the market (z = 0). Positive z is red.

    Blend between σ stops using the standard normal CDF so more shades
    fall where probability mass is (near 0). Do not rescale from the page.
    """
    if z is None:
        return "#e5e7eb"
    z_value = _to_float(z)
    if z_value is None:
        return "#e5e7eb"
    z_value = max(-2.0, min(2.0, z_value))
    if z_value <= _HEAT_STOPS[0][0]:
        return _rgb_to_hex(_HEAT_STOPS[0][1])
    for index in range(1, len(_HEAT_STOPS)):
        z_lo, rgb_lo = _HEAT_STOPS[index - 1]
        z_hi, rgb_hi = _HEAT_STOPS[index]
        if z_value <= z_hi:
            phi_lo = _standard_normal_cdf(z_lo)
            phi_hi = _standard_normal_cdf(z_hi)
            span = phi_hi - phi_lo
            t = 0.0 if span == 0 else (_standard_normal_cdf(z_value) - phi_lo) / span
            t = max(0.0, min(1.0, t))
            rgb = tuple(
                int(round(low + t * (high - low))) for low, high in zip(rgb_lo, rgb_hi)
            )
            return _rgb_to_hex(rgb)
    return _rgb_to_hex(_HEAT_STOPS[-1][1])


def _heat_label(z):
    if z is None:
        return "—"
    return f"{z:.2f}"


def _heat_title(z):
    if z is None:
        return "Heat: unavailable (no z-score vs market)"
    return f"Heat vs market average (0): z={z:.2f}"


def _stock_row(metric, sector=None):
    z = _to_float(metric.z_score)
    return {
        "company": metric.company,
        "ticker": metric.ticker,
        "currency": metric.currency,
        "current_price": metric.current_price,
        "industry": sector,
        "heat_score": z,
        "heat_label": _heat_label(z),
        "heat_color": heat_color_from_z(z),
        "heat_hot": z is not None and round(z, 2) > 1,
        "heat_title": _heat_title(z),
    }


def parse_exchange(value):
    """Return a known exchange query key, or None."""
    if value is None:
        return None
    key = str(value).strip().lower()
    return key if key in EXCHANGE_QUERY else None


def exchange_name_matches(stored, exchange_key):
    """Match stored `exchange_name` to a button. Accepts Yahoo-style names (NasdaqGS)."""
    if stored is None or exchange_key not in EXCHANGE_QUERY:
        return False
    text = str(stored).strip().casefold()
    if not text:
        return False
    expected = EXCHANGE_QUERY[exchange_key].casefold()
    if text == expected:
        return True
    if exchange_key == "nasdaq":
        return text.startswith("nasdaq")
    if exchange_key == "nyse":
        return text.startswith("nyse")
    if exchange_key == "omx_stockholm":
        return text in {"sto", "xsto"} or "stockholm" in text
    return False


def _tables_for_country(country):
    if country == "se":
        return SweMetric, SweTicker, SweMarketMetric
    return Metric, Ticker, MarketMetric


def _get_latest_metrics(metric_model):
    """Return the latest row per ticker (by trading_date), newest first."""
    latest_dates = (
        db.session.query(
            metric_model.ticker,
            db.func.max(metric_model.trading_date).label("latest_date"),
        )
        .group_by(metric_model.ticker)
        .subquery()
    )

    return (
        db.session.query(metric_model)
        .join(
            latest_dates,
            db.and_(
                metric_model.ticker == latest_dates.c.ticker,
                metric_model.trading_date == latest_dates.c.latest_date,
            ),
        )
        .order_by(metric_model.trading_date.desc())
        .all()
    )


def _get_latest_metrics_for_symbols(metric_model, symbols):
    """Latest metric row for each of `symbols`, in that order. Does not scan the whole table."""
    if not symbols:
        return []
    latest_dates = (
        db.session.query(
            metric_model.ticker,
            db.func.max(metric_model.trading_date).label("latest_date"),
        )
        .filter(metric_model.ticker.in_(symbols))
        .group_by(metric_model.ticker)
        .subquery()
    )
    rows = (
        db.session.query(metric_model)
        .join(
            latest_dates,
            db.and_(
                metric_model.ticker == latest_dates.c.ticker,
                metric_model.trading_date == latest_dates.c.latest_date,
            ),
        )
        .all()
    )
    by_ticker = {metric.ticker: metric for metric in rows}
    return [by_ticker[symbol] for symbol in symbols if symbol in by_ticker]


def _metric_history(metric_model, ticker, cutoff):
    return (
        db.session.query(metric_model)
        .filter(
            metric_model.ticker == ticker,
            metric_model.trading_date >= cutoff,
        )
        .order_by(metric_model.trading_date.asc())
        .all()
    )


def _latest_observation(ticker):
    latest = (
        db.session.query(Metric)
        .filter(Metric.ticker == ticker)
        .order_by(Metric.trading_date.desc())
        .first()
    )
    if latest is not None:
        return latest
    return (
        db.session.query(SweMetric)
        .filter(SweMetric.ticker == ticker)
        .order_by(SweMetric.trading_date.desc())
        .first()
    )


def get_last_weeks_metrics(ticker, weeks=52):
    """Return daily metrics for a ticker over the last `weeks` weeks from Neon."""
    cutoff = date.today() - timedelta(weeks=weeks)
    rows = _metric_history(Metric, ticker, cutoff)
    if not rows:
        rows = _metric_history(SweMetric, ticker, cutoff)

    return [
        {
            "trading_date": row.trading_date,
            "ticker": row.ticker,
            "sma_50": float(row.sma_50) if row.sma_50 is not None else None,
            "sma_200": float(row.sma_200) if row.sma_200 is not None else None,
            "current_price": (
                float(row.current_price) if row.current_price is not None else None
            ),
        }
        for row in rows
    ]


def _display_sector(sector):
    if sector is None:
        return None
    text = str(sector)
    for dash in ("-", "\u2010", "\u2011", "\u2012", "\u2013", "\u2014", "\u2212"):
        text = text.replace(dash, " ")
    text = " ".join(text.split())
    return text or None


def _ticker_map(ticker_model, symbols):
    if not symbols:
        return {}
    rows = ticker_model.query.filter(ticker_model.symbol.in_(symbols)).all()
    return {row.symbol: row for row in rows}


def _ticker_sectors(ticker_model, symbols):
    """Map ticker symbols to sector display text in one query."""
    return {
        symbol: _display_sector(ticker.sector)
        for symbol, ticker in _ticker_map(ticker_model, symbols).items()
    }


def _aktier_cache_key(user_id, exchange_key):
    return f"aktier_table:{user_id}:{exchange_key}"


def clear_aktier_table_cache(user_id):
    """Drop kept Aktier table pages for this user (all venues)."""
    if user_id is None:
        return
    for exchange_key in EXCHANGE_QUERY:
        cache.delete(_aktier_cache_key(user_id, exchange_key))


def _page_count(total):
    if total <= 0:
        return 1
    return (total + PAGE_SIZE - 1) // PAGE_SIZE


def parse_page(value, total):
    """1-based page, clamped to the last page for `total` matching names."""
    last = _page_count(total)
    try:
        page = int(value)
    except (TypeError, ValueError):
        page = 1
    if page < 1:
        page = 1
    if page > last:
        page = last
    return page


def _serialize_row(row):
    out = dict(row)
    if out.get("current_price") is not None:
        out["current_price"] = float(out["current_price"])
    if out.get("heat_score") is not None:
        out["heat_score"] = float(out["heat_score"])
    return out


def _cached_page(blob, page):
    if not isinstance(blob, dict):
        return None
    pages = blob.get("pages") or {}
    if page in pages:
        return pages[page]
    return pages.get(str(page))


def _empty_cache_blob(total):
    return {"total": total, "pages": {}}


def _matching_symbols_with_metrics(exchange_key):
    """Symbols on this venue that have a metric, sorted by symbol. No full latest-metric scan."""
    metric_model, ticker_model, market_model = _tables_for_country(
        EXCHANGE_COUNTRY[exchange_key]
    )
    tickers = ticker_model.query.all()
    matched = sorted(
        ticker.symbol
        for ticker in tickers
        if exchange_name_matches(ticker.exchange_name, exchange_key)
    )
    if not matched:
        return [], metric_model, ticker_model, market_model
    present = {
        row[0]
        for row in db.session.query(metric_model.ticker)
        .filter(metric_model.ticker.in_(matched))
        .distinct()
        .all()
    }
    symbols = [symbol for symbol in matched if symbol in present]
    return symbols, metric_model, ticker_model, market_model


def _build_page_rows(symbols_slice, metric_model, ticker_model):
    metrics = _get_latest_metrics_for_symbols(metric_model, symbols_slice)
    sectors = _ticker_sectors(ticker_model, [metric.ticker for metric in metrics])
    return [
        _serialize_row(_stock_row(metric, sector=sectors.get(metric.ticker)))
        for metric in metrics
    ]


def _store_page(user_id, exchange_key, total, page, rows, blob=None):
    if user_id is None:
        return
    key = _aktier_cache_key(user_id, exchange_key)
    if not isinstance(blob, dict) or blob.get("total") != total:
        blob = _empty_cache_blob(total)
    blob.setdefault("pages", {})[page] = rows
    blob["total"] = total
    cache.set(key, blob, timeout=AKTIER_CACHE_TIMEOUT)


def _load_table_page(user_id, exchange_key, requested_page):
    """Prefer cached page; otherwise load only this 25-row slice and Trend scores."""
    key = _aktier_cache_key(user_id, exchange_key) if user_id is not None else None
    blob = cache.get(key) if key else None

    if isinstance(blob, dict) and isinstance(blob.get("total"), int):
        total = blob["total"]
        page = parse_page(requested_page, total)
        cached_rows = _cached_page(blob, page)
        if cached_rows is not None:
            return cached_rows, total, page

    symbols, metric_model, ticker_model, _market_model = _matching_symbols_with_metrics(
        exchange_key
    )
    total = len(symbols)
    page = parse_page(requested_page, total)
    start = (page - 1) * PAGE_SIZE
    rows = _build_page_rows(
        symbols[start : start + PAGE_SIZE],
        metric_model,
        ticker_model,
    )
    _store_page(user_id, exchange_key, total, page, rows, blob)
    return rows, total, page


def _warm_exchange_pages(user_id, exchange_key):
    symbols, metric_model, ticker_model, _market_model = _matching_symbols_with_metrics(
        exchange_key
    )
    total = len(symbols)
    last = _page_count(total)
    key = _aktier_cache_key(user_id, exchange_key)
    blob = cache.get(key)
    if not isinstance(blob, dict) or blob.get("total") != total:
        blob = _empty_cache_blob(total)
    blob.setdefault("pages", {})
    for page in range(1, last + 1):
        if _cached_page(blob, page) is not None:
            continue
        start = (page - 1) * PAGE_SIZE
        blob["pages"][page] = _build_page_rows(
            symbols[start : start + PAGE_SIZE],
            metric_model,
            ticker_model,
        )
    blob["total"] = total
    cache.set(key, blob, timeout=AKTIER_CACHE_TIMEOUT)
    return last, total


def _aktier_return_url():
    exchange = parse_exchange(session.get("aktier_exchange"))
    if not exchange:
        return url_for("stocks.stocks")
    page = session.get("aktier_page") or 1
    try:
        page = int(page)
    except (TypeError, ValueError):
        page = 1
    if page < 1:
        page = 1
    return url_for("stocks.stocks", exchange=exchange, page=page)


def _remember_aktier_view(exchange_key, page):
    session["aktier_exchange"] = exchange_key
    session["aktier_page"] = page


@stocks_bp.route("/stocks")
@role_required(Role.USER, Role.ADMIN)
def stocks():
    selected_exchange = parse_exchange(request.args.get("exchange"))
    stock_rows = []
    stock_total = 0
    stock_page = 1
    if selected_exchange:
        stock_rows, stock_total, stock_page = _load_table_page(
            current_user.id,
            selected_exchange,
            request.args.get("page"),
        )
        _remember_aktier_view(selected_exchange, stock_page)
    last_page = _page_count(stock_total)
    range_start = ((stock_page - 1) * PAGE_SIZE) + 1 if stock_total else 0
    range_end = min(stock_page * PAGE_SIZE, stock_total)
    return render_template(
        "stocks.html",
        title="Aktier",
        stocks=stock_rows,
        selected_exchange=selected_exchange,
        stock_total=stock_total,
        stock_page=stock_page,
        stock_page_size=PAGE_SIZE,
        stock_last_page=last_page,
        stock_range_start=range_start,
        stock_range_end=range_end,
    )


@stocks_bp.route("/stocks/warm")
@role_required(Role.USER, Role.ADMIN)
def warm_stocks():
    selected_exchange = parse_exchange(request.args.get("exchange"))
    if not selected_exchange:
        return jsonify({"ok": False}), 400
    pages_cached, total = _warm_exchange_pages(current_user.id, selected_exchange)
    return jsonify({"ok": True, "pages_cached": pages_cached, "total": total})


@stocks_bp.route("/stocks/chart/<ticker>")
@role_required(Role.USER, Role.ADMIN)
def chart(ticker):
    history = get_last_weeks_metrics(ticker)
    latest = _latest_observation(ticker)
    company_name = latest.company if latest else ticker
    return render_template(
        "chart.html",
        title=company_name,
        ticker=ticker,
        company_name=company_name,
        history=history,
        stocks_return_url=_aktier_return_url(),
    )


@stocks_bp.route("/stocks/latest", methods=["GET"])
@role_required(Role.USER, Role.ADMIN)
def latest_stock_prices():
    """Return the latest price per ticker from US and Swedish metrics."""
    metrics = _get_latest_metrics(Metric) + _get_latest_metrics(SweMetric)
    return jsonify(
        [
            {
                "company": m.company,
                "ticker": m.ticker,
                "current_price": (
                    float(m.current_price) if m.current_price is not None else None
                ),
            }
            for m in metrics
        ]
    )
