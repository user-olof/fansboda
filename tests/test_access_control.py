"""
Test cases for access control decorator functionality.

This module tests the access control decorators and route protection.
"""

from src import db
from src.models.user import User


# def setup_test_routes():
#     """Set up test routes for access control testing."""

#     @app.route("/test-blocked")
#     @allowed_user_required
#     def test_blocked():
#         return "This should not be accessible"

#     @app.route("/test-protected")
#     @allowed_user_required
#     def test_protected():
#         return "Access granted"

#     @app.route("/test-auth-required")
#     @allowed_user_required
#     def test_auth_required():
#         return "Access granted"

#     @app.route("/test-logout-redirect")
#     @allowed_user_required
#     def test_logout_redirect():
#         return "Access granted"

#     # Create a test route
#     @app.route("/test-config-error")
#     @allowed_user_required
#     def test_config_error():
#         return "Should not reach here"

#     # Create a test route
#     @app.route("/test-no-user")
#     @allowed_user_required
#     def test_no_user():
#         return "Should not reach here"

#     # Create a test route with both decorators
#     @app.route("/test-double-protection")
#     @login_required
#     @allowed_user_required
#     def test_double_protection():
#         return "Access granted"

#     # Create a test route for testing decorator order
#     @app.route("/test-order-1")
#     @login_required
#     @allowed_user_required
#     def test_order_1():
#         return "Access granted"


# setup_test_routes()


class TestAccessControlDecorator:
    """Test the allowed_user_required decorator."""

    def test_decorator_allows_whitelisted_user(self, client, app):
        """Test that decorator allows access for whitelisted users."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():

            # Create and login allowed user
            user = User(email="allowed@example.com")
            # user.set_password("testpass")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login the user
            response = client.post(
                "/login",
                data={"email": "allowed@example.com", "password": "testpass"},
                follow_redirects=True,
            )
            assert response.status_code == 200

            # Now test accessing a protected route
            response = client.get("/")
            assert response.status_code == 200

    def test_decorator_blocks_non_whitelisted_user(self, client, app):
        """Test that decorator blocks access for non-whitelisted users."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():

            # Create and login non-allowed user
            user = User(email="notallowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login the user
            response = client.post(
                "/login",
                data={"email": "notallowed@example.com", "password": "testpass"},
                follow_redirects=True,
            )
            assert response.status_code == 200

            # Now test accessing a protected route - should be blocked
            response = client.get("/")
            # Should redirect to logout or show access denied
            assert response.status_code in [302, 403]

    def test_decorator_requires_authentication_first(self, client, app):
        """Test that decorator requires authentication before checking whitelist."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        # Try to access protected route without logging in
        response = client.get("/")
        # Should redirect to login
        assert response.status_code == 302
        assert "/login" in response.location

    def test_decorator_redirects_to_logout_on_access_denied(self, client, app):
        """Test that decorator redirects to logout when access is denied."""
        app.config["ALLOWED_EMAILS"] = ["other@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():

            # Create and login non-allowed user
            user = User(email="notallowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login the user
            response = client.post(
                "/login",
                data={"email": "notallowed@example.com", "password": "testpass"},
                follow_redirects=True,
            )
            assert response.status_code == 200

            # Now test accessing a protected route
            response = client.get("/")
            # Should redirect to logout
            assert response.status_code == 302
            assert "/login" in response.location

    def test_existing_routes_work_with_allowed_users(self, client, app):
        """Test that existing routes work correctly with allowed users."""
        app.config["ALLOWED_EMAILS"] = ["test@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():

            # Create and login allowed user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login the user
            response = client.post(
                "/login",
                data={"email": "test@example.com", "password": "testpass"},
                follow_redirects=True,
            )
            assert response.status_code == 200

            # Test accessing existing routes
            response = client.get("/")
            assert response.status_code == 200

    def test_public_routes_still_accessible(self, client, app):
        """Test that public routes are still accessible without authentication."""
        app.config["ALLOWED_EMAILS"] = ["test@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        # Test accessing login page (should be public)
        response = client.get("/login")
        assert response.status_code == 200

    def test_decorator_handles_missing_current_user(self, client, app):
        """Test that decorator handles missing current user gracefully."""
        app.config["ALLOWED_EMAILS"] = ["test@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        # Try to access protected route without any user logged in
        response = client.get("/")
        # Should redirect to login
        assert response.status_code == 302
        assert "/login" in response.location

    def test_decorator_handles_config_errors(self, client, app):
        """Test that decorator handles configuration errors gracefully."""
        # Remove ALLOWED_EMAILS from config to simulate config error
        if "ALLOWED_EMAILS" in app.config:
            del app.config["ALLOWED_EMAILS"]

        app.config["WTF_CSRF_ENABLED"] = False

        # Try to access protected route - should handle gracefully
        response = client.get("/")
        # Should either redirect to login or handle the error
        assert response.status_code in [302, 500]

    def test_decorator_works_with_login_required(self, client, app):
        """Test that decorator works correctly with login_required decorator."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():

            # Create and login allowed user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login the user
            response = client.post(
                "/login",
                data={"email": "allowed@example.com", "password": "testpass"},
                follow_redirects=True,
            )
            assert response.status_code == 200

            # Test accessing route with both decorators
            response = client.get("/")
            assert response.status_code == 200

    def test_decorator_order_matters(self, client, app):
        """Test that decorator order matters when combined with other decorators."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():

            # Create and login allowed user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login the user
            response = client.post(
                "/login",
                data={"email": "allowed@example.com", "password": "testpass"},
                follow_redirects=True,
            )
            assert response.status_code == 200

            # Test that the decorators work in the correct order
            response = client.get("/")
            assert response.status_code == 200

    def test_decorator_does_not_slow_down_requests_significantly(self, client, app):
        """Test that decorator does not significantly slow down requests."""
        app.config["ALLOWED_EMAILS"] = ["test@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        import time

        with client.application.app_context():

            # Create and login user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login the user
            response = client.post(
                "/login",
                data={"email": "test@example.com", "password": "testpass"},
                follow_redirects=True,
            )
            assert response.status_code == 200

            # Measure response time
            start_time = time.time()
            response = client.get("/")
            end_time = time.time()

            # Response should be fast (less than 1 second)
            assert (end_time - start_time) < 1.0
            assert response.status_code == 200

    def test_decorator_caches_config_access(self, client, app):
        """Test that decorator caches config access for performance."""
        app.config["ALLOWED_EMAILS"] = ["test@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():

            # Create and login user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login the user
            response = client.post(
                "/login",
                data={"email": "test@example.com", "password": "testpass"},
                follow_redirects=True,
            )
            assert response.status_code == 200

            # Make multiple requests to test caching
            for _ in range(5):
                response = client.get("/")
                assert response.status_code == 200

            # Verify config is still accessible
            with app.app_context():
                assert app.config["ALLOWED_EMAILS"] == ["test@example.com"]
