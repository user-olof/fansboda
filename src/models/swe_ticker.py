from src import db


class SweTicker(db.Model):
    """Read-only ticker directory from Neon `swe_tickers`."""

    __tablename__ = "swe_tickers"
    __table_args__ = {"extend_existing": True}

    symbol = db.Column(db.Text, primary_key=True)
    company = db.Column(db.Text, nullable=True)
    sector = db.Column(db.Text, nullable=True)
    industry = db.Column(db.Text, nullable=True)
    market = db.Column(db.Text, nullable=True)
    exchange_name = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<SweTicker {self.symbol} {self.exchange_name or self.market}>"
