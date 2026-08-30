from src import db


class MarketMetric(db.Model):
    """Read-only country-level market observations from Neon `market_metrics`."""

    __tablename__ = "market_metrics"
    __table_args__ = {"extend_existing": True}

    market = db.Column(db.Text, primary_key=True)
    trading_date = db.Column(db.Date, primary_key=True)
    raw_mean_50 = db.Column(db.Numeric(18, 6), nullable=True)
    raw_mean_200 = db.Column(db.Numeric(18, 6), nullable=True)
    raw_std_50 = db.Column(db.Numeric(18, 6), nullable=True)
    raw_std_200 = db.Column(db.Numeric(18, 6), nullable=True)

    @property
    def sma_200(self):
        """Chart overlay uses the market's 200-day mean raw ratio."""
        return self.raw_mean_200

    def __repr__(self):
        return f"<MarketMetric {self.market} {self.trading_date} {self.raw_mean_200}>"
