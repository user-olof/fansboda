from src import app
from flask import render_template
from werkzeug.exceptions import HTTPException


@app.route("/404")
def four_oh_four():
    return render_template("404.html", message="Page not found"), 404


@app.errorhandler(Exception)
def handle_exception(e):
    # pass through HTTP errors
    if isinstance(e, HTTPException):
        return e

    # now you're handling non-HTTP exceptions only
    return render_template("404.html", message=e), 404
