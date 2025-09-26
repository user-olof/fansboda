from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Email, Length


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        validators=[
            DataRequired(),
            Email(message="Please enter a valid email address"),
        ],
    )
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=3, message="Password must be at least 3 characters long"),
        ],
    )
    remember_me = BooleanField("Remember Me")
    submit = SubmitField("Sign In")
    csrf_token = HiddenField("CSRF Token")
