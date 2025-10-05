from src import db, bcrypt
from flask_login import UserMixin
from flask import current_app
from sqlalchemy.ext.hybrid import hybrid_property
from datetime import datetime, timedelta, timezone


class User(UserMixin, db.Model):
    __tablename__ = 'user'
    __table_args__ = {'extend_existing': True}  # This allows redefinition
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    _password_hash = db.Column(db.String)

    # Lockout fields
    failed_login_attempts = db.Column(db.Integer, default=0)
    locked_until = db.Column(db.DateTime, nullable=True)
    last_failed_login = db.Column(db.DateTime, nullable=True)

    def __repr__(self):
        return f"<User {self.email}>"

    @hybrid_property
    def password_hash(self):
        return self._password_hash

    @password_hash.setter
    def password_hash(self, password):
        # Generate hash from plain text password and store it
        try:
            hashed = bcrypt.generate_password_hash(password.encode("utf-8"), 10)
            self._password_hash = hashed.decode("utf-8")
        except ValueError as e:
            current_app.logger.error(f"Error setting password hash: {e}")
            raise e
        except Exception as e:
            current_app.logger.error(f"Error setting password hash: {e}")
            raise e

    def authenticate(self, password):
        return bcrypt.check_password_hash(self._password_hash, password.encode("utf-8"))

    def is_allowed(self):
        """Check if user email is in the allowed emails list."""
        if not self or not self.email:
            return False

        # Get normalized allowed emails (cached for performance)
        allowed_emails = self._get_normalized_allowed_emails()

        # Normalize user email once
        str_email = str(self.email)
        normalized_email = str_email.lower().strip()

        # O(1) lookup instead of O(n) loop
        return normalized_email in allowed_emails

    @classmethod
    def _get_normalized_allowed_emails(cls):
        """Get normalized allowed emails (cached for performance)."""
        allowed_emails = current_app.config.get("ALLOWED_EMAILS", [])

        # Normalize all emails once and store in a set
        normalized = set()
        for email in allowed_emails:
            if email and email.strip():  # Skip empty/None emails
                normalized.add(email.lower().strip())

        return normalized

    def is_locked_out(self):
        """Check if user is currently locked out."""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    def record_failed_login(self):
        """Record a failed login attempt."""
        now = datetime.now(timezone.utc)
        self.failed_login_attempts += 1
        self.last_failed_login = now

        # Lock for 24 hours after 5 failed attempts
        if self.failed_login_attempts >= 5:
            self.locked_until = now + timedelta(hours=24)

        db.session.commit()

    def reset_login_attempts(self):
        """Reset failed login attempts (call on successful login)."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_failed_login = None
        db.session.commit()

    def get_lockout_time_remaining(self):
        """Get remaining lockout time in minutes."""
        if not self.is_locked_out():
            return 0
        remaining = self.locked_until - datetime.utcnow()
        return max(0, int(remaining.total_seconds() / 60))
