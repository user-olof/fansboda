"""
Test cases for email whitelist security functionality.

This module tests the new security features including:
- Email whitelist validation
- Login security checks
- Route access control
- Configuration-based security
"""

import pytest
from src import app, db
from src.models.user import User, load_user
from flask import url_for


class TestEmailWhitelist:
    """Test email whitelist functionality."""

    def test_user_is_allowed_with_whitelisted_email(self, client):
        """Test that users with whitelisted emails are allowed."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com", "test@example.com"]

        with client.application.app_context():
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is True

    def test_user_is_allowed_with_non_whitelisted_email(self, client):
        """Test that users with non-whitelisted emails are not allowed."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]

        with client.application.app_context():
            user = User(email="blocked@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_empty_whitelist(self, client):
        """Test behavior when ALLOWED_EMAILS is empty."""
        app.config["ALLOWED_EMAILS"] = []

        with client.application.app_context():
            user = User(email="any@example.com")
            user.password_hash = "testpass"

            assert user.is_allowed() is False

    def test_user_is_allowed_with_missing_config(self, client):
        """Test behavior when ALLOWED_EMAILS config is missing."""
        # Remove the config key if it exists
        if "ALLOWED_EMAILS" in app.config:
            del app.config["ALLOWED_EMAILS"]

        with client.application.app_context():
            user = User(email="any@example.com")
            user.password_hash = "testpass"

            # Should return False when config is missing (default behavior)
            assert user.is_allowed() is False

    def test_user_is_allowed_case_sensitivity(self, client):
        """Test that email comparison is case sensitive."""
        app.config["ALLOWED_EMAILS"] = ["Test@Example.com"]

        with client.application.app_context():
            user_lower = User(email="test@example.com")
            user_upper = User(email="TEST@EXAMPLE.COM")
            user_mixed = User(email="Test@Example.com")

            # Only exact case match should be allowed
            assert user_lower.is_allowed() is False
            assert user_upper.is_allowed() is False
            assert user_mixed.is_allowed() is True


class TestLoadUserSecurity:
    """Test load_user function security checks."""

    def test_load_user_returns_allowed_user(self, client):
        """Test that load_user returns user when they are allowed."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]

        with client.application.app_context():
            db.create_all()

            # Create and save user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Test load_user function
            loaded_user = load_user(user.id)
            assert loaded_user is not None
            assert loaded_user.email == "allowed@example.com"

    def test_load_user_returns_none_for_blocked_user(self, client):
        """Test that load_user returns None when user is not allowed."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]

        with client.application.app_context():
            db.create_all()

            # Create and save user with non-allowed email
            user = User(email="blocked@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Test load_user function
            loaded_user = load_user(user.id)
            assert loaded_user is None

    def test_load_user_returns_none_for_nonexistent_user(self, client):
        """Test that load_user returns None for non-existent user ID."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]

        with client.application.app_context():
            db.create_all()

            # Test with non-existent user ID
            loaded_user = load_user(99999)
            assert loaded_user is None


class TestLoginSecurity:
    """Test login route security functionality."""

    def test_login_success_with_allowed_email(self, client):
        """Test successful login with allowed email."""
        # Configure test settings
        client.application.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        client.application.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create allowed user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

        # Attempt login (outside the explicit context)
        response = client.post(
            "/login", data={"email": "allowed@example.com", "password": "testpass"}
        )

        # Should redirect to index on success
        assert response.status_code == 302
        assert "/" in response.location

    def test_login_blocked_with_non_allowed_email(self, client):
        """Test that login is blocked for non-allowed email."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create user with non-allowed email
            user = User(email="blocked@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Attempt login
            response = client.post(
                "/login", data={"email": "blocked@example.com", "password": "testpass"}
            )

            # Should redirect back to login with error
            assert response.status_code == 302
            assert "/login" in response.location

    def test_login_blocked_with_correct_password_but_blocked_email(self, client):
        """Test that even with correct password, blocked emails can't login."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create user with non-allowed email but valid password
            user = User(email="blocked@example.com")
            user.password_hash = "correctpassword"
            db.session.add(user)
            db.session.commit()

            # Attempt login with correct credentials
            response = client.post(
                "/login",
                data={"email": "blocked@example.com", "password": "correctpassword"},
            )

            # Should still be blocked
            assert response.status_code == 302
            assert "/login" in response.location

    def test_login_with_invalid_password_and_allowed_email(self, client):
        """Test login failure with wrong password but allowed email."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create allowed user
            user = User(email="allowed@example.com")
            user.password_hash = "correctpass"
            db.session.add(user)
            db.session.commit()

            # Attempt login with wrong password
            response = client.post(
                "/login", data={"email": "allowed@example.com", "password": "wrongpass"}
            )

            # Should redirect back to login
            assert response.status_code == 302
            assert "/login" in response.location


class TestRouteAccess:
    """Test route access with whitelist security."""

    def test_index_access_with_allowed_user(self, client):
        """Test that allowed users can access protected routes."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create and login allowed user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login
            client.post(
                "/login", data={"email": "allowed@example.com", "password": "testpass"}
            )

            # Access protected route
            response = client.get("/")
            assert response.status_code == 200

    def test_index_redirect_for_unauthenticated_user(self, client):
        """Test that unauthenticated users are redirected to login."""
        response = client.get("/")
        assert response.status_code == 302
        # Should redirect to login
        assert "/login" in response.location

    def test_users_route_accessible_without_auth(self, client):
        """Test that /users route is accessible without authentication."""
        # Note: This tests current behavior - you might want to change this
        response = client.get("/users")
        assert response.status_code == 200


class TestConfigurationScenarios:
    """Test different configuration scenarios."""

    def test_dev_config_allows_test_email(self, client):
        """Test that development config includes test email."""
        # Simulate dev config
        app.config["ALLOWED_EMAILS"] = ["olof.thornell@gmail.com", "test@example.com"]

        with client.application.app_context():
            test_user = User(email="test@example.com")
            prod_user = User(email="olof.thornell@gmail.com")

            assert test_user.is_allowed() is True
            assert prod_user.is_allowed() is True

    def test_prod_config_blocks_test_email(self, client):
        """Test that production config blocks test email."""
        # Simulate prod config
        app.config["ALLOWED_EMAILS"] = ["olof.thornell@gmail.com"]

        with client.application.app_context():
            test_user = User(email="test@example.com")
            prod_user = User(email="olof.thornell@gmail.com")

            assert test_user.is_allowed() is False
            assert prod_user.is_allowed() is True

    def test_empty_allowed_emails_blocks_all(self, client):
        """Test that empty ALLOWED_EMAILS blocks all users."""
        app.config["ALLOWED_EMAILS"] = []

        with client.application.app_context():
            user1 = User(email="any@example.com")
            user2 = User(email="another@example.com")

            assert user1.is_allowed() is False
            assert user2.is_allowed() is False


class TestSecurityEdgeCases:
    """Test edge cases and potential security issues."""

    def test_sql_injection_in_email_field(self, client):
        """Test that SQL injection attempts in email are handled safely."""
        app.config["ALLOWED_EMAILS"] = ["valid@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Attempt login with SQL injection
            response = client.post(
                "/login",
                data={"email": "'; DROP TABLE user; --", "password": "anything"},
            )

            # Should not crash and should redirect to login
            assert response.status_code == 302

            # Database should still be intact
            users = User.query.all()
            # Should not crash when querying

    def test_xss_in_email_field(self, client):
        """Test that XSS attempts in email are handled safely."""
        app.config["ALLOWED_EMAILS"] = ["valid@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Attempt login with XSS
            response = client.post(
                "/login",
                data={"email": "<script>alert('xss')</script>", "password": "anything"},
            )

            # Should not crash and should redirect to login
            assert response.status_code == 302

    def test_very_long_email(self, client):
        """Test handling of extremely long email addresses."""
        app.config["ALLOWED_EMAILS"] = ["valid@example.com"]

        with client.application.app_context():
            # Create user with very long email
            long_email = "a" * 1000 + "@example.com"
            user = User(email=long_email)

            # Should handle gracefully
            result = user.is_allowed()
            assert result is False

    def test_unicode_in_email(self, client):
        """Test handling of unicode characters in email."""
        app.config["ALLOWED_EMAILS"] = ["tëst@exämple.com", "valid@example.com"]

        with client.application.app_context():
            unicode_user = User(email="tëst@exämple.com")
            normal_user = User(email="valid@example.com")

            assert unicode_user.is_allowed() is True
            assert normal_user.is_allowed() is True

    def test_none_email_handling(self, client):
        """Test handling of None email values."""
        app.config["ALLOWED_EMAILS"] = ["valid@example.com"]

        with client.application.app_context():
            # This should be prevented by database constraints,
            # but test the is_allowed method's robustness
            user = User()
            user.email = None

            # Should not crash
            try:
                result = user.is_allowed()
                # If it doesn't crash, it should return False
                assert result is False
            except (TypeError, AttributeError):
                # Also acceptable if it raises an exception
                pass


class TestSessionSecurity:
    """Test session-based security functionality."""

    def test_session_invalidated_when_user_removed_from_whitelist(self, client):
        """Test that sessions are invalidated when user is removed from whitelist."""
        # This is a conceptual test - in practice, you'd need to implement
        # real-time whitelist checking or session invalidation
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create and login user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login successfully
            login_response = client.post(
                "/login", data={"email": "allowed@example.com", "password": "testpass"}
            )
            assert login_response.status_code == 302

            # Access should work
            response = client.get("/")
            assert response.status_code == 200

            # Simulate removing user from whitelist
            app.config["ALLOWED_EMAILS"] = ["other@example.com"]

            # Access should now be blocked (due to load_user check)
            response = client.get("/")
            assert response.status_code == 302  # Redirect to login

    def test_concurrent_sessions_with_mixed_permissions(self, client):
        """Test behavior with multiple sessions and changing permissions."""
        # This tests the load_user function's real-time checking
        app.config["ALLOWED_EMAILS"] = ["user1@example.com", "user2@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create two users
            user1 = User(email="user1@example.com")
            user1.password_hash = "pass1"
            user2 = User(email="user2@example.com")
            user2.password_hash = "pass2"

            db.session.add(user1)
            db.session.add(user2)
            db.session.commit()

            # Test that both users can be loaded
            loaded_user1 = load_user(user1.id)
            loaded_user2 = load_user(user2.id)

            assert loaded_user1 is not None
            assert loaded_user2 is not None

            # Remove user2 from whitelist
            app.config["ALLOWED_EMAILS"] = ["user1@example.com"]

            # Now only user1 should be loadable
            loaded_user1 = load_user(user1.id)
            loaded_user2 = load_user(user2.id)

            assert loaded_user1 is not None
            assert loaded_user2 is None
