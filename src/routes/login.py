import os
from src import app, db
from flask import render_template, flash, redirect, url_for
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from src.models.user import User
from src.forms.loginform import LoginForm
from src.forms.signupform import SignupForm
import scrypt
from werkzeug.exceptions import HTTPException


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.scalar(sa.select(User).where(User.email == form.email.data))
        if user is None or not verify_password(user.password_hash, form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("login"))
        login_user(user, remember=form.remember_me.data)
        return redirect(url_for("index"))
    return render_template("login.html", title="Sign In", form=form)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = SignupForm()
    if form.validate_on_submit():

        if User.query.filter_by(email=form.email.data).first() is not None:
            flash("Email already exists")
            return redirect(url_for("signup"))

        hashed_password = hash_password(form.password.data)

        user = User(
            email=form.email.data,
            password_hash=hashed_password,
        )
        db.session.add(user)
        db.session.commit()
        flash("Account created successfully")
        return redirect(url_for("index"))
    return render_template("signup.html", title="Sign Up", form=form)


def hash_password(password, maxtime=2, datalength=64):
    """Create a secure password hash using scrypt encryption.

    Args:
        password: The password to hash
        maxtime: Maximum time to spend hashing in seconds
        datalength: Length of the random data to encrypt

    Returns:
        bytes: An encrypted hash suitable for storage and later verification
    """
    return scrypt.encrypt(os.urandom(datalength), password, maxtime=maxtime)


def verify_password(hashed_password, guessed_password, maxtime=0.5):
    """Verify a password against its hash with better error handling.

    Args:
        hashed_password: The stored password hash from hash_password()
        guessed_password: The password to verify
        maxtime: Maximum time to spend in verification

    Returns:
        tuple: (is_valid, status_code) where:
            - is_valid: True if password is correct, False otherwise
            - status_code: One of "correct", "wrong_password", "time_limit_exceeded",
              "memory_limit_exceeded", or "error"

    Raises:
        scrypt.error: Only raised for resource limit errors, which you may want to
                    handle by retrying with higher limits or force=True
    """
    try:
        scrypt.decrypt(hashed_password, guessed_password, maxtime, encoding=None)
        return True, "correct"
    except scrypt.error as e:
        # Check the specific error message to differentiate between causes
        error_message = str(e)
        if error_message == "password is incorrect":
            # Wrong password was provided
            return False, "wrong_password"
        elif error_message == "decrypting file would take too long":
            # Time limit exceeded
            raise  # Re-raise so caller can handle appropriately
        elif error_message == "decrypting file would take too much memory":
            # Memory limit exceeded
            raise  # Re-raise so caller can handle appropriately
        else:
            # Some other error occurred (corrupted data, etc.)
            return False, "error"


@login_required
@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for("index"))


# @app.errorhandler(Exception)
# def handle_exception(e):
#     # pass through HTTP errors
#     if isinstance(e, HTTPException):
#         return e

#     # now you're handling non-HTTP exceptions only
#     return render_template("404.html", message=e), 404
