# src/routes/stocks.py
import math
from datetime import date, timedelta
from decimal import Decimal

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
from src.services.cross_detection import SmaSnapshot, detect_all_patterns
from src.services.kors_display import select_kors_display

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
SMA_HISTORY_WEEKS = 52

# Sortable Aktier columns (URL `sort=`). Invalid sort/dir → default symbol order.
SORT_COLUMNS = frozenset({"trend", "bolag", "signal"})
DEFAULT_SORT_DIR = {
    "trend": "desc",
    "bolag": "asc",
    "signal": "asc",
}
SIGNAL_SORT_RANK = {
    "Golden": 0,
    "Death": 1,
}


def _to_float(value):
    return float(value) if value is not None else None


def parse_sort(sort_value, dir_value):
    """Return ``(sort, dir)`` or ``(None, None)`` for default symbol order."""
    sort_key = str(sort_value).strip().lower() if sort_value is not None else ""
    direction = str(dir_value).strip().lower() if dir_value is not None else ""
    if sort_key not in SORT_COLUMNS:
        return None, None
    if direction not in ("asc", "desc"):
        return None, None
    return sort_key, direction


def next_sort_direction(column, current_sort, current_dir):
    """Dir to apply when the user activates ``column`` (toggle if already active)."""
    if column not in SORT_COLUMNS:
        return DEFAULT_SORT_DIR.get(column, "asc")
    if current_sort == column and current_dir in ("asc", "desc"):
        return "asc" if current_dir == "desc" else "desc"
    return DEFAULT_SORT_DIR[column]


def aria_sort_value(column, current_sort, current_dir):
    if current_sort != column or current_dir not in ("asc", "desc"):
        return "none"
    return "ascending" if current_dir == "asc" else "descending"


def sort_stock_rows(rows, sort_key, direction):
    """Sort a full exchange row list. Secondary key is always ticker ascending.

    Trend null heat scores sort last. Signal order (asc): Golden < Death < empty.
    """
    ordered = list(rows)
    if not sort_key or sort_key not in SORT_COLUMNS:
        return ordered
    reverse = direction == "desc"

    def ticker_key(row):
        return (row.get("ticker") or "").casefold()

    # Stable secondary: ticker ascending first, then primary (preserves ticker on ties).
    ordered.sort(key=ticker_key)

    if sort_key == "trend":
        valued = [row for row in ordered if row.get("heat_score") is not None]
        missing = [row for row in ordered if row.get("heat_score") is None]
        valued.sort(key=lambda row: float(row["heat_score"]), reverse=reverse)
        return valued + missing

    if sort_key == "bolag":
        ordered.sort(
            key=lambda row: (row.get("company") or "").casefold(),
            reverse=reverse,
        )
        return ordered

    # signal
    ordered.sort(
        key=lambda row: SIGNAL_SORT_RANK.get(row.get("kors"), 2),
        reverse=reverse,
    )
    return ordered


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


def _stock_row(metric, sector=None, kors=None, kors_title=""):
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
        "kors": kors,
        "kors_title": kors_title or "",
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
    # v2: full-row blobs for global sort (partial page caches must not be sorted).
    return f"aktier_table_v2:{user_id}:{exchange_key}"


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
    # Cache-safe kors fields (never leave raw date objects in the blob).
    kors = out.get("kors")
    if kors not in ("Golden", "Death"):
        out["kors"] = None
    title = out.get("kors_title")
    if title is None:
        out["kors_title"] = ""
    else:
        out["kors_title"] = str(title)
    return out


def _slice_page(rows, page):
    start = (page - 1) * PAGE_SIZE
    return rows[start : start + PAGE_SIZE]


def _to_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _batch_sma_history(metric_model, symbols, weeks=SMA_HISTORY_WEEKS):
    """Load ordered SMA history for a page symbol slice (no per-ticker N+1).

    Returns ``dict[ticker, list[SmaSnapshot]]`` ordered by trading_date ascending.
    """
    if not symbols:
        return {}
    cutoff = date.today() - timedelta(weeks=weeks)
    rows = (
        db.session.query(
            metric_model.ticker,
            metric_model.trading_date,
            metric_model.sma_50,
            metric_model.sma_200,
        )
        .filter(
            metric_model.ticker.in_(symbols),
            metric_model.trading_date >= cutoff,
        )
        .order_by(metric_model.ticker.asc(), metric_model.trading_date.asc())
        .all()
    )
    history: dict[str, list[SmaSnapshot]] = {symbol: [] for symbol in symbols}
    for ticker, trading_date, sma_50, sma_200 in rows:
        history.setdefault(ticker, []).append(
            SmaSnapshot(
                trading_date=trading_date,
                sma_50=_to_decimal(sma_50),
                sma_200=_to_decimal(sma_200),
            )
        )
    return history


