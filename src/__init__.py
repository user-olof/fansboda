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
app.env = "test"

# Configure the app
if app.env == "test":
    app.config.from_object("config.TestConfig")
elif app.env == "development":
    app.config.from_object("config.DevConfig")
else:
    app.config.from_object("config.ProdConfig")

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
