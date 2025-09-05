
from src import app
from flask import render_template

from src.access_control import allowed_user_required
from src.models.user import User
from src.route_protection import dev_only


@app.route("/")
@app.route("/index")
@allowed_user_required
def index():
    return render_template("index.html", title="Dashboard")


@app.route("/users")
@dev_only
def users():
    users_list = User.query.all()
    return render_template("users.html", title="Users", users=users_list)


@app.route("/users/<int:user_id>")
@allowed_user_required
def user(user_id):
    user = User.query.get_or_404(user_id)
    return render_template("user_profile.html", title=f"User {user.email}", user=user)


@app.route("/users/<string:email>")
@allowed_user_required
def user_by_email(email):
    user = User.query.filter_by(email=email).first_or_404()
    return render_template("user_profile.html", title=f"User {user.email}", user=user)
