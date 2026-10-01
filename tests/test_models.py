import pytest
from datetime import date
from decimal import Decimal

from src.models.user import User, Role
from src.models.metrics import Metric
from src.models.market_metrics import MarketMetric
from src.models.swe_by_sector import SweBySector
from src.models.swe_market_metrics import SweMarketMetric
from src.models.swe_metrics import SweMetric
from src.models.swe_ticker import SweTicker
from src.models.ticker import Ticker
from src.models.us_by_sector import UsBySector
from src import db


class TestUserModel:
    """Test cases for the User model."""

    def test_user_creation(self, user):
        """Test creating a new user."""
        assert user.email == "test@example.com"
        assert user.password_hash is not None

    def test_user_repr(self, user):
        """Test user string representation."""
        assert repr(user) == "<User test@example.com (user)>"

    def test_set_password(self, user):
        """Test password hashing."""
        assert user.password_hash is not None
        assert user.password_hash != "testpass"

    def test_check_password(self, user):
        """Test password verification."""
        assert user.authenticate("testpass") is True
        assert user.authenticate("wrongpass") is False

    def test_user_uniqueness(self, user, client):
        """Test that usernames and emails must be unique."""
        with client.application.app_context():
            db.session.add(user)
            db.session.commit()

            # Try to create another user with same email
            user2 = User(email="test@example.com", role=Role.USER)
            user2.password_hash = "password2"
            db.session.add(user2)

            with pytest.raises(Exception):
                db.session.commit()

    def test_user_database_operations(self, user, client):
        """Test basic database operations with User model."""
        with client.application.app_context():
            # Create and save user
            db.session.add(user)
            db.session.commit()

            # Query user
            found_user = User.query.filter_by(email="test@example.com").first()
            assert found_user is not None
            assert found_user.email == "test@example.com"
            assert found_user.authenticate("testpass") is True


class TestMetricModel:
    """Test cases for the Metric model."""

    def test_us_table_names_and_exchange_name(self, client):
        assert Ticker.__tablename__ == "us_tickers"
        assert Metric.__tablename__ == "us_metrics"
        assert MarketMetric.__tablename__ == "us_market_metrics"
        with client.application.app_context():
            ticker = Ticker(
                symbol="AAPL",
                company="Apple Inc.",
                market="us_market",
                exchange_name="NASDAQ",
                business_summary="Apple designs consumer electronics.",
            )
            db.session.add(ticker)
            db.session.commit()
            found = db.session.get(Ticker, "AAPL")
            assert found.exchange_name == "NASDAQ"
            assert found.business_summary == "Apple designs consumer electronics."
            assert "exchange_name" in Ticker.__table__.c
            assert "business_summary" in Ticker.__table__.c

    def test_swe_ticker_business_summary(self, client):
        assert SweTicker.__tablename__ == "swe_tickers"
        with client.application.app_context():
            ticker = SweTicker(
                symbol="VOLV-B.ST",
                company="Volvo AB",
                market="se_market",
                exchange_name="OMX Stockholm",
                business_summary="Volvo AB manufactures trucks and buses.",
            )
            db.session.add(ticker)
            db.session.commit()
            found = db.session.get(SweTicker, "VOLV-B.ST")
            assert found.business_summary == "Volvo AB manufactures trucks and buses."
            assert "business_summary" in SweTicker.__table__.c

    def test_metric_creation(self, client):
        """Test creating a metric with optional display fields."""
        with client.application.app_context():
            metric = Metric(
                ticker="VOLV-B.ST",
                company="Volvo AB",
                trading_date=date(2026, 7, 1),
                current_price=265.50,
                sma_50=250.1234,
                sma_200=230.5678,
                currency="SEK",
                momentum=1.08,
                z_score=0.0,
            )
            db.session.add(metric)
            db.session.commit()

            found = Metric.query.filter_by(ticker="VOLV-B.ST").one()
            assert found.company == "Volvo AB"
            assert found.currency == "SEK"
            assert float(found.current_price) == 265.50
            assert float(found.momentum) == 1.08
            assert float(found.z_score) == 0.0

    def test_observation_models_drop_raw_columns(self):
        for model in (Metric, SweMetric, MarketMetric, SweMarketMetric):
            raw_columns = [name for name in model.__table__.c.keys() if name.startswith("raw_")]
            assert raw_columns == []
        assert "momentum" in Metric.__table__.c
        assert "z_score" in Metric.__table__.c
        assert "momentum" in SweMetric.__table__.c
        assert "z_score" in SweMetric.__table__.c
        assert "momentum_mean" in MarketMetric.__table__.c
        assert "momentum_std" in MarketMetric.__table__.c
        assert "momentum_mean" in SweMarketMetric.__table__.c
        assert "momentum_std" in SweMarketMetric.__table__.c
        assert "sma_200" not in MarketMetric.__table__.c

    def test_market_metric_creation(self, client):
        """Test creating a country-level market momentum row."""
        with client.application.app_context():
            row = MarketMetric(
                market="us_market",
                trading_date=date(2026, 7, 1),
                momentum_mean=1.02,
                momentum_std=0.15,
            )
            db.session.add(row)
            db.session.commit()

            found = MarketMetric.query.filter_by(market="us_market").one()
            assert found.market == "us_market"
            assert found.trading_date == date(2026, 7, 1)
            assert float(found.momentum_mean) == 1.02
            assert float(found.momentum_std) == 0.15
            assert "id" not in MarketMetric.__table__.c

    def test_heat_color_from_stored_z_at_market(self):
        from src.routes.stocks import heat_color_from_z

        assert heat_color_from_z(0) == "#fef9c3"
        assert heat_color_from_z(0.5) == "#fb923c"
        assert heat_color_from_z(-0.5) == "#93c5fd"
        assert heat_color_from_z(None) == "#e5e7eb"

    def test_heat_color_finer_shades_in_band(self):
        from src.routes.stocks import heat_color_from_z

        mild = heat_color_from_z(-0.6)
        stronger = heat_color_from_z(-0.9)
        assert mild != stronger
        assert mild != heat_color_from_z(0)
        assert stronger != heat_color_from_z(-2)

    def test_heat_color_clamps_extremes_and_missing(self):
        from src.routes.stocks import heat_color_from_z

        assert heat_color_from_z(-2) == "#1d4ed8"
        assert heat_color_from_z(-3) == "#1d4ed8"
        assert heat_color_from_z(2) == "#991b1b"
        assert heat_color_from_z(3) == "#991b1b"
        assert heat_color_from_z(None) == "#e5e7eb"

    def test_display_sector_replaces_dashes_with_spaces(self):
        from src.routes.stocks import _display_sector

        assert _display_sector("communication-services") == "communication services"
        assert _display_sector("foo--bar") == "foo bar"
        assert _display_sector("   ") is None
        assert _display_sector(None) is None


