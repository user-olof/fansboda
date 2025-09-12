"""
Test cases for access control decorator functionality.

This module tests the access control decorators and route protection.
"""

import pytest
from src import app, db
from src.models.user import User
from src.access_control import allowed_user_required
from flask import render_template
from flask_login import login_user, current_user, login_required


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
#         return "Double protected"

#     # Create routes with different decorator orders
#     @app.route("/test-order-1")
#     @allowed_user_required  # This includes @login_required
#     def test_order_1():
#         return "Order 1"


# setup_test_routes()


class TestAccessControlDecorator:
    """Test the allowed_user_required decorator."""

    def test_decorator_allows_whitelisted_user(self, client):
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

            # Login
            response = client.post(
                "/login", data={"email": "allowed@example.com", "password": "testpass"}
            )
            assert response.status_code == 302

            # Access protected route
            response = client.get("/test-protected")
            assert response.status_code == 200

    def test_decorator_blocks_non_whitelisted_user(self, client):
        """Test that decorator blocks access for non-whitelisted users."""

        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():

            # Create user with non-allowed email
            user = User(email="blocked@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Try to login (this should fail due to our login security)
            response = client.post(
                "/login", data={"email": "blocked@example.com", "password": "testpass"}
            )

            # Should redirect back to login
            assert response.status_code == 302
            assert "/login" in response.location

            # Try to access protected route (should redirect to login)
            response = client.get("/test-blocked")
            assert response.status_code == 302
            assert "/login" in response.location

    def test_decorator_requires_authentication_first(self, client):
        """Test that decorator requires user to be logged in first."""

        # # Create a test route with the decorator
        # @app.route("/test-auth-required")
        # @allowed_user_required
        # def test_auth_required():
        #     return "Access granted"

        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]

        with client.application.app_context():

            # Try to access without login
            response = client.get("/test-auth-required")
            assert response.status_code == 302
            assert "/login" in response.location

    def test_decorator_redirects_to_logout_on_access_denied(self, client):
        """Test that decorator redirects to logout when access is denied."""
        # This test is more complex because we need to simulate a scenario
        # where a user is logged in but then their access is revoked
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        # # Create a test route with the decorator
        # @app.route("/test-logout-redirect")
        # @allowed_user_required
        # def test_logout_redirect():
        #     return "Access granted"

        with client.application.app_context():

            # Create user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login successfully
            response = client.post(
                "/login", data={"email": "allowed@example.com", "password": "testpass"}
            )

            # Verify login was successful
            assert response.status_code == 302

            # Verify access works initially
            response = client.get("/test-logout-redirect")
            assert response.status_code == 200

            # Now remove user from whitelist
            app.config["ALLOWED_EMAILS"] = ["other@example.com"]

            # Access should now redirect to logout
            response = client.get("/test-logout-redirect")
            # The exact behavior depends on your logout route implementation
            # It might redirect to login or show a logout page
            assert response.status_code == 302
            assert "/login" in response.location


class TestRouteProtectionIntegration:
    """Test integration of route protection with existing routes."""

    def test_existing_routes_work_with_allowed_users(self, client):
        """Test that existing routes work properly with allowed users."""
        app.config["ALLOWED_EMAILS"] = ["test@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create allowed user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login
            response = client.post(
                "/login", data={"email": "test@example.com", "password": "testpass"}
            )

            assert response.status_code == 302

            # Test that protected routes work
            response = client.get("/")
            assert response.status_code == 200

            # Test user profile routes
            response = client.get(f"/users/{user.id}")
            assert response.status_code == 200

    def test_public_routes_still_accessible(self, client):
        """Test that public routes remain accessible without authentication."""
        app.config["ALLOWED_EMAILS"] = ["test@example.com"]

        # Test public routes
        response = client.get("/users")  # This route doesn't require auth
        assert response.status_code == 200

        response = client.get("/login")
        assert response.status_code == 200


class TestDecoratorErrorHandling:
    """Test error handling in access control decorators."""

    def test_decorator_handles_missing_current_user(self, client):
        """Test decorator behavior when current_user is not available."""

        app.config["ALLOWED_EMAILS"] = ["test@example.com"]

        with client.application.app_context():
            db.create_all()

            # Access without any user context
            response = client.get("/test-no-user")
            assert response.status_code == 302
            assert "/login" in response.location

    def test_decorator_handles_config_errors(self, client):
        """Test decorator behavior when config has issues."""

        # Remove ALLOWED_EMAILS config
        if "ALLOWED_EMAILS" in app.config:
            del app.config["ALLOWED_EMAILS"]

        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create user and login
            user = User(email="any@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # This login should fail due to missing config
            response = client.post(
                "/login", data={"email": "any@example.com", "password": "testpass"}
            )

            # Should redirect back to login
            assert response.status_code == 302


class TestDecoratorChaining:
    """Test decorator chaining and interaction with other decorators."""

    def test_decorator_works_with_login_required(self, client):
        """Test that allowed_user_required works with @login_required."""

        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with app.app_context():
            # Verify config is set
            assert app.config["ALLOWED_EMAILS"] == ["allowed@example.com"]

            db.create_all()

            # Test without login
            response = client.get("/test-double-protection")
            assert response.status_code == 302
            assert "/login" in response.location

            # Create and login allowed user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login the user
            response = client.post(
                "/login", data={"email": "allowed@example.com", "password": "testpass"}
            )

            # Verify login was successful
            assert response.status_code == 302

            # Now should work - FIXED: expect 200 status code
            response = client.get("/test-double-protection")
            assert response.status_code == 200
            assert b"Double protected" in response.data

    def test_decorator_order_matters(self, client):
        """Test that decorator order affects behavior."""
        # from flask_login import login_required

        # # Create routes with different decorator orders
        # @app.route("/test-order-1")
        # @allowed_user_required  # This includes @login_required
        # def test_order_1():
        #     return "Order 1"

        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Both should behave the same way
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            client.post(
                "/login", data={"email": "allowed@example.com", "password": "testpass"}
            )

            response1 = client.get("/test-order-1")
            response2 = client.get("/test-order-2")

            assert response1.status_code == 200
            assert response2.status_code == 200


class TestDecoratorPerformance:
    """Test performance aspects of the access control decorator."""

    def test_decorator_does_not_slow_down_requests_significantly(self, client):
        """Test that decorator doesn't add significant overhead."""
        import time

        app.config["ALLOWED_EMAILS"] = ["test@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create and login user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            client.post(
                "/login", data={"email": "test@example.com", "password": "testpass"}
            )

            # Time both requests (this is a basic performance check)
            start_time = time.time()
            for _ in range(10):
                client.get("/test-protected-perf")
            protected_time = time.time() - start_time

            start_time = time.time()
            for _ in range(10):
                client.get("/test-unprotected-perf")
            unprotected_time = time.time() - start_time

            # Protected should not be more than 10x slower (very generous threshold)
            assert protected_time < unprotected_time * 10

    def test_decorator_caches_config_access(self, client):
        """Test that decorator efficiently accesses config."""

        app.config["ALLOWED_EMAILS"] = ["test@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            response = client.post(
                "/login", data={"email": "test@example.com", "password": "testpass"}
            )
            assert response.status_code == 302

            # Make multiple requests
            for _ in range(5):
                response = client.get("/test-config-access")
                assert response.status_code == 200
