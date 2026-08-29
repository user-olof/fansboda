import pytest
from datetime import date

from src.models.user import User, Role
from src.models.metrics import Metric
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

    def test_heat_score_neutral_when_sma_or_price_missing(self):
        from types import SimpleNamespace

        from src.routes.stocks import calculate_heat_score

        rows = [
            SimpleNamespace(
                sma_50=None,
                sma_200=100,
                current_price=110,
                trading_date=date(2026, 1, 1),
            ),
            SimpleNamespace(
                sma_50=None,
                sma_200=100,
                current_price=110,
                trading_date=date(2026, 1, 2),
            ),
        ]
        assert calculate_heat_score(rows) == 0
