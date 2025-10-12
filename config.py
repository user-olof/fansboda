import os
from datetime import timedelta
from dotenv import load_dotenv
from cachelib.file import FileSystemCache

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


def get_database_uri(env_name="dev"):
    """Get database URI."""
    if env_name == "test":
        return "sqlite:///:memory:"
    elif env_name == "dev":
        # Use Neon serverless PostgreSQL
        neon_database_url = os.getenv("DATABASE_MAIN_URL")
        if not neon_database_url:
            raise ValueError(
                "DATABASE_URL environment variable must be set for development. "
                "Get your connection string from https://neon.tech"
            )
        return neon_database_url
    elif env_name == "prod":
        neon_database_url = os.getenv("DATABASE_PROD_URL")
        if not neon_database_url:
            raise ValueError(
                "DATABASE_URL environment variable must be set for production. "
                "Get your connection string from https://neon.tech"
            )
        return neon_database_url
    else:
        raise ValueError(f"Invalid environment name: {env_name}")


class TestConfig:
    """Test configuration."""

    FLASK_APP = "app.py"
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

    # SESSION_COOKIE_SECURE = True  # ensure that cookies are only sent over HTTPS
    # SESSION_COOKIE_HTTPONLY = True  # mitigate the risk of XSS attacks by ensuring that cookies cannot be easily stolen via malicious scripts
    # REMEMBER_COOKIE_SECURE = True
    # REMEMBER_COOKIE_DURATION = 300  # 5 minutes
    SESSION_COOKIE_NAME = "session"
    SESSION_COOKIE_ENABLED = True

    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = "cache"
    SESSION_FILE_THRESHOLD = 500
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_CLEANUP_N_REQUESTS = 10


class DevConfig:
    FLASK_APP = "app.py"
    SSL_CONTEXT = ("certificates/cert.pem", "certificates/key.pem")
    SECRET_KEY = os.getenv("SECRET_KEY") or "dev-secret-key"
    SQLALCHEMY_DATABASE_URI = get_database_uri("dev")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True
    DEBUG = True
    PORT = 5000
    HOST = "localhost"
    ALLOWED_EMAILS = os.getenv("ALLOWED_EMAILS", "").split(",")
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_NO_NULL_WARNING = True
    WTF_CSRF_ENABLED = True
    PERMANENT_SESSION_LIFETIME = 300
    REMEMBER_COOKIE_DURATION = 300  # 5 minutes

    SESSION_TYPE = "cachelib"
    SESSION_SERIALIZATION_FORMAT = "json"
    SESSION_CACHELIB = FileSystemCache(threshold=500, cache_dir="./flask_session")
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_CLEANUP_N_REQUESTS = 100


class ProdConfig:
    SSL_CONTEXT = None  # gunicorn and NGINX
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = get_database_uri("prod")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False

    # PostgreSQL connection pool settings for Neon
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_size": 5,
        "max_overflow": 2,
        "pool_timeout": 30,
        "pool_recycle": 1800,  # Recycle connections after 30 minutes
        "pool_pre_ping": True,  # Verify connections before using
    }

    DEBUG = False
    PORT = 8080
    HOST = "0.0.0.0"
    ALLOWED_EMAILS = ["olof.thornell@gmail.com"]

    # Use SimpleCache instead of Redis (cost saving)
    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_NO_NULL_WARNING = True

    # Use filesystem for sessions (cost saving)
    SESSION_TYPE = "filesystem"
    SESSION_FILE_DIR = "/tmp/flask_session"
    SESSION_PERMANENT = False
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)

    SESSION_COOKIE_SECURE = True  # ensure that cookies are only sent over HTTPS
    SESSION_COOKIE_HTTPONLY = True  # mitigate the risk of XSS attacks by ensuring that cookies cannot be easily stolen via malicious scripts
    REMEMBER_COOKIE_SECURE = True
    REMEMBER_COOKIE_DURATION = 300  # 5 minutes

    WTF_CSRF_ENABLED = True
