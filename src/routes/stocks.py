# src/routes/stocks.py
from datetime import date, timedelta

from flask import Blueprint, jsonify, render_template, request
from src import db
from src.access_control import role_required
from src.models.market_metrics import MarketMetric
from src.models.metrics import Metric
from src.models.swe_market_metrics import SweMarketMetric
from src.models.swe_metrics import SweMetric
from src.models.swe_ticker import SweTicker
from src.models.ticker import Ticker
from src.models.user import Role

stocks_bp = Blueprint("stocks", __name__)

# Neon `metrics` has no `market` column. Prefer ticker `market`, else currency.
CURRENCY_TO_MARKET = {
    "USD": "us_market",
    "SEK": "se_market",
}

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


def _to_float(value):
    return float(value) if value is not None else None


def z_score(raw, mean, std):
    """Standard score vs the market cross-section. Market mean maps to 0."""
    raw_value = _to_float(raw)
    mean_value = _to_float(mean)
    std_value = _to_float(std)
    if None in (raw_value, mean_value, std_value) or std_value == 0:
        return None
    return (raw_value - mean_value) / std_value


def combined_z(z_50, z_200):
    """Average of available z-scores. Market average stays 0."""
    values = [value for value in (z_50, z_200) if value is not None]
    if not values:
        return None
    return sum(values) / len(values)


def heat_color_from_z(z):
    """Diverging colors around the market (z = 0). Negative z is hotter."""
    if z is None:
        return "#e5e7eb"
    z = round(z, 2)
    if z <= -2:
        return "#991b1b"
    if z < -1:
        return "#dc2626"
    if z < -0.5:
        return "#fb923c"
    if z <= 0.5:
        return "#fef9c3"
    if z < 1:
        return "#93c5fd"
    if z < 2:
        return "#3b82f6"
    return "#1d4ed8"


def _heat_label(z):
    if z is None:
        return "—"
    return f"{z:.2f}"


def _heat_title(z_50, z_200, z):
    if z is None:
        return "Heat: unavailable (no z-score vs market)"
    parts = []
    if z_50 is not None:
        parts.append(f"z50={z_50:.2f}")
    if z_200 is not None:
        parts.append(f"z200={z_200:.2f}")
    return "Heat vs market average (0): " + ", ".join(parts)


def _stock_row(metric, z_50, z_200, sector=None):
    z = combined_z(z_50, z_200)
    return {
        "company": metric.company,
        "ticker": metric.ticker,
        "currency": metric.currency,
        "current_price": metric.current_price,
        "industry": sector,
        "heat_score": z,
        "heat_label": _heat_label(z),
        "heat_color": heat_color_from_z(z),
        "heat_hot": z is not None and round(z, 2) < -1,
        "heat_title": _heat_title(z_50, z_200, z),
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


def market_key_for_currency(latest):
    if latest is None or not latest.currency:
        return None
    return CURRENCY_TO_MARKET.get(str(latest.currency).strip().upper())


def market_key_for_ticker(latest, symbol=None, ticker_model=Ticker):
    """Return the market-metrics key for a ticker, or None."""
    lookup = symbol or (latest.ticker if latest is not None else None)
    if lookup:
        ticker = db.session.get(ticker_model, lookup)
        if ticker and ticker.market:
            return ticker.market
    return market_key_for_currency(latest)


def _market_row(market_model, market, trading_date):
    if not market or trading_date is None:
        return None
    return db.session.get(market_model, (market, trading_date))


def _z_scores_for_metric(metric, ticker_model=Ticker, market_model=MarketMetric):
    market = market_key_for_ticker(metric, ticker_model=ticker_model)
    market_row = _market_row(market_model, market, metric.trading_date)
    if market_row is None:
        return None, None
    z_50 = z_score(metric.raw_50, market_row.raw_mean_50, market_row.raw_std_50)
    z_200 = z_score(metric.raw_200, market_row.raw_mean_200, market_row.raw_std_200)
    return z_50, z_200


def _stocks_for_exchange(exchange_key):
    metric_model, ticker_model, market_model = _tables_for_country(
        EXCHANGE_COUNTRY[exchange_key]
    )
    metrics = _get_latest_metrics(metric_model)
    tickers = _ticker_map(ticker_model, [metric.ticker for metric in metrics])
    matched = [
        metric
        for metric in metrics
        if metric.ticker in tickers
        and exchange_name_matches(tickers[metric.ticker].exchange_name, exchange_key)
    ]
    sectors = {
        symbol: _display_sector(ticker.sector) for symbol, ticker in tickers.items()
    }
    return [
        _stock_row(
            metric,
            *_z_scores_for_metric(metric, ticker_model, market_model),
            sector=sectors.get(metric.ticker),
        )
        for metric in matched
    ]


@stocks_bp.route("/stocks")
@role_required(Role.USER, Role.ADMIN)
def stocks():
    selected_exchange = parse_exchange(request.args.get("exchange"))
    stock_rows = _stocks_for_exchange(selected_exchange) if selected_exchange else []
    return render_template(
        "stocks.html",
        title="Aktier",
        stocks=stock_rows,
        selected_exchange=selected_exchange,
    )


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
