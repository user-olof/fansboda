from flask import Flask
import os
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect


# Configure Flask to look for templates in the parent directory
basedir = os.path.abspath(os.path.dirname(__file__))
template_dir = os.path.join(os.path.dirname(basedir), "templates")
static_dir = os.path.join(os.path.dirname(basedir), "static")

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
app.env = "development"

# Configure the app
app.config.from_object(
    "config.DevConfig" if app.env == "development" else "config.ProdConfig"
)

# Enable CSRF protection
csrf = CSRFProtect(app)

db = SQLAlchemy(app)

login = LoginManager(app)
login.login_view = "login"

# Import models and routes after app initialization
from src.models.user import User
from src.routes import home
from src.routes import login as login_routes
from src.routes import errorhandler
