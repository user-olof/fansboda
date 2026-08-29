# src/routes/errorhandler.py
from flask import Blueprint, current_app, render_template
from werkzeug.exceptions import HTTPException

errorhandler_bp = Blueprint("errorhandler", __name__)

GENERIC_ERROR_MESSAGE = (
    "An unexpected error occurred. Please try again later."
)


@errorhandler_bp.route("/404")
def four_oh_four():
    return render_template("404.html", message="Page not found"), 404


@errorhandler_bp.route("/500")
def five_hundred():
    return render_template("500.html", message=GENERIC_ERROR_MESSAGE), 500


def register_error_handlers(app):
    """Register error handlers with the app."""

    @app.errorhandler(Exception)
    def handle_exception(e):
        # pass through HTTP errors
        if isinstance(e, HTTPException):
            return e

        current_app.logger.exception("Unhandled exception")

        if current_app.debug:
            message = str(e)
        else:
            message = GENERIC_ERROR_MESSAGE

        return render_template("500.html", message=message), 500
