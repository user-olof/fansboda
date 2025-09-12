import os
import pickle
from src import app, cache, db, login_manager
from flask import current_app, render_template, flash, redirect, url_for
from flask_login import current_user, login_user, logout_user, login_required
import sqlalchemy as sa
from src.models.user import User
from src.forms.loginform import LoginForm
from src.forms.signupform import SignupForm
from src.access_control import allowed_user_required
# import scrypt
from werkzeug.exceptions import HTTPException


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    form = LoginForm()
    if form.validate_on_submit():

        # first find the user in the database
        user = db.session.scalar(sa.select(User).where(User.email == form.email.data))
        if user is None or not user.authenticate(form.password.data):
            flash("Invalid username or password")
            return redirect(url_for("login"))

        # then check if the user is allowed to login
        if not user.is_allowed():
            flash("Access denied. You are not authorized to use this application.")
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
        # first check if the user is allowed to sign up
        allowed_emails = current_app.config["ALLOWED_EMAILS"]
        if form.email.data not in allowed_emails:
            flash("Access denied. You are not authorized to use this application.")
            return redirect(url_for("signup"))

        if User.query.filter_by(email=form.email.data).first() is not None:
            flash("Email already exists")
            return redirect(url_for("signup"))

        user = User(email=form.email.data)
        user.password_hash = form.password.data

        db.session.add(user)
        db.session.commit()
        flash("Account created successfully")
        return redirect(url_for("index"))
    return render_template("signup.html", title="Sign Up", form=form)


@app.route("/logout")
@login_required
def logout():
    if current_user.is_authenticated:
        user_id = current_user.id
        logout_user()
        cache.delete(f"user_{user_id}")
    return redirect(url_for("login"))


@login_manager.user_loader
def load_user(id):
    user = cache.get(f"user_{id}")
    if user is None:
        user = User.query.get(int(id))
        cache.set(f"user_{id}", pickle.dumps(user), timeout=3600)
        return user
    else:
        print("User found in cache")
        return pickle.loads(user)
    return None
