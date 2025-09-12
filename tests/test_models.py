import pytest
from src.models.user import User
from src import db


class TestUserModel:
    """Test cases for the User model."""

    def test_user_creation(self, client):
        """Test creating a new user."""
        user = User(email="test@example.com")
        assert user.email == "test@example.com"
        assert user.password_hash is None

    def test_user_repr(self, client):
        """Test user string representation."""
        user = User(email="test@example.com")
        assert repr(user) == "<User test@example.com>"

    def test_set_password(self, client):
        """Test password hashing."""
        user = User(email="test@example.com")
        user.password_hash = "testpassword"
        assert user.password_hash is not None
        assert user.password_hash != "testpassword"

    def test_check_password(self, client):
        """Test password verification."""
        user = User(email="test@example.com")
        user.password_hash = "testpassword"
        assert user.authenticate("testpassword") is True
        assert user.authenticate("wrongpassword") is False

    def test_user_uniqueness(self, client):
        """Test that usernames and emails must be unique."""
        with client.application.app_context():
            user1 = User(email="test1@example.com")
            user1.password_hash = "password1"
            db.session.add(user1)
            db.session.commit()

            # Try to create another user with same email
            user2 = User(email="test1@example.com")
            user2.password_hash = "password2"
            db.session.add(user2)

            with pytest.raises(Exception):
                db.session.commit()

    def test_user_database_operations(self, client):
        """Test basic database operations with User model."""
        with client.application.app_context():
            # Create and save user
            user = User(email="dbtest@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Query user
            found_user = User.query.filter_by(email="dbtest@example.com").first()
            assert found_user is not None
            assert found_user.email == "dbtest@example.com"
            assert found_user.authenticate("testpass") is True
