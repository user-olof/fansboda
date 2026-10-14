from src import db


class UkMarketMetric(db.Model):
    """Read-only country-level market observations from Neon `uk_market_metrics`."""

    __tablename__ = "uk_market_metrics"
    __table_args__ = {"extend_existing": True}

    market = db.Column(db.Text, primary_key=True)
    week_start = db.Column(db.Date, primary_key=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    momentum_mean = db.Column(db.Numeric(18, 6), nullable=True)
    momentum_std = db.Column(db.Numeric(18, 6), nullable=True)

    def __repr__(self):
        return f"<UkMarketMetric {self.market} {self.week_start} {self.momentum_mean}>"
