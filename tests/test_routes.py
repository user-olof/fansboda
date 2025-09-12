from src.models.user import User
from src import db
from unittest.mock import patch


class TestRoutes:
    """Test cases for application routes."""

    def test_index_route_redirect_when_not_logged_in(self, client):
        """Test that index route redirects to login when not authenticated."""
        response = client.get("/")
        assert response.status_code == 302
        assert "/login" in response.location

    def test_index_route_with_login(self, client, auth):
        """Test index route when logged in."""
        with client.application.app_context():
            # Create a test user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login and access index
            # with patch("src.models.user.User.is_allowed", return_value=True):
            auth.login()
            response = client.get("/")
            assert response.status_code == 200
            assert b"You have successfully logged in" in response.data

    def test_users_route(self, client):
        """Test users route."""
        response = client.get("/users")
        assert response.status_code == 200
        assert b"Users" in response.data

    def test_login_route_get(self, client):
        """Test login route GET request."""
        response = client.get("/login")
        assert response.status_code == 200
        # Note: This will fail without the login.html template
        # You'll need to create the template or mock the render_template

    def test_login_route_post_valid_credentials(self, client):
        """Test login with valid credentials."""
        with client.application.app_context():
            # Create a test user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

        response = client.post(
            "/login", data={"email": "test@example.com", "password": "testpass"}
        )
        assert response.status_code == 302
        assert "/" in response.location

    def test_login_route_post_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/login", data={"email": "nonexistent", "password": "wrongpass"}
        )
        assert response.status_code == 302
        assert "/login" in response.location

    def test_login_redirect_when_already_authenticated(self, client, auth):
        """Test that login redirects to index when already authenticated."""
        with client.application.app_context():
            # Create a test user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Try to access login page again
            
            # Login first
            auth.login()
            response = client.get("/login")
            assert response.status_code == 302
            assert "/" in response.location

    def test_logout_route(self, client, auth):
        """Test logout route."""
        with client.application.app_context():
            # Create a test user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

        # Login first
        auth.login()

        # Then logout
        response = client.get("/logout")
        assert response.status_code == 302
        assert "/" in response.location

        # Verify we're logged out by trying to access protected route
        response = client.get("/")
        assert response.status_code == 302
        assert "/login" in response.location


class TestErrorHandlers:
    """Test cases for error handlers."""

    def test_404_error_handler(self, client):
        """Test 404 error handler."""
        response = client.get("/nonexistent-route")
        assert response.status_code == 404
        # Note: This will fail without the 404.html template properly configured
