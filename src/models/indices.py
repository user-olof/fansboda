from src import db


class Indice(db.Model):
    """Read-only market and sector index observations from Neon `indices`."""

    __tablename__ = "indices"
    __table_args__ = {"extend_existing": True}

    ticker = db.Column(db.Text, primary_key=True)
    trading_date = db.Column(db.Date, primary_key=True)
    sector = db.Column(db.Text, nullable=False)
    country = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ticker_count = db.Column(db.Integer, nullable=True)
    current_price = db.Column(db.Numeric(18, 6), nullable=True)
    sma_50 = db.Column(db.Numeric(18, 6), nullable=True)
    sma_200 = db.Column(db.Numeric(18, 6), nullable=True)
    momentum = db.Column(db.Numeric(18, 6), nullable=True)
    currency = db.Column(db.Text, nullable=True)
    pct_uptrend = db.Column(db.Numeric(18, 6), nullable=True)
    z_score = db.Column(db.Numeric(18, 6), nullable=True)

    def __repr__(self):
        return f"<Indice {self.ticker} {self.trading_date}>"
