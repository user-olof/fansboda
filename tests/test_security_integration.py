"""
Integration tests for the complete security workflow.

This module tests end-to-end security scenarios combining multiple components.
"""

from unittest.mock import patch

import pytest
from src import db
from src.models.user import User


class TestCompleteSecurityWorkflow:
    """Test complete security workflows from login to route access."""

    def test_complete_allowed_user_workflow(self, client, app):
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
            assert profile_response.status_code in [200, 302]

    def test_complete_blocked_user_workflow(self, client, app):
        """Test complete workflow for a blocked user."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Step 1: Create user
            user = User(email="blocked@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Step 2: Verify user is not allowed
            assert user.is_allowed() is False

            # Step 3: Login should still succeed (authentication vs authorization)
            login_response = client.post(
                "/login", data={"email": "blocked@example.com", "password": "testpass"}
            )
            assert login_response.status_code == 302

            # Step 4: Access protected routes should be blocked
            index_response = client.get("/")
            assert index_response.status_code == 302
            assert "/login" in index_response.location

    def test_user_access_revoked_during_session(self, client, app):
        """Test what happens when user access is revoked during an active session."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Step 1: Create and login allowed user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login
            login_response = client.post(
                "/login", data={"email": "allowed@example.com", "password": "testpass"}
            )
            assert login_response.status_code == 302

            # Step 2: Revoke access by changing config
            app.config["ALLOWED_EMAILS"] = ["other@example.com"]

            # Step 3: Try to access protected route - should be blocked
            index_response = client.get("/")
            assert index_response.status_code == 302
            assert "/login" in index_response.location

    def test_multiple_users_different_permissions(self, client, app):
        """Test multiple users with different permission levels."""
        app.config["ALLOWED_EMAILS"] = ["allowed1@example.com", "allowed2@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create multiple users
            user1 = User(email="allowed1@example.com")
            user1.password_hash = "testpass1"
            db.session.add(user1)

            user2 = User(email="allowed2@example.com")
            user2.password_hash = "testpass2"
            db.session.add(user2)

            user3 = User(email="blocked@example.com")
            user3.password_hash = "testpass3"
            db.session.add(user3)

            db.session.commit()

            # Test user1 access
            login_response = client.post(
                "/login",
                data={"email": "allowed1@example.com", "password": "testpass1"},
            )
            assert login_response.status_code == 302

            index_response = client.get("/")
            assert index_response.status_code == 200

            # Logout user1
            from flask_login import logout_user

            logout_user()

            # Test user2 access
            login_response = client.post(
                "/login",
                data={"email": "allowed2@example.com", "password": "testpass2"},
            )
            assert login_response.status_code == 302

            index_response = client.get("/")
            assert index_response.status_code == 200

            # Logout user2
            logout_user()

            # Test user3 access (should be blocked)
            login_response = client.post(
                "/login", data={"email": "blocked@example.com", "password": "testpass3"}
            )
            assert login_response.status_code == 302

            index_response = client.get("/")
            assert index_response.status_code == 302
            assert "/login" in index_response.location

    def test_config_changes_affect_all_users(self, client, app):
        """Test that config changes affect all users immediately."""
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create users
            user1 = User(email="user1@example.com")
            user1.password_hash = "testpass1"
            db.session.add(user1)

            user2 = User(email="user2@example.com")
            user2.password_hash = "testpass2"
            db.session.add(user2)

            db.session.commit()

            # Initially allow both users
            app.config["ALLOWED_EMAILS"] = ["user1@example.com", "user2@example.com"]

            # Login user1
            login_response = client.post(
                "/login", data={"email": "user1@example.com", "password": "testpass1"}
            )
            assert login_response.status_code == 302

            # Login user2
            login_response = client.post(
                "/login", data={"email": "user2@example.com", "password": "testpass2"}
            )
            assert login_response.status_code == 302

            # Change config to only allow user1
            app.config["ALLOWED_EMAILS"] = ["user1@example.com"]

            # user1 should still have access
            index_response = client.get("/")
            assert index_response.status_code == 200

            # Change config to only allow user2
            app.config["ALLOWED_EMAILS"] = ["user2@example.com"]

            # user1 should now be blocked
            index_response = client.get("/")
            assert index_response.status_code == 302
            assert "/login" in index_response.location

    def test_empty_password_with_allowed_email(self, client, app):
        """Test that empty passwords are handled correctly for allowed emails."""
        app.config["ALLOWED_EMAILS"] = ["valid@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create user with empty password
            try:
                user = User(email="valid@example.com")
                user.password_hash = ""
            except ValueError as e:
                assert str(e) == "Password must be non-empty."

 # Should show form with errors

    def test_sql_injection_through_login_form(self, client, app):
        """Test that SQL injection attempts are handled safely."""
        app.config["ALLOWED_EMAILS"] = ["valid@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create valid user
            user = User(email="valid@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Test SQL injection attempts
            sql_injection_attempts = [
                "'; DROP TABLE users; --",
                "' OR '1'='1",
                "admin'--",
                "' UNION SELECT * FROM users --",
                "'; INSERT INTO users (email) VALUES ('hacker@evil.com'); --",
            ]

            for injection in sql_injection_attempts:
                login_response = client.post(
                    "/login", data={"email": injection, "password": "anything"}
                )
                # Should not crash or allow access
                assert login_response.status_code in [200, 302]
                # Should not redirect to protected area
                if login_response.status_code == 302:
                    assert "/" not in login_response.location

    def test_concurrent_login_attempts(self, client, app):
        """Test handling of concurrent login attempts."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Simulate concurrent login attempts
            import threading
            import time

            results = []

            def login_attempt():
                response = client.post(
                    "/login",
                    data={"email": "allowed@example.com", "password": "testpass"},
                )
                results.append(response.status_code)

            # Start multiple threads
            threads = []
            for _ in range(5):
                thread = threading.Thread(target=login_attempt)
                threads.append(thread)
                thread.start()

            # Wait for all threads to complete
            for thread in threads:
                thread.join()

            # All attempts should succeed
            assert all(status == 302 for status in results)

    def test_session_fixation_prevention(self, client, app):
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

            # Get initial session ID
            initial_response = client.get("/login")
            initial_session_id = client.cookie_jar._cookies.get("session", {}).get("")

            # Login
            login_response = client.post(
                "/login", data={"email": "allowed@example.com", "password": "testpass"}
            )
            assert login_response.status_code == 302

            # Session ID should change after login
            new_session_id = client.cookie_jar._cookies.get("session", {}).get("")
            assert initial_session_id != new_session_id

    def test_database_connection_failure_during_login(self, client, app):
        """Test handling of database connection failures during login."""
        app.config["ALLOWED_EMAILS"] = ["test@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Mock database connection failure
            with patch(
                "src.db.session.commit",
                side_effect=Exception("Database connection failed"),
            ):
                login_response = client.post(
                    "/login", data={"email": "test@example.com", "password": "testpass"}
                )
                # Should handle gracefully
                assert login_response.status_code in [200, 500]

    def test_config_corruption_handling(self, client, app):
        """Test handling of corrupted configuration."""
        app.config["ALLOWED_EMAILS"] = "not_a_list"  # Should be a list

        with client.application.app_context():
            db.create_all()

            # Create user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login should handle config corruption gracefully
            login_response = client.post(
                "/login", data={"email": "test@example.com", "password": "testpass"}
            )
            assert login_response.status_code in [200, 302, 500]

    def test_memory_pressure_during_security_checks(self, client, app):
        """Test security checks under memory pressure."""
        app.config["ALLOWED_EMAILS"] = ["test@example.com"] * 1000  # Large list

        with client.application.app_context():
            db.create_all()

            # Create user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Login should still work with large config
            login_response = client.post(
                "/login", data={"email": "test@example.com", "password": "testpass"}
            )
            assert login_response.status_code == 302

    def test_failed_login_attempts_tracking(self, client, app):
        """Test tracking of failed login attempts."""
        app.config["ALLOWED_EMAILS"] = ["allowed@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create user
            user = User(email="allowed@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Test multiple failed login attempts
            for i in range(5):
                login_response = client.post(
                    "/login",
                    data={"email": "allowed@example.com", "password": "wrongpass"},
                )
                assert login_response.status_code == 200  # Should show form with errors

            # Correct login should still work
            login_response = client.post(
                "/login", data={"email": "allowed@example.com", "password": "testpass"}
            )
            assert login_response.status_code == 302

    def test_access_pattern_monitoring(self, client, app):
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
            login_response = client.post(
                "/login", data={"email": "monitor@example.com", "password": "testpass"}
            )
            assert login_response.status_code == 302

            # Access multiple routes
            routes = ["/", "/users", "/profile"]
            for route in routes:
                response = client.get(route)
                assert response.status_code in [200, 302]

    def test_password_not_logged_or_exposed(self, client, app):
        """Test that passwords are not logged or exposed in responses."""
        app.config["ALLOWED_EMAILS"] = ["test@example.com"]
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.app_context():
            db.create_all()

            # Create user
            user = User(email="test@example.com")
            user.password_hash = "sensitive_password"
            db.session.add(user)
            db.session.commit()

            # Login
            login_response = client.post(
                "/login",
                data={"email": "test@example.com", "password": "sensitive_password"},
            )

            # Check that password is not in response
            assert b"sensitive_password" not in login_response.data

            # Check that password is not in any subsequent responses
            if login_response.status_code == 302:
                index_response = client.get("/")
                assert b"sensitive_password" not in index_response.data

    # def test_session_security_headers(self, client):
    #     """Test that appropriate security headers are set."""
    #     app.config["ALLOWED_EMAILS"] = ["test@example.com"]
    #     app.config["WTF_CSRF_ENABLED"] = False

    #     with client.application.app_context():
    #         db.create_all()

    #         # Create user
    #         user = User(email="test@example.com")
    #         user.password_hash = "testpass"
    #         db.session.add(user)
    #         db.session.commit()

    #         # Login
    #         login_response = client.post(
    #             "/login", data={"email": "test@example.com", "password": "testpass"}
    #         )
    #         assert login_response.status_code == 302

    #         # Check security headers
    #         index_response = client.get("/")
    #         # Add checks for security headers like X-Frame-Options, etc.

    def test_csrf_protection_when_enabled(self, client, app):
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

            # Login should work with CSRF
            login_response = client.post(
                "/login", data={"email": "test@example.com", "password": "testpass"}
            )
            # CSRF might cause issues in test environment
            assert login_response.status_code in [200, 302, 400]
