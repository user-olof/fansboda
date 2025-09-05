from src import db, login
from werkzeug.security import generate_password_hash, check_password_hash

from flask_login import UserMixin
from flask import current_app


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))

    def __repr__(self):
        return f"<User {self.email}>"

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_allowed(self):
        allowed_emails = current_app.config.get("ALLOWED_EMAILS", [])
        return self.email in allowed_emails


@login.user_loader
def load_user(id):
    user = User.query.get(int(id))
    if user and user.is_allowed():
        return user
    else:
        return None
