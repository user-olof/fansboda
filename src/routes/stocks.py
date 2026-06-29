# src/routes/stocks.py
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


@stocks_bp.route("/stocks")
@role_required(Role.USER, Role.ADMIN)
def stocks():
    metrics = _get_latest_metrics()
    return render_template("stocks.html", title="Aktier", stocks=metrics)


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
