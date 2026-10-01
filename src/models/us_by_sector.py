from src import db


class UsBySector(db.Model):
    """Read-only sector aggregates from Neon `us_by_sector`."""

    __tablename__ = "us_by_sector"
    __table_args__ = {"extend_existing": True}

    sector = db.Column(db.Text, primary_key=True)
    week_start = db.Column(db.Date, primary_key=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ticker_count = db.Column(db.Integer, nullable=True)
    momentum_mean = db.Column(db.Numeric(18, 6), nullable=True)
    momentum_median = db.Column(db.Numeric(18, 6), nullable=True)
    z_score_mean = db.Column(db.Numeric(18, 6), nullable=True)
    pct_uptrend = db.Column(db.Numeric(18, 6), nullable=True)

    def __repr__(self):
        return f"<UsBySector {self.sector} {self.week_start}>"