def _kors_for_metric(metric, snapshots, country=""):
    """Detect crosses and apply freshness; never fail the page on bad history."""
    try:
        events = detect_all_patterns(
            snapshots or [],
            ticker=metric.ticker,
            country=country,
        )
        display = select_kors_display(events, metric.trading_date)
        return display.kors, display.kors_title
    except Exception:
        return None, ""


def _cached_page(blob, page):
    if not isinstance(blob, dict):
        return None
    pages = blob.get("pages") or {}
    if page in pages:
        return pages[page]
    return pages.get(str(page))


def _empty_cache_blob(total):
    return {"total": total, "pages": {}, "rows": None, "complete": False}


def _blob_complete_rows(blob, total):
    """Return full symbol-order rows only when the cache holds the entire set."""
    if not isinstance(blob, dict) or blob.get("total") != total:
        return None
    rows = blob.get("rows")
    if blob.get("complete") and isinstance(rows, list) and len(rows) == total:
        return rows
    last = _page_count(total)
    if total == 0:
        return []
    assembled = []
    for page in range(1, last + 1):
        page_rows = _cached_page(blob, page)
        if page_rows is None:
            return None
        assembled.extend(page_rows)
    if len(assembled) != total:
        return None
    return assembled


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


def _build_page_rows(symbols_slice, metric_model, ticker_model, country=""):
    metrics = _get_latest_metrics_for_symbols(metric_model, symbols_slice)
    sectors = _ticker_sectors(ticker_model, [metric.ticker for metric in metrics])
    history = _batch_sma_history(metric_model, [metric.ticker for metric in metrics])
    rows = []
    for metric in metrics:
        kors, kors_title = _kors_for_metric(
            metric,
            history.get(metric.ticker, []),
            country=country,
        )
        rows.append(
            _serialize_row(
                _stock_row(
                    metric,
                    sector=sectors.get(metric.ticker),
                    kors=kors,
                    kors_title=kors_title,
                )
            )
        )
    return rows


def _store_cache_blob(user_id, exchange_key, blob):
    if user_id is None:
        return
    cache.set(
        _aktier_cache_key(user_id, exchange_key),
        blob,
        timeout=AKTIER_CACHE_TIMEOUT,
    )


def _store_page(user_id, exchange_key, total, page, rows, blob=None):
    if user_id is None:
        return
    if not isinstance(blob, dict) or blob.get("total") != total:
        blob = _empty_cache_blob(total)
    blob.setdefault("pages", {})[page] = rows
    blob["total"] = total
    # A single page write never claims completeness for sorting.
    if blob.get("complete") and isinstance(blob.get("rows"), list):
        start = (page - 1) * PAGE_SIZE
        full = list(blob["rows"])
        full[start : start + len(rows)] = rows
        blob["rows"] = full
    else:
        blob["complete"] = False
        complete_rows = _blob_complete_rows(blob, total)
        if complete_rows is not None:
            blob["rows"] = complete_rows
            blob["complete"] = True
    _store_cache_blob(user_id, exchange_key, blob)


def _store_full_rows(user_id, exchange_key, rows, total, blob=None):
    if user_id is None:
        return
    if not isinstance(blob, dict) or blob.get("total") != total:
        blob = _empty_cache_blob(total)
    blob["total"] = total
    blob["rows"] = rows
    blob["complete"] = True
    blob.setdefault("pages", {})
    last = _page_count(total)
    for page in range(1, last + 1):
        blob["pages"][page] = _slice_page(rows, page)
    _store_cache_blob(user_id, exchange_key, blob)


