import pytest
from datetime import date

from src.models.user import User, Role
from src.models.metrics import Metric
from src.models.market_metrics import MarketMetric
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
            )
            db.session.add(metric)
            db.session.commit()

            found = Metric.query.filter_by(ticker="VOLV-B.ST").one()
            assert found.company == "Volvo AB"
            assert found.currency == "SEK"
            assert float(found.current_price) == 265.50

    def test_market_metric_creation(self, client):
        """Test creating a country-level market SMA-200 row."""
        with client.application.app_context():
            row = MarketMetric(
                market="us_market",
                trading_date=date(2026, 7, 1),
                raw_mean_200=2400.5,
            )
            db.session.add(row)
            db.session.commit()

            found = MarketMetric.query.filter_by(market="us_market").one()
            assert found.market == "us_market"
            assert found.trading_date == date(2026, 7, 1)
            assert float(found.raw_mean_200) == 2400.5
            assert float(found.sma_200) == 2400.5
            assert "id" not in MarketMetric.__table__.c

    def test_z_score_is_zero_at_market_average(self):
        from src.routes.stocks import combined_z, heat_color_from_z, z_score

        assert z_score(0.95, 0.95, 0.05) == 0
        assert combined_z(0, 0) == 0
        assert heat_color_from_z(0) == "#fef9c3"

    def test_z_score_hotter_when_below_market_mean(self):
        from src.routes.stocks import combined_z, heat_color_from_z, z_score

        z_50 = z_score(0.85, 0.95, 0.05)
        assert z_50 == pytest.approx(-2)
        assert combined_z(z_50, None) == pytest.approx(-2)
        assert heat_color_from_z(z_50) == "#991b1b"

    def test_z_score_unavailable_when_std_missing(self):
        from src.routes.stocks import combined_z, heat_color_from_z, z_score

        assert z_score(0.9, 0.95, None) is None
        assert z_score(0.9, 0.95, 0) is None
        assert combined_z(None, None) is None
        assert heat_color_from_z(None) == "#e5e7eb"

    def test_display_sector_replaces_dashes_with_spaces(self):
        from src.routes.stocks import _display_sector

        assert _display_sector("communication-services") == "communication services"
        assert _display_sector("foo--bar") == "foo bar"
        assert _display_sector("   ") is None
        assert _display_sector(None) is None
