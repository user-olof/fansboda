from src import db
from datetime import datetime, timezone




class Metric(db.Model):
    __tablename__ = "metrics"
    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(20), nullable=False, index=True)
    company = db.Column(db.String(255), nullable=False)
    trading_date = db.Column(db.Date, nullable=False, index=True)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    sma_50 = db.Column(db.Numeric(18, 4), nullable=True)
    sma_200 = db.Column(db.Numeric(18, 4), nullable=True)
    current_price = db.Column(db.Numeric(18, 4), nullable=True)
    currency = db.Column(db.String(10), nullable=True)
    raw_50 = db.Column(db.Numeric(18, 6), nullable=True)
    raw_200 = db.Column(db.Numeric(18, 6), nullable=True)


    def __repr__(self):
        return f"<Metric {self.ticker} {self.trading_date} {self.current_price}>"
