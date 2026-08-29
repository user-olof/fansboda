# src/routes/stocks.py
from datetime import date, timedelta

from flask import Blueprint, render_template, jsonify
from src import db
from src.access_control import role_required
from src.models.metrics import Metric
from src.models.user import Role

stocks_bp = Blueprint("stocks", __name__)

LOOKBACK_DAYS = 10
DIP_TOLERANCE = 0.02
RISING_FASTER_WEEKS = 3

HEAT_COLORS = {
    -1: "#93c5fd",
    0: "#dbeafe",
    1: "#fef08a",
    2: "#fdba74",
    3: "#fb923c",
    4: "#f87171",
    5: "#dc2626",
    6: "#991b1b",
}


def _to_float(value):
    return float(value) if value is not None else None


def _get_recent_metrics_by_ticker(weeks=8):
    """Return recent Metric rows grouped by ticker, ordered by trading_date asc."""
    cutoff = date.today() - timedelta(weeks=weeks)
    rows = (
        db.session.query(Metric)
        .filter(Metric.trading_date >= cutoff)
        .order_by(Metric.ticker, Metric.trading_date.asc())
        .all()
    )

    by_ticker = {}
    for row in rows:
        by_ticker.setdefault(row.ticker, []).append(row)
    return by_ticker


def _row_on_or_before(rows, target_date):
    """Return the last row with trading_date on or before target_date."""
    match = None
    for row in rows:
        if row.trading_date <= target_date:
            match = row
        else:
            break
    return match


def _sma_50_rising_faster_three_weeks(rows):
    """True if sma_50 rose faster than sma_200 for 3 consecutive calendar weeks."""
    if not rows:
        return False

    end_date = rows[-1].trading_date
    boundaries = [
        end_date - timedelta(weeks=RISING_FASTER_WEEKS),
        end_date - timedelta(weeks=2),
        end_date - timedelta(weeks=1),
        end_date,
    ]

    snapshots = []
    for boundary_date in boundaries:
        row = _row_on_or_before(rows, boundary_date)
        if row is None:
            return False
        snapshots.append(row)

    for previous, current in zip(snapshots, snapshots[1:]):
        prev_sma_50 = _to_float(previous.sma_50)
        prev_sma_200 = _to_float(previous.sma_200)
        curr_sma_50 = _to_float(current.sma_50)
        curr_sma_200 = _to_float(current.sma_200)

        if None in (prev_sma_50, prev_sma_200, curr_sma_50, curr_sma_200):
            return False

        if (curr_sma_50 - prev_sma_50) <= (curr_sma_200 - prev_sma_200):
            return False

    return True


def _sma_50_crossed_below_sma_200(rows):
    """True if sma_50 recently crossed below sma_200."""
    for previous, current in zip(rows, rows[1:]):
        prev_sma_50 = _to_float(previous.sma_50)
        prev_sma_200 = _to_float(previous.sma_200)
        curr_sma_50 = _to_float(current.sma_50)
        curr_sma_200 = _to_float(current.sma_200)

        if None in (prev_sma_50, prev_sma_200, curr_sma_50, curr_sma_200):
            continue

        if prev_sma_50 >= prev_sma_200 and curr_sma_50 < curr_sma_200:
            return True
    return False


def _price_dipped_to_sma(rows):
    """True if latest price is within tolerance of sma_50 or sma_200."""
    if not rows:
        return False

    latest = rows[-1]
    price = _to_float(latest.current_price)
    if price is None:
        return False

    for sma in (_to_float(latest.sma_50), _to_float(latest.sma_200)):
        if sma is not None and sma > 0 and abs(price - sma) / sma <= DIP_TOLERANCE:
            return True
    return False


def calculate_heat_score(rows):
    """
    Score stock heat from recent metrics history.

    Rules:
    - sma_50 below sma_200: 0 points (no bonus for position)
    - sma_50 rising faster than sma_200 for 3 weeks in a row (only when sma_50 below sma_200): +1
    - sma_50 over sma_200: +2
    - current_price over both sma_50 and sma_200 (only when sma_50 below sma_200): +2
    - current_price dipping to sma_50 or sma_200 on latest date: +1
    - sma_200 sloping upward: +1
    - sma_50 dipping below sma_200: -1
    """
    if len(rows) < 2:
        return 0

    latest = rows[-1]
    lookback = rows[max(0, len(rows) - 1 - LOOKBACK_DAYS)]

    sma_50 = _to_float(latest.sma_50)
    sma_200 = _to_float(latest.sma_200)
    price = _to_float(latest.current_price)

    if None in (sma_50, sma_200, price):
        return 0

    score = 0

    if sma_50 > sma_200:
        score += 2

    if sma_50 < sma_200 and _sma_50_rising_faster_three_weeks(rows):
        score += 1

    if sma_50 < sma_200 and price > sma_50 and price > sma_200:
        score += 2

    if _price_dipped_to_sma(rows):
        score += 1

    lookback_sma_200_val = _to_float(lookback.sma_200)
    if lookback_sma_200_val is not None and sma_200 > lookback_sma_200_val:
        score += 1

    if _sma_50_crossed_below_sma_200(rows[-LOOKBACK_DAYS:]):
        score -= 1

    return score


def _heat_color(score):
    clamped = max(-1, min(6, score))
    return HEAT_COLORS.get(clamped, "#e5e7eb")


def _stock_row(metric, heat_score):
    return {
        "company": metric.company,
        "ticker": metric.ticker,
        "currency": metric.currency,
        "current_price": metric.current_price,
        "heat_score": heat_score,
        "heat_color": _heat_color(heat_score),
    }


def _get_latest_metrics():
    """Return the latest Metric row per ticker (by trading_date), newest first."""
    latest_dates = (
        db.session.query(
            Metric.ticker,
            db.func.max(Metric.trading_date).label("latest_date"),
        )
        .group_by(Metric.ticker)
        .subquery()
    )

    return (
        db.session.query(Metric)
        .join(
            latest_dates,
            db.and_(
                Metric.ticker == latest_dates.c.ticker,
                Metric.trading_date == latest_dates.c.latest_date,
            ),
        )
        .order_by(Metric.trading_date.desc())
        .all()
    )


def get_last_weeks_metrics(ticker, weeks=52):
    """Return daily metrics for a ticker over the last `weeks` weeks from Neon."""
    cutoff = date.today() - timedelta(weeks=weeks)

    rows = (
        db.session.query(Metric)
        .filter(
            Metric.ticker == ticker,
            Metric.trading_date >= cutoff,
        )
        .order_by(Metric.trading_date.asc())
        .all()
    )

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


@stocks_bp.route("/stocks")
@role_required(Role.USER, Role.ADMIN)
def stocks():
    metrics = _get_latest_metrics()
    recent_by_ticker = _get_recent_metrics_by_ticker()
    stocks = [
        _stock_row(
            metric, calculate_heat_score(recent_by_ticker.get(metric.ticker, []))
        )
        for metric in metrics
    ]
    return render_template("stocks.html", title="Aktier", stocks=stocks)


@stocks_bp.route("/stocks/chart/<ticker>")
@role_required(Role.USER, Role.ADMIN)
def chart(ticker):
    history = get_last_weeks_metrics(ticker)
    latest = (
        db.session.query(Metric)
        .filter(Metric.ticker == ticker)
        .order_by(Metric.trading_date.desc())
        .first()
    )
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
    """Return the latest price per ticker (by trading_date) from the metrics table."""
    metrics = _get_latest_metrics()
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
