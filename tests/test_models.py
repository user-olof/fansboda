import pytest
from src.models.user import User, Role
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
