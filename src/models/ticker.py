from src import db


class Ticker(db.Model):
    """Read-only ticker directory from Neon `tickers`."""

    __tablename__ = "tickers"
    __table_args__ = {"extend_existing": True}

    symbol = db.Column(db.Text, primary_key=True)
    company = db.Column(db.Text, nullable=True)
    sector = db.Column(db.Text, nullable=True)
    industry = db.Column(db.Text, nullable=True)
    market = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f"<Ticker {self.symbol} {self.market}>"
