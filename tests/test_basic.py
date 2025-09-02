"""
Basic smoke tests to verify the test setup is working correctly.
"""

from src import app, db
from src.models.user import User


class TestBasicFunctionality:
    """Basic smoke tests."""

    def test_app_import(self):
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
        # Test a simple request
        response = client.get("/users")  # This route doesn't require auth
        assert response.status_code == 200

    def test_database_fixture(self, client):
        """Test that database operations work in tests."""
        with client.application.app_context():
            # Create a user
            user = User(email="smoke@example.com")
            user.set_password("testpass")
            db.session.add(user)
            db.session.commit()

            # Query the user
            found_user = User.query.filter_by(email="smoke@example.com").first()
            assert found_user is not None
