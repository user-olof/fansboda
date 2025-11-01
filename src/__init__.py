# src/__init__.py
import sys
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
from flask_talisman import Talisman
from flask_cors import CORS
import flask_bcrypt
from flask_migrate import Migrate
from dotenv import load_dotenv


# x
load_dotenv()

# Configure Flask to look for templates in the parent directory
basedir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(os.path.dirname(basedir), "templates")
static_dir = os.path.join(os.path.dirname(basedir), "static")

# Initialize extensions without app context
db = SQLAlchemy()
bcrypt = flask_bcrypt.Bcrypt()
login_manager = LoginManager()
csrf = CSRFProtect()
cache = Cache()
migrate = Migrate()


def get_allowed_emails():
    """Get allowed emails from environment variable."""
    return os.environ.get("ALLOWED_EMAILS", "").split(",")


def get_environment():
    """
    Determine which configuration to use based on various indicators.
    """
    # Check if we're running tests
    is_testing = (
        any("pytest" in arg for arg in sys.argv)
        or "pytest" in sys.modules
        or any("test" in path for path in sys.path if os.path.exists(path))
        or os.environ.get("FLASK_ENV") == "test"
    )

    # Check if we're in production
    is_production = (
        os.environ.get("FLASK_ENV") == "production"
        or os.environ.get("ENVIRONMENT") == "production"
        or os.environ.get("ENV") == "production"
    )

    if is_testing:
        print("Using TestConfig")
        return "test"
    elif is_production:
        print("Using ProdConfig")
        return "production"
    else:
        print("Using DevConfig")
        return "development"


def create_app(config_name=None):
    """Application factory pattern."""
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    # Determine environment
    env = config_name or get_environment()

    # Configure the app based on environment
    if env == "test":
        app.config.from_object("config.TestConfig")
        app.env = "test"
    elif env == "production":
        app.config.from_object("config.ProdConfig")
        app.env = "production"
    elif env == "development":
        app.config.from_object("config.DevConfig")
        app.env = "development"
    else:
        raise ValueError(f"Invalid environment: {env}")

    # Initialize extensions with app context
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "login.login"  # Updated for blueprint
    csrf.init_app(app)
    cache.init_app(app)
    # Session(app)

    CORS(
        app,
        origins=[],  # No external origins allowed
        methods=["GET", "POST"],  # Only allow necessary methods
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=True,
        max_age=86400,
    )
    print("CORS initialized")

    migrate.init_app(app, db)

    # Configure Flask-Talisman with CSP
    talisman = configure_talisman(app)
    print(f"Talisman initialized: {talisman}")

    # Import and register blueprints
    from src.routes.home import home_bp
    from src.routes.login import login_bp, register_login_manager
    from src.routes.errorhandler import errorhandler_bp, register_error_handlers
    from src.routes.tests import tests_bp

    app.register_blueprint(home_bp)
    app.register_blueprint(login_bp)
    app.register_blueprint(errorhandler_bp)
    app.register_blueprint(tests_bp)

    # Register error handlers and login manager
    register_error_handlers(app)
    register_login_manager(login_manager, cache, db)

    # Initialize database and prepopulate if not in test mode
    # SHOULD NOT BE DONE IN PRODUCTION!!!!!
    # with app.app_context():
    #     if env != "test":
    #         prepopulate_database(app)

    return app


def prepopulate_database(app):
    """Initialize database and add default data."""
    try:
        # Check if the database exists
        db_path = app.config.get("SQLALCHEMY_DATABASE_URI", "").replace(
            "sqlite:///", ""
        )

        if os.path.exists(db_path):
            print("Database exists, skipping table creation")
        else:
            print("Database does not exist, creating tables")
            db.create_all()
            print("Database tables created/verified")

        # Import User model here to avoid circular imports
        from src.models.user import User

        # Check if we already have any users
        try:
            user_count = db.session.query(User).count()
            print(f"Current user count: {user_count}")

            if user_count == 0:
                # No users exist, create the default admin user
                user = User(email="admin@test.com")
                user.password_hash = "123456"
                db.session.add(user)
                print(f"Added user {user.email} to database")
                db.session.commit()
                print("Default admin user created successfully")
            else:
                print("Users already exist in database, skipping user creation")
        except Exception as e:
            print(f"Error checking/creating users: {e}")
            db.session.rollback()

    except Exception as e:
        print(f"Error in prepopulate_database: {e}")


