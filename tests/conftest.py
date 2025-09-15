import pytest
from src import app, db
from src.models.user import User


@pytest.fixture(autouse=True)
def reset_database():
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
def client():
    """Create a test client for the Flask application."""
    # # Configure for testing
    # app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    # app.config["TESTING"] = True
    app.config["DEBUG"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    # app.config["SECRET_KEY"] = "test-secret-key"
    # app.config["LOGIN_DISABLED"] = False

    # # Disable all caching
    # app.config["CACHE_TYPE"] = "NullCache"
    # app.config["CACHE_DEFAULT_TIMEOUT"] = 0
    # app.config["CACHE_NO_NULL_WARNING"] = True
    # app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    # app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    #     "pool_pre_ping": True,
    #     "pool_recycle": 300,
    # }

    # # Disable template caching
    # app.jinja_env.cache = None

    # # Disable static file caching
    # app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0

    # # Disable user caching for tests
    # from src.models.user import load_user

    # def test_load_user(id):
    #     return User.query.get(int(id))

    # original_load_user = load_user
    # load_user = test_load_user

    with app.test_client() as client:
        yield client

    # Restore original load_user method
    # load_user = original_load_user


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
        yield client


@pytest.fixture
def client_with_user():
    """Create a test client with a logged-in user."""
    # Configure for testing
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["SECRET_KEY"] = "test-secret-key"
    app.config["LOGIN_DISABLED"] = False

    app.config["ALLOWED_EMAILS"] = ["test@example.com"]

    with app.test_client() as client:
        with app.app_context():
            db.create_all()

            # Create user
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Actually log in the user
            client.post(
                "/login", data={"email": "test@example.com", "password": "testpass"}
            )

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
    user.password_hash = "testpass"
    return user


@pytest.fixture
def authenticated_user(client):
    """Create and save a test user to the database."""
    with client.application.app_context():
        user = User(email="test@example.com")
        user.password_hash = "testpass"
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


@pytest.fixture(autouse=True)
def clear_sessions():
    """Clear all sessions and caches before each test."""
    with app.app_context():

        # Clear any other caches
        if hasattr(app, "cache"):
            app.cache.clear()

    yield

    with app.app_context():

        # Clear any other caches
        if hasattr(app, "cache"):
            app.cache.clear()