class TestSectorModels:
    def test_us_and_swe_by_sector_map_neon_tables(self, client):
        assert UsBySector.__tablename__ == "us_by_sector"
        assert SweBySector.__tablename__ == "swe_by_sector"
        for model in (UsBySector, SweBySector):
            pk = {column.name for column in model.__table__.primary_key.columns}
            assert pk == {"sector", "week_start"}
            for name in (
                "ticker_count",
                "z_score_mean",
                "pct_uptrend",
                "momentum_mean",
                "momentum_median",
                "updated_at",
            ):
                assert name in model.__table__.c

    def test_us_by_sector_round_trip(self, client):
        with client.application.app_context():
            row = UsBySector(
                sector="energy",
                week_start=date(2026, 9, 28),
                ticker_count=190,
                z_score_mean=Decimal("0.317925"),
                pct_uptrend=Decimal("72.631579"),
            )
            db.session.add(row)
            db.session.commit()
            found = db.session.get(UsBySector, ("energy", date(2026, 9, 28)))
            assert found.ticker_count == 190
            assert float(found.z_score_mean) == 0.317925
            assert float(found.pct_uptrend) == 72.631579

    def test_swe_by_sector_round_trip(self, client):
        with client.application.app_context():
            row = SweBySector(
                sector="basic-materials",
                week_start=date(2026, 9, 21),
                ticker_count=36,
                z_score_mean=Decimal("0.101050"),
                pct_uptrend=Decimal("55.555556"),
            )
            db.session.add(row)
            db.session.commit()
            found = db.session.get(SweBySector, ("basic-materials", date(2026, 9, 21)))
            assert found.ticker_count == 36
            assert float(found.pct_uptrend) == 55.555556

    def test_ratio_label_uses_stored_percent(self):
        from src.routes.stocks import _ratio_label

        assert _ratio_label(Decimal("72.631579")) == "72.6%"
        assert _ratio_label(Decimal("55.555556")) == "55.6%"
        assert _ratio_label(None) is None
        assert _ratio_label(0) == "0.0%"
