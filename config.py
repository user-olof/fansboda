import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


def get_database_uri(env_name="dev"):
    """Get database URI."""
    if env_name == "test":
        return "sqlite:///:memory:"
    else:
        return f"sqlite:///{os.path.join(basedir, 'database.db')}"


class TestConfig:
    """Test configuration."""
    SSL_CONTEXT = ("certificates/cert.pem", "certificates/key.pem")
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = get_database_uri("test")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True
    DEBUG = True
    TESTING = True
    PORT = 5000
    HOST = "localhost"
    CACHE_TYPE = "NullCache"
    CACHE_DEFAULT_TIMEOUT = 0
    CACHE_NO_NULL_WARNING = True
    WTF_CSRF_ENABLED = False
    LOGIN_DISABLED = True
    ALLOWED_EMAILS = ["test@example.com"]


class DevConfig:
    SSL_CONTEXT = ("certificates/cert.pem", "certificates/key.pem")
    SECRET_KEY = os.getenv("SECRET_KEY") or "dev-secret-key"
    SQLALCHEMY_DATABASE_URI = get_database_uri("dev")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True
    DEBUG = True
    PORT = 5000
    HOST = "localhost"
    ALLOWED_EMAILS = ["olof.thornell@gmail.com", "admin@test.com"]
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_NO_NULL_WARNING = True
    WTF_CSRF_ENABLED = True
    PERMANENT_SESSION_LIFETIME = 300


class ProdConfig:
    SSL_CONTEXT = None  # gunicorn and NGINX
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = get_database_uri("prod")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    DEBUG = False
    PORT = 8080
    HOST = "0.0.0.0"
    ALLOWED_EMAILS = ["olof.thornell@gmail.com"]
    CACHE_TYPE = "redis"
    CACHE_REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

    SESSION_COOKIE_SECURE = True  # ensure that cookies are only sent over HTTPS
    SESSION_COOKIE_HTTPONLY = True  # mitigate the risk of XSS attacks by ensuring that cookies cannot be easily stolen via malicious scripts
    REMEMBER_COOKIE_SECURE = True

    # Install Redis
    # sudo apt update
    # sudo apt install redis-server

    # # Start Redis service
    # sudo systemctl start redis-server
    # sudo systemctl enable redis-server

    # # Verify Redis is running
    # redis-cli ping
    WTF_CSRF_ENABLED = True
