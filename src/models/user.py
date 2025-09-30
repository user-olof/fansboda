from src import db, bcrypt
from flask_login import UserMixin
from flask import current_app
from sqlalchemy.ext.hybrid import hybrid_property


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    _password_hash = db.Column(db.String)

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
        allowed_emails = current_app.config.get("ALLOWED_EMAILS", [])
        return self.email in allowed_emails

    # def _hash_password(self, password, maxtime=5, datalength=64):
    #     """Create a secure password hash using scrypt encryption.

    #     Args:
    #         password: The password to hash
    #         maxtime: Maximum time to spend hashing in seconds
    #         datalength: Length of the random data to encrypt

    #     Returns:
    #         bytes: An encrypted hash suitable for storage and later verification
    #     """
    #     return scrypt.encrypt(os.urandom(datalength), password, maxtime=maxtime)

    # def _verify_password(
    #     self, hashed_password, guessed_password, maxtime=5
    # ) -> tuple[bool, str]:
    #     """Verify a password against its hash with better error handling.

    #     Args:
    #         hashed_password: The stored password hash from hash_password()
    #         guessed_password: The password to verify
    #         maxtime: Maximum time to spend in verification

    #     Returns:
    #         tuple: (is_valid, status_code) where:
    #             - is_valid: True if password is correct, False otherwise
    #             - status_code: One of "correct", "wrong_password", "time_limit_exceeded",
    #             "memory_limit_exceeded", or "error"

    #     Raises:
    #         scrypt.error: Only raised for resource limit errors, which you may want to
    #                     handle by retrying with higher limits or force=True
    #     """
    #     try:
    #         scrypt.decrypt(hashed_password, guessed_password, maxtime, encoding="utf-8")
    #         return True, "correct"
    #     except scrypt.error as e:
    #         # Check the specific error message to differentiate between causes
    #         error_message = str(e)
    #         if error_message == "password is incorrect":
    #             # Wrong password was provided
    #             return False, "wrong_password"
    #         elif error_message == "decrypting file would take too long":
    #             # Time limit exceeded
    #             raise  # Re-raise so caller can handle appropriately
    #         elif error_message == "decrypting file would take too much memory":
    #             # Memory limit exceeded
    #             raise  # Re-raise so caller can handle appropriately
    #         else:
    #             # Some other error occurred (corrupted data, etc.)
    #             return False, "error"
