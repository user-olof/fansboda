from datetime import timedelta
from dotenv import load_dotenv
import os


load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class TestConfig:
    SECRET_KEY = "test-secret-key"
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
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
    SECRET_KEY = (
        os.getenv("SECRET_KEY") or "dev-secret-key"
    )  # secret key needs to be set in .env file
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(basedir, "database.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = True
    DEBUG = True
    PORT = 5000
    HOST = "localhost"

    # Allowed email addresses
    ALLOWED_EMAILS = ["olof.thornell@gmail.com", "admin@test.com"]

    CACHE_TYPE = "SimpleCache"
    CACHE_DEFAULT_TIMEOUT = 300
    CACHE_NO_NULL_WARNING = True

    # Session timeout in seconds
    PERMANENT_SESSION_LIFETIME = 300 # 5 minutes


class ProdConfig:
    SECRET_KEY = os.getenv("SECRET_KEY")
    # secret key needs to be set in the .env file and uploaded to GCP
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{os.path.join(basedir, "database.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    DEBUG = False
    PORT = 8080
    HOST = "0.0.0.0"

    # Allowed email addresses
    ALLOWED_EMAILS = ["olof.thornell@gmail.com"]

    CACHE_TYPE = "redis"
    CACHE_REDIS_URL = "redis://localhost:6379"

    # Install Redis
    # sudo apt update
    # sudo apt install redis-server

    # # Start Redis service
    # sudo systemctl start redis-server
    # sudo systemctl enable redis-server

    # # Verify Redis is running
    # redis-cli ping
