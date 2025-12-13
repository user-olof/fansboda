from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user, login_required
from src.models.user import Role


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


def admin_required(f):
    """
    Decorator to require admin role for a route.

    Usage:
        @admin_required
        def admin_dashboard():
            return render_template("admin.html")
    """

    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated and allowed (email whitelist)
        if not current_user.is_authenticated or not current_user.is_allowed():
            flash("Access denied. You are not authorized.", "error")
            return redirect(url_for("login.login"))

        # Check if user has admin role
        if not current_user.is_admin():
            flash("Access denied. Admin privileges required.", "error")
            abort(403)

        return f(*args, **kwargs)

    return decorated_function


def role_required(*required_roles):
    """
    Decorator to require specific role(s) for a route.

    Usage:
        @role_required(Role.ADMIN)
        @role_required(Role.USER, Role.ADMIN)  # Either role works
    """

    def decorator(f):
        @wraps(f)
        @login_required
        def decorated_function(*args, **kwargs):
            # Check if user is authenticated and allowed
            if not current_user.is_authenticated or not current_user.is_allowed():
                flash("Access denied. You are not authorized.", "error")
                return redirect(url_for("login.login"))

            # Check if user has one of the required roles
            if current_user.role not in required_roles:
                flash("Access denied. Insufficient permissions.", "error")
                abort(403)

            return f(*args, **kwargs)

        return decorated_function

    return decorator
