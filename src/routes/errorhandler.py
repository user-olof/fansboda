# src/routes/errorhandler.py
from flask import Blueprint, render_template
from werkzeug.exceptions import HTTPException

errorhandler_bp = Blueprint("errorhandler", __name__)


@errorhandler_bp.route("/404")
def four_oh_four():
    return render_template("404.html", message="Page not found"), 404


def register_error_handlers(app):
    """Register error handlers with the app."""

    @app.errorhandler(Exception)
    def handle_exception(e):
        # pass through HTTP errors
        if isinstance(e, HTTPException):
            return e

        # now you're handling non-HTTP exceptions only
        return render_template("404.html", message=e), 404
