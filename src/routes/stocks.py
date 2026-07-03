# src/routes/stocks.py
from datetime import date, timedelta

from flask import Blueprint, render_template, jsonify
from src import db
from src.access_control import role_required
from src.models.metrics import Metric
from src.models.user import Role

stocks_bp = Blueprint("stocks", __name__)


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
    return render_template("stocks.html", title="Aktier", stocks=metrics)


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
    company_name = latest.name if latest else ticker
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
                "name": m.name,
                "ticker": m.ticker,
                "current_price": (
                    float(m.current_price) if m.current_price is not None else None
                ),
            }
            for m in metrics
        ]
    )
