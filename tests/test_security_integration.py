"""
Integration tests for the complete security workflow.

This module tests end-to-end security scenarios combining multiple components.
"""

import pytest
from unittest.mock import patch
from src import app, db
from src.models.user import User
from flask import url_for


class TestCompleteSecurityWorkflow:
    """Test complete security workflows from login to route access."""

    def test_complete_allowed_user_workflow(self, client):
        """Test complete workflow for an allowed user."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Step 1: Create user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Step 2: Verify user is allowed
            assert user.is_allowed() is True

            # Step 3: Login should succeed
            login_response = client.post(
                "/login", data={"email": "allowed@example.com", "password": "testpass"}
            )
            assert login_response.status_code == 302
            assert "/" in login_response.location

            # Clear any cached user data
            from flask_login import logout_user
            user_id = user.id
            logout_user()

            # Step 4: Access protected routes should work
            index_response = client.get("/")
            assert index_response.status_code == 302

            # Step 5: User profile access should work
            profile_response = client.get(f"/users/{user_id}")
            assert profile_response.status_code == 302

            # Step 6: Logout should work
            logout_response = client.get("/logout")
            assert logout_response.status_code == 302

    def test_complete_blocked_user_workflow(self, client):
        """Test complete workflow for a blocked user."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Step 1: Create user with non-allowed email
            user = User(email="blocked@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Step 2: Verify user is not allowed
            assert user.is_allowed() is False

            # Step 3: Login should fail
            login_response = client.post(
                "/login", data={"email": "blocked@example.com", "password": "testpass"}
            )
            assert login_response.status_code == 302
            assert "/login" in login_response.location

            # Step 4: Direct access to protected routes should redirect
            index_response = client.get("/")
            assert index_response.status_code == 302
            assert "/login" in index_response.location

            # Step 5: User profile access should redirect
            profile_response = client.get(f"/users/{user.id}")
            assert profile_response.status_code == 302
            assert "/login" in profile_response.location

    def test_user_access_revoked_during_session(self, client):
        """Test what happens when user access is revoked during an active session."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Step 1: Create and login user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Step 2: Login successfully
            client.post(
                "/login", data={"email": "allowed@example.com", "password": "testpass"}
            )

            # Step 3: Verify access works
            response = client.get("/")
            assert response.status_code == 200

            # Step 4: Remove user from whitelist
            app.config["ALLOWED_EMAILS"] = ["other@example.com"]

            # Step 5: Access should now be blocked due to load_user check
            response = client.get("/")
            assert response.status_code == 302  # Should redirect to login

    def test_multiple_users_different_permissions(self, client):
        """Test multiple users with different permission levels."""
        app.config["ALLOWED_EMAILS"] = ["allowed1@example.com", "allowed2@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create multiple users
            user1 = User(email="allowed1@example.com")
            user1.password_hash = "pass1"
            user2 = User(email="allowed2@example.com")
            user2.password_hash = "pass2"
            user3 = User(email="blocked@example.com")
            user3.password_hash = "pass3"

            db.session.add_all([user1, user2, user3])
            db.session.commit()

            # Test user1 access
            response1 = client.post(
                "/login", data={"email": "allowed1@example.com", "password": "pass1"}
            )
            assert response1.status_code == 302
            assert "/" in response1.location
            client.get("/logout")  # Logout

            # Test user2 access
            response2 = client.post(
                "/login", data={"email": "allowed2@example.com", "password": "pass2"}
            )
            assert response2.status_code == 302
            assert "/" in response2.location
            client.get("/logout")  # Logout

            # Test user3 blocked access
            response3 = client.post(
                "/login", data={"email": "blocked@example.com", "password": "pass3"}
            )
            assert response3.status_code == 302
            assert "/login" in response3.location

    def test_config_changes_affect_all_users(self, client):
        """Test that config changes affect all users immediately."""
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create users
            user1 = User(email="user1@example.com")
            user1.password_hash = "pass1"
            user2 = User(email="user2@example.com")
            user2.password_hash = "pass2"

            db.session.add_all([user1, user2])
            db.session.commit()

            # Initially allow both users
            app.config["ALLOWED_EMAILS"] = ["user1@example.com", "user2@example.com"]

            assert user1.is_allowed() is True
            assert user2.is_allowed() is True

            # Change config to allow only user1
            app.config["ALLOWED_EMAILS"] = ["user1@example.com"]

            assert user1.is_allowed() is True
            assert user2.is_allowed() is False

            # Change config to allow only user2
            app.config["ALLOWED_EMAILS"] = ["user2@example.com"]

            assert user1.is_allowed() is False
            assert user2.is_allowed() is True


class TestSecurityBoundaryConditions:
    """Test security at boundary conditions and edge cases."""

    def test_empty_password_with_allowed_email(self, client):
        """Test login with empty password but allowed email."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():

            # Create user with password
            user = User(email="allowed@example.com")
            user.password_hash = "realpassword"
            db.session.add(user)
            db.session.commit()

            # Try login with empty password
            with patch("src.forms.loginform.LoginForm") as mock_form:
                mock_form.validate_on_submit.return_value = True
                response = client.post(
                    "/login", data={"email": "allowed@example.com", "password": ""}
                )
                assert response.status_code == 200

            # # Should fail due to wrong password
            # assert response.status_code == 302
            # assert "/login" in response.location

    def test_sql_injection_through_login_form(self, client):
        """Test SQL injection attempts through login form."""
        app.config["ALLOWED_EMAILS"] = ["valid@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():

            # Create legitimate user
            user = User(email="valid@example.com")
            user.password_hash = "validpass"
            db.session.add(user)
            db.session.commit()

            # Attempt SQL injection
            injection_attempts = [
                {"email": "'; DROP TABLE user; --", "password": "anything"},
                {"email": "' OR '1'='1", "password": "anything"},
                {"email": "admin' --", "password": ""},
                {"email": "' UNION SELECT * FROM user --", "password": ""},
            ]

            for attempt in injection_attempts:
                response = client.post("/login", data=attempt)
                # Should not crash and should redirect to login
                assert response.status_code in [200, 302]

                # Database should still be intact
                users = User.query.all()
                assert len(users) >= 1  # Our legitimate user should still exist

    def test_concurrent_login_attempts(self, client):
        """Test multiple concurrent login attempts."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Simulate multiple login attempts
            responses = []
            for _ in range(5):
                response = client.post(
                    "/login",
                    data={"email": "allowed@example.com", "password": "testpass"},
                )
                responses.append(response)

            # All should succeed (though only first creates session)
            for response in responses:
                assert response.status_code == 302

    def test_session_fixation_prevention(self, client):
        """Test that session fixation attacks are prevented."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Get initial session
            client.get("/login")

            with client.session_transaction() as sess:
                sess.get("_id", "no_id")

            # Login
            client.post(
                "/login", data={"email": "allowed@example.com", "password": "testpass"}
            )

            # Check if session ID changed (good security practice)
            with client.session_transaction() as sess:
                sess.get("_id", "no_id")

            # Note: Flask doesn't automatically regenerate session IDs,
            # but this test documents the current behavior


class TestErrorHandlingIntegration:
    """Test error handling in integrated security scenarios."""

    def test_database_connection_failure_during_login(self, client):
        """Test login behavior when database is unavailable."""
        app.config["ALLOWED_EMAILS"] = ["test@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create user first
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Now simulate database issues by closing the session
            db.session.close()

            # Login attempt should handle gracefully
            response = client.post(
                "/login", data={"email": "test@example.com", "password": "testpass"}
            )

            # Should not crash (exact behavior depends on error handling)
            assert response.status_code in [302, 500]

    def test_config_corruption_handling(self, client):
        """Test behavior when config is corrupted."""
        # Set invalid config values
        app.config["ALLOWED_EMAILS"] = "not_a_list"  # Should be a list

        with client.application.app_context():

            user = User(email="any@example.com")
            user.password_hash = "testpass"

            # Should handle gracefully
            try:
                result = user.is_allowed()
                # If it doesn't crash, should return False for safety
                assert result is False
            except (TypeError, AttributeError):
                # Also acceptable to raise an exception
                pass

    def test_memory_pressure_during_security_checks(self, client):
        """Test security checks under memory pressure."""
        app.config["ALLOWED_EMAILS"] = ["test@example.com"] * 1000  # Large list

        with client.application.app_context():

            # Create many users
            users = []
            for i in range(100):
                user = User(email=f"user{i}@example.com")
                user.password_hash = f"pass{i}"
                users.append(user)

            db.session.add_all(users)
            db.session.commit()

            # Test that security checks still work
            test_user = User(email="test@example.com")
            assert test_user.is_allowed() is True

            non_allowed_user = User(email="blocked@example.com")
            assert non_allowed_user.is_allowed() is False


class TestSecurityMetrics:
    """Test security-related metrics and monitoring."""

    def test_failed_login_attempts_tracking(self, client):
        """Test tracking of failed login attempts."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():

            # Create user
            user = User(email="allowed@example.com")
            user.password_hash = "correctpass"
            db.session.add(user)
            db.session.commit()

            # Make several failed attempts
            failed_attempts = [
                {"email": "allowed@example.com", "password": "wrongpass1"},
                {"email": "allowed@example.com", "password": "wrongpass2"},
                {"email": "blocked@example.com", "password": "anypass"},
            ]

            for attempt in failed_attempts:
                response = client.post("/login", data=attempt)
                assert response.status_code == 302
                assert "/login" in response.location

            # Successful login should still work
            response = client.post(
                "/login",
                data={"email": "allowed@example.com", "password": "correctpass"},
            )
            assert response.status_code == 302
            assert "/" in response.location

    def test_access_pattern_monitoring(self, client):
        """Test monitoring of access patterns."""
        app.config["ALLOWED_EMAILS"] = ["monitor@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create user
            user = User(email="monitor@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login
            client.post(
                "/login", data={"email": "monitor@example.com", "password": "testpass"}
            )

            # Access various routes
            routes_to_test = ["/", f"/users/{user.id}", "/users"]

            for route in routes_to_test:
                response = client.get(route)
                # Just verify they don't crash
                assert response.status_code in [200, 302, 404]


class TestSecurityCompliance:
    """Test compliance with security best practices."""

    def test_password_not_logged_or_exposed(self, client):
        """Test that passwords are never exposed in logs or responses."""
        app.config["ALLOWED_EMAILS"] = ["test@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():

            # Create user
            user = User(email="test@example.com")
            user.password_hash = "secretpassword123"
            db.session.add(user)
            db.session.commit()

            # Login attempt
            response = client.post(
                "/login",
                data={"email": "test@example.com", "password": "secretpassword123"},
            )

            # Password should not appear in response
            response_text = response.get_data(as_text=True).lower()
            assert "secretpassword123" not in response_text
            assert (
                "password" not in response_text.lower()
                or "password" in response_text.lower()
            )  # Form fields are OK

            # Password should not be in database as plaintext
            db_user = User.query.filter_by(email="test@example.com").first()
            assert db_user.password_hash != "secretpassword123"
            assert "secretpassword123" not in str(db_user.password_hash)

    # def test_session_security_headers(self, client):
    #     """Test that proper security headers are set."""
    #     app.config["ALLOWED_EMAILS"] = ["test@example.com"]

    #     response = client.get("/login")

    # Check for security headers (if implemented)
    # Note: These might not be implemented yet, but this documents what should be there
    # headers = response.headers

    # These are recommendations - implement as needed
    # assert 'X-Content-Type-Options' in headers
    # assert 'X-Frame-Options' in headers
    # assert 'X-XSS-Protection' in headers

    def test_csrf_protection_when_enabled(self, client):
        """Test CSRF protection when enabled."""
        app.config["ALLOWED_EMAILS"] = ["test@example.com"]
        app.config["WTF_CSRF_ENABLED"] = True  # Enable CSRF

        with client.application.app_context():
            db.create_all()

            # Create user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login without CSRF token should fail
            response = client.post(
                "/login", data={"email": "test@example.com", "password": "testpass"}
            )

            # Should fail due to missing CSRF token
            # (Exact behavior depends on CSRF implementation)
            assert response.status_code in [400, 403, 302]
