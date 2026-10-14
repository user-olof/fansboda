from src import db


class Ticker(db.Model):
    """Read-only ticker directory from Neon `us_tickers`."""

    __tablename__ = "us_tickers"
    __table_args__ = {"extend_existing": True}

    symbol = db.Column(db.Text, primary_key=True)
    company = db.Column(db.Text, nullable=True)
    sector = db.Column(db.Text, nullable=True)
    industry = db.Column(db.Text, nullable=True)
    market = db.Column(db.Text, nullable=True)
    exchange_name = db.Column(db.Text, nullable=True)
    business_summary = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Ticker {self.symbol} {self.exchange_name or self.market}>"
