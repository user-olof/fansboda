import pytest
from src import create_app, db
from src.models.user import User
from flask_caching import Cache

cache = Cache()


"""Create application for testing."""
# app = create_app("test") # This line is removed as per the new_code

# Explicitly configure cache for testing
# app.config["CACHE_TYPE"] = "NullCache" # This line is removed as per the new_code
# app.config["CACHE_DEFAULT_TIMEOUT"] = 0 # This line is removed as per the new_code
# app.config["CACHE_NO_NULL_WARNING"] = True # This line is removed as per the new_code

# Reinitialize cache with test config
# cache.init_app(app) # This line is removed as per the new_code


@pytest.fixture(scope="session")
def app():
    """Create application for testing."""
    app = create_app("test")

    # # Configure cache for testing
    # app.config["CACHE_TYPE"] = "NullCache"
    # app.config["CACHE_DEFAULT_TIMEOUT"] = 0
    # app.config["CACHE_NO_NULL_WARNING"] = True

    # # Reinitialize cache with test config
    # cache.init_app(app)

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
    # Ensure we're using test config
    # app.config.from_object("config.TestConfig")

    # Reinitialize cache with test config
    # cache.init_app(app)

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
            user = User(email="test@example.com")
            user.password_hash = "testpass"
            db.session.add(user)
            db.session.commit()

            # Actually log in the user
            client.post(
                "/login", data={"email": "test@example.com", "password": "testpass"}
            )

            yield client


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
def clear_sessions(app):
    """Clear all sessions and caches before each test."""
    ''' This is not needed as we are using NullCache for testing '''
    # with app.app_context():

    # # Clear any other caches
    # if hasattr(app, "cache"):
    #     app.cache.clear()

    yield


