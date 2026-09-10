from src import db


class SweMarketMetric(db.Model):
    """Read-only country-level market observations from Neon `swe_market_metrics`."""

    __tablename__ = "swe_market_metrics"
    __table_args__ = {"extend_existing": True}

    market = db.Column(db.Text, primary_key=True)
    trading_date = db.Column(db.Date, primary_key=True)
    momentum_mean = db.Column(db.Numeric(18, 6), nullable=True)
    momentum_std = db.Column(db.Numeric(18, 6), nullable=True)

    def __repr__(self):
        return f"<SweMarketMetric {self.market} {self.trading_date} {self.momentum_mean}>"
