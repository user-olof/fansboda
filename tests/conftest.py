import pytest
from src import app, db
from src.models.user import User


@pytest.fixture
def client():
    """Create a test client for the Flask application."""
    # Configure for testing
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False  # Disable CSRF for easier testing
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["LOGIN_DISABLED"] = False  # Ensure login is enabled for testing

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()


@pytest.fixture
def client_with_csrf():
    """Create a test client with CSRF protection enabled."""
    # Configure for testing with CSRF enabled
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = True  # Enable CSRF for specific tests
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["LOGIN_DISABLED"] = False

    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            yield client
            db.drop_all()


@pytest.fixture
def auth(client):
    """Authentication helper fixture."""
    return AuthActions(client)


@pytest.fixture
def user():
    """Create a test user."""
    user = User(username="testuser", email="test@example.com")
    user.set_password("testpass")
    return user


@pytest.fixture
def authenticated_user(client):
    """Create and save a test user to the database."""
    with client.application.app_context():
        user = User(username="testuser", email="test@example.com")
        user.set_password("testpass")
        db.session.add(user)
        db.session.commit()
        return user


class AuthActions:
    """Helper class for authentication actions in tests."""

    def __init__(self, client):
        self._client = client

    def login(
        self, email="test@example.com", password="testpass"
    ):  # Changed from username to email
        return self._client.post(
            "/login",
            data={
                "email": email,
                "password": password,
            },  # Changed from username to email
            follow_redirects=True,
        )

    def logout(self):
        return self._client.get("/logout", follow_redirects=True)
