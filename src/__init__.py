import sys
from flask import Flask
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_caching import Cache
import redis
import flask_bcrypt


# Configure Flask to look for templates in the parent directory
basedir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(os.path.dirname(basedir), "templates")
static_dir = os.path.join(os.path.dirname(basedir), "static")

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)


# Environment detection logic
def get_environment():
    """
    Determine which configuration to use based on various indicators.
    """
    # Check if we're running tests
    is_testing = (
        # Check if pytest is in the command line arguments
        any("pytest" in arg for arg in sys.argv)
        or
        # Check if pytest module is loaded
        "pytest" in sys.modules
        or
        # Check if we're running from a test directory
        any("test" in path for path in sys.path if os.path.exists(path))
        or
        # Check if FLASK_ENV is explicitly set to test
        os.environ.get("FLASK_ENV") == "test"
    )

    if is_testing:
        print("Using TestConfig")
        return "test"
    else:
        print("Using DevConfig")
        return "development"


# Set the environment
env = get_environment()

# Configure the app based on environment
if env == "test":
    app.config.from_object("config.TestConfig")
    app.env = "test"
else:
    app.config.from_object("config.DevConfig")
    app.env = "development"


# Enable CSRF protection
csrf = CSRFProtect(app)

db = SQLAlchemy(app)


bcrypt = flask_bcrypt.Bcrypt(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"


cache = Cache()
cache.init_app(app)


# Import models and routes after app initialization
from src.models.user import User
from src.routes import home
from src.routes import login as login_routes
from src.routes import errorhandler
from src.routes import tests


# prepopulate database with test data
def prepopulate_database():
    with app.app_context():
        db.create_all()

        # Check if user already exists
        existing_user = User.query.filter_by(email="admin@test.com").first()
        if not existing_user:
            user = User(email="admin@test.com")
            user.password_hash = "123456"
            db.session.add(user)
            db.session.commit()
            print("Test user created successfully")
        else:
            print("Test user already exists")


# prepopulate database with test data
prepopulate_database()
