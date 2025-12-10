# src/routes/login.py
import pickle
from flask import (
    Blueprint,
    current_app,
    render_template,
    flash,
    redirect,
    url_for,
    session,
    request,
)
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from src.models.user import User
from src.forms.loginform import LoginForm
from src.forms.signupform import SignupForm
from datetime import datetime, timedelta
from src import db

login_bp = Blueprint("login", __name__)


@login_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("home.index"))

    form = LoginForm()
    if form.validate_on_submit():
        # Find the user in the database
        try:
            user = db.session.scalar(
                sa.select(User).where(User.email == form.email.data)
            )
        except Exception as e:
            print(f"Error: {e}")
            user = None

        # Check if user exists and is not locked out
        if user is None:
            flash("Invalid username or password")
            return redirect(url_for("login.login"))

        # Check if user is locked out
        if user.is_locked_out():
            remaining_minutes = user.get_lockout_time_remaining()
            flash(
                f"Account locked due to too many failed attempts. Try again in {remaining_minutes} minutes."
            )
            return render_template("temporary_closed.html")

        # Check if password is correct
        if not user.authenticate(form.password.data):
            # Record failed login attempt
            user.record_failed_login()

            if user.is_locked_out():
                flash(
                    "Account locked due to too many failed attempts. Try again in 24 hours."
                )
                return render_template("temporary_closed.html")
            else:
                attempts_left = 5 - user.failed_login_attempts
                flash(
                    f"Invalid username or password. {attempts_left} attempts remaining."
                )
                return redirect(url_for("login.login"))

        # Check if user is allowed to login
        if not user.is_allowed():
            flash("Access denied. You are not authorized to use this application.")
            return redirect(url_for("login.login"))

        # Successful login - reset attempts and log in
        user.reset_login_attempts()
        login_user(user, remember=form.remember_me.data)

        flash(f"Welcome back, {user.email}! You have successfully logged in!")
        return redirect(url_for("home.index"))

    return render_template("login.html", title="Login", form=form)


# @login_bp.route("/signup", methods=["GET", "POST"])
# def signup():
#     return "SIGNUP ROUTE IS WORKING - THIS IS A TEST"


@login_bp.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("home.index"))
    form = SignupForm()
    if form.validate_on_submit():

        # first check if the user is allowed to sign up
        allowed_emails = current_app.config["ALLOWED_EMAILS"]
        if form.email.data not in allowed_emails:
            flash("Access denied. You are not authorized to use this application.")
            return redirect(url_for("login.signup"))

        from src import db

        if db.session.query(User).filter_by(email=form.email.data).first() is not None:
            flash("Email already exists")
            return redirect(url_for("login.signup"))

        if form.password.data == "":
            flash("Password cannot be empty")
            return redirect(url_for("login.signup"))

        user = User(email=form.email.data)
        user.password_hash = form.password.data  # This will be encrypted in the setter
        db.session.add(user)
        db.session.commit()

        flash("Account created successfully")
        return redirect(url_for("home.index"))

    return render_template("signup.html", title="Sign Up", form=form)


@login_bp.route("/logout")
@login_required
def logout():
    if current_user.is_authenticated:
        from src import cache

        user_id = current_user.id
        # Clear user cache
        cache.delete(f"user_{user_id}")

        # Clear session data
        session.clear()

        logout_user()
    return redirect(url_for("login.login"))


# This needs to be registered with the app, not the blueprint
def register_login_manager(login_manager, cache, db):
    """Register the user loader with the login manager."""

    @login_manager.user_loader
    def load_user(id):
        try:
            b_user = cache.get(f"user_{id}")
            if b_user is None:
                # user = User.query.get(int(id))
                # Use a fresh query to avoid session issues
                user = db.session.get(User, int(id))
                if user is not None and user.is_allowed():
                    cache.set(f"user_{id}", pickle.dumps(user), timeout=3600)
                    return user
                return None
            else:
                user = pickle.loads(b_user)
                if user is not None and user.is_allowed():
                    return user
                else:
                    cache.delete(f"user_{id}")
                    return None
        except Exception:
            # If there's any error (including cache issues), clear cache and return None
            cache.delete(f"user_{id}")
            return None