def configure_talisman(app: Flask):
    # Configure Flask-Talisman with CSP
    if app.env in ["production", "development", "test"]:
        if app.env == "test":
            # Testing CSP - minimal security for tests
            talisman = Talisman(
                app,
                force_https=False,  # Allow HTTP in tests
                strict_transport_security=False,  # No HSTS in tests
                content_security_policy={
                    "default-src": "'self'",
                    "script-src": [
                        "'self'",
                        "'unsafe-inline'",  # Allow inline scripts for tests
                        "'unsafe-eval'",  # Allow eval for tests
                    ],
                    "style-src": [
                        "'self'",
                        "'unsafe-inline'",  # Allow inline styles for tests
                    ],
                    "font-src": [
                        "'self'",
                    ],
                    "img-src": [
                        "'self'",
                        "data:",  # Allow data URLs for tests
                    ],
                    "connect-src": [
                        "'self'",
                    ],
                    "frame-ancestors": "'none'",
                    "base-uri": "'self'",
                    "form-action": "'self'",
                    "object-src": "'none'",
                    "media-src": "'self'",
                    "worker-src": "'self'",
                    "manifest-src": "'self'",
                },
                content_security_policy_nonce_in=["script-src", "style-src"],
                referrer_policy="strict-origin-when-cross-origin",
            )
        elif app.env == "development":
            # Development CSP - slightly more permissive
            talisman = Talisman(
                app,
                force_https=False,  # Allow HTTP in development
                strict_transport_security=False,  # No HSTS in development
                content_security_policy={
                    "default-src": "'self'",
                    "script-src": [
                        "'self'",
                        "'unsafe-inline'",  # Needed for inline scripts
                        "https://cdn.jsdelivr.net",
                        "https://code.jquery.com",
                    ],
                    "style-src": [
                        "'self'",
                        "'unsafe-inline'",  # Needed for inline styles
                        "https://cdn.jsdelivr.net",
                        "https://fonts.googleapis.com",
                    ],
                    "font-src": [
                        "'self'",
                        "https://cdn.jsdelivr.net",
                        "https://fonts.gstatic.com",
                    ],
                    "img-src": [
                        "'self'",
                        "data:",
                        # "https:", # This is not needed as we are using HTTP in development
                    ],
                    "connect-src": [
                        "'self'",
                    ],
                    "frame-ancestors": "'none'",
                    "base-uri": "'self'",
                    "form-action": "'self'",
                    "object-src": "'none'",
                    "media-src": "'self'",
                    "worker-src": "'self'",
                    "manifest-src": "'self'",
                },
                content_security_policy_nonce_in=["script-src", "style-src"],
                referrer_policy="strict-origin-when-cross-origin",
            )
        else:
            # Production CSP - strict security
            talisman = Talisman(
                app,
                force_https=True,
                strict_transport_security=True,
                strict_transport_security_max_age=31536000,
                strict_transport_security_include_subdomains=True,
                strict_transport_security_preload=True,
                content_security_policy={
                    "default-src": "'self'",
                    "script-src": [
                        "'self'",
                        "https://cdn.jsdelivr.net",
                        "https://code.jquery.com",
                    ],
                    "style-src": [
                        "'self'",
                        "https://cdn.jsdelivr.net",
                        "https://fonts.googleapis.com",
                    ],
                    "font-src": [
                        "'self'",
                        "https://cdn.jsdelivr.net",
                        "https://fonts.gstatic.com",
                    ],
                    "img-src": [
                        "'self'",
                        "data:",
                        # "https:",
                    ],
                    "connect-src": [
                        "'self'",
                    ],
                    "frame-ancestors": "'none'",
                    "base-uri": "'self'",
                    "form-action": "'self'",
                    "object-src": "'none'",
                    "media-src": "'self'",
                    "worker-src": "'self'",
                    "manifest-src": "'self'",
                },
                content_security_policy_nonce_in=["script-src", "style-src"],
                referrer_policy="strict-origin-when-cross-origin",
            )

        return talisman


# Export commonly used objects for backward compatibility
__all__ = ["db", "bcrypt", "login_manager", "csrf", "cache", "create_app"]
