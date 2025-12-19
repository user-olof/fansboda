import sys
import os
from pathlib import Path

# Add project root to Python path before any other imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pytest
from src import create_app, db
from src.models.user import Role, User
from flask_caching import Cache

cache = Cache()


@pytest.fixture(scope="session")
def app():
    """Create application for testing."""
    app = create_app("test")

    return app


@pytest.fixture(autouse=True)
def reset_database(app):
    """Reset the database before each test."""
    with app.app_context():
        # Drop all tables
        db.drop_all()
        # Recreate all tables
        db.create_all()
    yield
    # Optional: cleanup after test
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    """Create a test client for the Flask application."""

    app.config["WTF_CSRF_ENABLED"] = False

    return app.test_client()


@pytest.fixture
def client_with_csrf(app):
    """Create a test client with CSRF protection enabled."""
    # Configure for testing with CSRF enabled
    app.config["WTF_CSRF_ENABLED"] = True  # Enable CSRF for specific tests

    with app.test_client() as client:
        yield client


@pytest.fixture
def client_with_user(app):
    """Create a test client with a logged-in user."""
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["ALLOWED_EMAILS"] = ["test@example.com"]

    with app.test_client() as client:
        with app.app_context():

            # Create user
            user = User(email="test@example.com", role=Role.USER)
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Actually log in the user
            client.post(
                "/login", data={"email": "test@example.com", "password": "testpass"}
            )

            yield client


@pytest.fixture
def client_with_admin_user(app):
    """Create a test client with a logged-in admin user."""
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["ALLOWED_EMAILS"] = ["admin@example.com"]

    with app.test_client() as client:
        with app.app_context():
            user = User(email="admin@example.com", role=Role.ADMIN)
            user.password_hash = "adminpass"
            db.session.add(user)
            db.session.commit()

            client.post(
                "/login", data={"email": "admin@example.com", "password": "adminpass"}
            )
            yield client


@pytest.fixture
def auth(client):
    """Authentication helper fixture."""
    return AuthActions(client)


@pytest.fixture
def user():
    """Create a test user."""
    user = User(email="test@example.com", role=Role.USER)
    user.password_hash = "testpass"
    return user


@pytest.fixture
def admin_user():
    """Create a test admin user."""
    user = User(email="admin@example.com", role=Role.ADMIN)
    user.password_hash = "adminpass"
    return user


@pytest.fixture
def authenticated_user(client):
    """Create and save a test user to the database."""
    with client.application.app_context():
        user = User(email="test@example.com", role=Role.USER)
        user.password_hash = "testpass"
        db.session.add(user)
        db.session.commit()
        return user


@pytest.fixture
def authenticated_admin_user(client):
    """Create and save a test admin user to the database."""
    with client.application.app_context():
        user = User(email="admin@example.com", role=Role.ADMIN)
        user.password_hash = "adminpass"
        db.session.add(user)
        db.session.commit()
        return user


class AuthActions:
    """Helper class for authentication actions in tests."""

    def __init__(self, client):
        self._client = client

    def login(
        self, email="test@example.com", password="testpass", follow_redirects=True
    ):  # Changed from username to email
        return self._client.post(
            "/login",
            data={
                "email": email,
                "password": password,
            },  # Changed from username to email
            follow_redirects=follow_redirects,
        )

    def logout(self):
        return self._client.get("/logout", follow_redirects=True)


@pytest.fixture(autouse=True)
def clear_sessions(app):
    """Clear all sessions and caches before each test."""
    """ This is not needed as we are using NullCache for testing """
    # with app.app_context():

    # # Clear any other caches
    # if hasattr(app, "cache"):
    #     app.cache.clear()

    yield
