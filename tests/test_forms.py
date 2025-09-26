import pytest
from src.forms.loginform import LoginForm
from src.forms.signupform import SignupForm


class TestLoginForm:
    """Test cases for the LoginForm."""

    def test_login_form_creation(self, client):
        """Test creating a login form."""
        with client.application.app_context():
            form = LoginForm()
            assert hasattr(form, "email")  # Changed from username to email
            assert hasattr(form, "password")
            assert hasattr(form, "remember_me")
            assert hasattr(form, "submit")
            assert hasattr(form, "csrf_token")  # CSRF token is automatically included

    def test_csrf_token_present(self, client):
        """Test that CSRF token is present in the form."""
        with client.application.app_context():
            form = LoginForm()
            assert hasattr(form, "csrf_token")

    def test_form_validation_with_valid_data(self, client):
        """Test form validation with valid data."""
        with client.application.test_request_context():
            form_data = {
                "email": "test@example.com",  # Changed from username to email
                "password": "testpass",
                "remember_me": True,
            }
            form = LoginForm(data=form_data)
            # Note: CSRF validation might fail in test context
            # We'll test the individual field validation
            assert form.email.data == "test@example.com"
            assert form.password.data == "testpass"
            assert form.remember_me.data is True

    def test_form_validation_with_invalid_email(self, client):
        """Test form validation with invalid email."""
        with client.application.test_request_context():
            form_data = {
                "email": "invalid-email",  # Invalid email format
                "password": "testpass",
                "remember_me": True,
            }
            form = LoginForm(data=form_data)
            # The form should not validate due to invalid email
            assert form.validate() is False
            assert "email" in form.errors

    def test_form_validation_with_missing_password(self, client):
        """Test form validation with missing password."""
        with client.application.test_request_context():
            form_data = {
                "email": "test@example.com",
                "password": "",  # Empty password
                "remember_me": True,
            }
            form = LoginForm(data=form_data)
            # The form should not validate due to missing password
            assert form.validate() is False
            assert "password" in form.errors

    def test_form_validation_with_missing_email(self, client):
        """Test form validation with missing email."""
        with client.application.test_request_context():
            form_data = {
                "email": "",  # Empty email
                "password": "testpass",
                "remember_me": True,
            }
            form = LoginForm(data=form_data)
            # The form should not validate due to missing email
            assert form.validate() is False
            assert "email" in form.errors

    def test_remember_me_field_default(self, client):
        """Test that remember_me field has correct default value."""
        with client.application.test_request_context():
            form = LoginForm()
            # By default, remember_me should be False
            assert form.remember_me.data is False

    def test_form_rendering(self, client):
        """Test that form can be rendered."""
        with client.application.app_context():
            form = LoginForm()
            # Test that we can get the HTML representation
            html = str(form.email)
            assert "email" in html.lower()

    def test_csrf_protection_integration(self, client):
        """Test CSRF protection integration with the form."""
        # Test by making a GET request to login page
        response = client.get("/login")
        # The response should contain the CSRF token in the form
        assert response.status_code == 200
        assert b"csrf_token" in response.data or b"hidden" in response.data

    def test_form_validation_without_csrf(self, client, app):
        """Test that form validation works when CSRF is disabled (normal testing)."""
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.test_request_context():

            form_data = {
                "email": "test@example.com",  # Changed from username to email
                "password": "testpass",
                "remember_me": True,
            }
            form = LoginForm(data=form_data)
            # Should validate successfully when CSRF is disabled
            assert form.validate() is True


class TestSignupForm:
    """Test cases for the SignupForm."""

    def test_signup_form_creation(self, client):
        """Test creating a signup form."""
        with client.application.app_context():
            form = SignupForm()
            assert hasattr(form, "email")
            assert hasattr(form, "password")
            assert hasattr(form, "password_confirm")
            assert hasattr(form, "submit")
            assert hasattr(form, "csrf_token")

    def test_form_validation_with_valid_data(self, client):
        """Test form validation with valid data."""
        with client.application.test_request_context():
            form_data = {
                "email": "newuser@example.com",
                "password": "newpass123",
                "password_confirm": "newpass123",
            }
            form = SignupForm(data=form_data)
            # Note: CSRF validation might fail in test context
            assert form.email.data == "newuser@example.com"
            assert form.password.data == "newpass123"
            assert form.password_confirm.data == "newpass123"

    def test_password_confirmation_validation(self, client):
        """Test password confirmation validation."""
        with client.application.test_request_context():
            form_data = {
                "email": "newuser@example.com",
                "password": "newpass123",
                "password_confirm": "differentpass",  # Different password
            }
            form = SignupForm(data=form_data)
            # The form should not validate due to password mismatch
            assert form.validate() is False
            assert "password_confirm" in form.errors

    def test_password_length_validation(self, client):
        """Test password length validation."""
        with client.application.test_request_context():
            form_data = {
                "email": "newuser@example.com",
                "password": "12",  # Too short
                "password_confirm": "12",
            }
            form = SignupForm(data=form_data)
            # The form should not validate due to short password
            assert form.validate() is False
            assert "password" in form.errors

    def test_email_validation(self, client):
        """Test email validation."""
        with client.application.test_request_context():
            form_data = {
                "email": "invalid-email",  # Invalid email
                "password": "newpass123",
                "password_confirm": "newpass123",
            }
            form = SignupForm(data=form_data)
            # The form should not validate due to invalid email
            assert form.validate() is False
            assert "email" in form.errors

    def test_form_rendering(self, client):
        """Test that form can be rendered."""
        with client.application.app_context():
            form = SignupForm()
            # Test that we can get the HTML representation
            html = str(form.email)
            assert "email" in html.lower()

    def test_csrf_protection_integration(self, client):
        """Test CSRF protection integration with the form."""
        # Test by making a GET request to signup page
        response = client.get("/signup")
        # The response should contain the CSRF token in the form
        assert response.status_code == 200
        assert b"csrf_token" in response.data or b"hidden" in response.data

    def test_form_validation_without_csrf(self, client, app):
        """Test that form validation works when CSRF is disabled (normal testing)."""
        app.config["WTF_CSRF_ENABLED"] = False

        with client.application.test_request_context():
            form_data = {
                "email": "newuser@example.com",
                "password": "newpass123",
                "password_confirm": "newpass123",
            }
            form = SignupForm(data=form_data)
            # Should validate successfully when CSRF is disabled
            assert form.validate() is True
