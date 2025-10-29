from functools import wraps
from flask import current_app, abort


def dev_only(f):
    """Decorator to make routes available only in development."""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_app.config.get("DEBUG", False):
            abort(404)  # Return 404 in production
        return f(*args, **kwargs)
git 
    return decorated_function


def config_enabled(config_key):
    """Decorator to enable routes based on config flag."""

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_app.config.get(config_key, False):
                abort(404)
            return f(*args, **kwargs)

        return decorated_function

    return decorator
