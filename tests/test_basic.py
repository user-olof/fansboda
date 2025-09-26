"""
Basic smoke tests to verify the test setup is working correctly.
"""

from src import db
from src.models.user import User


class TestBasicFunctionality:
    """Basic smoke tests."""

    def test_app_import(self, app):
        """Test that we can import the Flask app."""
        assert app is not None
        assert app.name == "src"

    def test_database_import(self):
        """Test that we can import the database."""
        assert db is not None

    def test_user_model_import(self):
        """Test that we can import the User model."""
        assert User is not None

    def test_client_fixture(self, client):
        """Test that the client fixture works."""
        assert client is not None
        # Test a simple request - use the correct blueprint route name
        response = client.get("/")  # This should work now
        # Note: This might redirect to login, so check for 200 or 302
        assert response.status_code in [200, 302]

    def test_database_fixture(self, client):
        """Test that database operations work in tests."""
        with client.application.app_context():
            # Create a user
            user = User(email="smoke@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Query the user
            found_user = User.query.filter_by(email="smoke@example.com").first()
            assert found_user is not None
