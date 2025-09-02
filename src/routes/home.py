
from src import app
from flask import render_template
from flask_login import login_required
from src.models.user import User


@app.route("/")
@app.route("/index")
@login_required
def index():
    return render_template("index.html", title="Dashboard")


@app.route("/users")
def users():
    users_list = User.query.all()
    return render_template("users.html", title="Users", users=users_list)


@app.route("/users/<int:user_id>")
@login_required
def user(user_id):
    user = User.query.get_or_404(user_id)
    return render_template("user_profile.html", title=f"User {user.email}", user=user)


@app.route("/users/<string:email>")
@login_required
def user_by_email(email):
    user = User.query.filter_by(email=email).first_or_404()
    return render_template("user_profile.html", title=f"User {user.email}", user=user)
