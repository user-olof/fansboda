from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user, login_required


def allowed_user_required(f):
    """Decorator to ensure only whitelisted users can access routes."""

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_allowed():
            flash(
                "Access denied. You are not authorized to use this application.",
                "error",
            )
            return redirect(url_for("login.login"))
        return f(*args, **kwargs)

    return decorated_function
