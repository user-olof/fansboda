from src import db
from sqlalchemy import text


class TestAppConfiguration:
    """Test cases for Flask application configuration."""

    def test_app_exists(self, app):
        """Test that the Flask app exists."""
        assert app is not None

    def test_database_configuration(self, client):
        """Test database configuration."""

        assert client.application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] is False

    def test_secret_key_set(self, client):
        """Test that secret key is set for testing."""
        assert client.application.config["SECRET_KEY"] is not None

    def test_database_creation(self, client):
        """Test that database tables are created."""
        with client.application.app_context():
            # Check if tables exist by trying to query
            from src.models.user import User

            users = User.query.all()
            assert isinstance(users, list)


class TestDatabaseIntegration:
    """Integration tests for database operations."""

    def test_database_connection(self, client):
        """Test database connection."""
        with client.application.app_context():
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT 1")).scalar()
            assert result == 1

    def test_user_crud_operations(self, client):
        """Test complete CRUD operations for User model."""
        with client.application.app_context():
            from src.models.user import User

            # Create
            user = User(email="crud@example.com")
            user.password_hash = "crudpass"
            db.session.add(user)
            db.session.commit()

            # Read
            found_user = User.query.filter_by(email="crud@example.com").first()
            assert found_user is not None

            # Update
            found_user.email = "updated@example.com"
            db.session.commit()

            updated_user = User.query.filter_by(email="updated@example.com").first()
            assert updated_user is not None

            # Delete
            db.session.delete(updated_user)
            db.session.commit()

            deleted_user = User.query.filter_by(email="updated@example.com").first()
            assert deleted_user is None