def _ensure_full_rows(user_id, exchange_key):
    """Full exchange rows in default symbol order. Never returns a partial set."""
    key = _aktier_cache_key(user_id, exchange_key) if user_id is not None else None
    blob = cache.get(key) if key else None
    symbols, metric_model, ticker_model, _market_model = _matching_symbols_with_metrics(
        exchange_key
    )
    total = len(symbols)
    cached = _blob_complete_rows(blob, total)
    if cached is not None:
        if isinstance(blob, dict) and not blob.get("complete"):
            _store_full_rows(user_id, exchange_key, cached, total, blob)
        return cached, total

    country = EXCHANGE_COUNTRY[exchange_key]
    rows = _build_page_rows(symbols, metric_model, ticker_model, country=country)
    _store_full_rows(user_id, exchange_key, rows, total, blob)
    return rows, total


def _load_table_page(
    user_id, exchange_key, requested_page, sort_key=None, direction=None
):
    """Load one page. With sort: full dataset → sort → paginate. Without: may lazy-slice."""
    if sort_key:
        all_rows, total = _ensure_full_rows(user_id, exchange_key)
        ordered = sort_stock_rows(all_rows, sort_key, direction)
        page = parse_page(requested_page, total)
        return _slice_page(ordered, page), total, page

    key = _aktier_cache_key(user_id, exchange_key) if user_id is not None else None
    blob = cache.get(key) if key else None

    if isinstance(blob, dict) and isinstance(blob.get("total"), int):
        total = blob["total"]
        page = parse_page(requested_page, total)
        complete_rows = _blob_complete_rows(blob, total)
        if complete_rows is not None:
            return _slice_page(complete_rows, page), total, page
        cached_rows = _cached_page(blob, page)
        if cached_rows is not None:
            return cached_rows, total, page

    symbols, metric_model, ticker_model, _market_model = _matching_symbols_with_metrics(
        exchange_key
    )
    country = EXCHANGE_COUNTRY[exchange_key]
    total = len(symbols)
    page = parse_page(requested_page, total)
    start = (page - 1) * PAGE_SIZE
    rows = _build_page_rows(
        symbols[start : start + PAGE_SIZE],
        metric_model,
        ticker_model,
        country=country,
    )
    _store_page(user_id, exchange_key, total, page, rows, blob)
    return rows, total, page


def _warm_exchange_pages(user_id, exchange_key):
    symbols, metric_model, ticker_model, _market_model = _matching_symbols_with_metrics(
        exchange_key
    )
    country = EXCHANGE_COUNTRY[exchange_key]
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
            country=country,
        )
    blob["total"] = total
    full_rows = _blob_complete_rows(blob, total) or []
    blob["rows"] = full_rows
    blob["complete"] = True
    cache.set(key, blob, timeout=AKTIER_CACHE_TIMEOUT)
    return last, total


def _aktier_query_args(exchange, page, sort_key=None, direction=None):
    args = {"exchange": exchange, "page": page}
    if sort_key and direction:
        args["sort"] = sort_key
        args["dir"] = direction
    return args


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
    sort_key, direction = parse_sort(
        session.get("aktier_sort"),
        session.get("aktier_dir"),
    )
    return url_for(
        "stocks.stocks",
        **_aktier_query_args(exchange, page, sort_key, direction),
    )


def _remember_aktier_view(exchange_key, page, sort_key=None, direction=None):
    session["aktier_exchange"] = exchange_key
    session["aktier_page"] = page
    if sort_key and direction:
        session["aktier_sort"] = sort_key
        session["aktier_dir"] = direction
    else:
        session.pop("aktier_sort", None)
        session.pop("aktier_dir", None)


@stocks_bp.route("/stocks")
@role_required(Role.USER, Role.ADMIN)
def stocks():
    selected_exchange = parse_exchange(request.args.get("exchange"))
    sort_key, direction = parse_sort(
        request.args.get("sort"),
        request.args.get("dir"),
    )
    stock_rows = []
    stock_total = 0
    stock_page = 1
    if selected_exchange:
        stock_rows, stock_total, stock_page = _load_table_page(
            current_user.id,
            selected_exchange,
            request.args.get("page"),
            sort_key=sort_key,
            direction=direction,
        )
        _remember_aktier_view(
            selected_exchange, stock_page, sort_key=sort_key, direction=direction
        )
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
        stock_sort=sort_key,
        stock_dir=direction,
        sort_next_dir={
            column: next_sort_direction(column, sort_key, direction)
            for column in SORT_COLUMNS
        },
        sort_aria={
            column: aria_sort_value(column, sort_key, direction)
            for column in SORT_COLUMNS
        },
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
