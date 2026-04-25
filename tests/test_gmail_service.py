"""
Comprehensive test suite for Gmail service.

This module tests Gmail service functionality including:
- Credential refresh for service-account creds
- Service account authentication (only supported path in ``get_gmail_service``)
- Email sending with success and error cases
"""

import os
import base64
from unittest.mock import Mock, mock_open
import pytest
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from email import message_from_bytes

from src.services.gmail_service import (
    _validate_and_refresh_credentials,
    get_gmail_service,
    send_email,
    SCOPES,
)


class TestValidateAndRefreshCredentials:
    """Test cases for _validate_and_refresh_credentials function."""

    def test_validate_credentials_valid(self, mocker, app):
        """Test validation of already valid credentials."""
        with app.app_context():
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = True

            result = _validate_and_refresh_credentials(mock_creds)

            assert result == mock_creds

    def test_validate_credentials_none(self, app):
        """Test validation when credentials are None."""
        with app.app_context():
            result = _validate_and_refresh_credentials(None)

            assert result is None

    def test_refresh_expired_credentials_success(self, mocker, app):
        """Test successful refresh of expired credentials."""
        with app.app_context():
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = False
            mock_creds.expired = True
            mock_creds.refresh_token = "refresh_token_123"
            mock_logger = mocker.patch("flask.current_app.logger")

            # Mock Request class
            mocker.patch("src.services.gmail_service.Request")

            def _after_refresh(_req):
                mock_creds.valid = True

            mock_creds.refresh.side_effect = _after_refresh

            result = _validate_and_refresh_credentials(mock_creds)

            assert result == mock_creds
            mock_creds.refresh.assert_called_once()
            mock_logger.info.assert_called_once_with(
                "Credentials refreshed successfully"
            )

    def test_refresh_expired_credentials_failure(self, mocker, app):
        """Test handling of credential refresh failure."""
        with app.app_context():
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = False
            mock_creds.expired = True
            mock_creds.refresh_token = "refresh_token_123"
            mock_creds.refresh.side_effect = Exception("Refresh failed")
            mock_logger = mocker.patch("flask.current_app.logger")

            result = _validate_and_refresh_credentials(mock_creds)

            assert result is None
            mock_logger.warning.assert_called_once()

    def test_credentials_valid_no_refresh_token(self, mocker, app):
        """Invalid credentials that stay invalid after refresh attempt yield None."""
        with app.app_context():
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = False
            mock_creds.expired = True
            mock_creds.refresh_token = None
            mocker.patch("src.services.gmail_service.Request")
            mocker.patch("flask.current_app.logger")

            result = _validate_and_refresh_credentials(mock_creds)

            assert result is None


class TestGetGmailService:
    """Tests for get_gmail_service (service account only, no user OAuth)."""

    def test_get_gmail_service_with_service_account(self, mocker, app):
        """Build Gmail client when service account + DWD are configured correctly."""
        with app.app_context():
            mock_service_account_creds = Mock()
            mock_creds_with_subject = Mock(spec=Credentials)
            mock_creds_with_subject.valid = True
            mock_service = Mock()

            mocker.patch.dict(
                os.environ,
                {
                    "GMAIL_APPLICATION_CREDENTIALS": "/path/to/service_account.json",
                    "GMAIL_SENDER_EMAIL": "sender@example.com",
                },
            )
            mocker.patch("os.path.exists", return_value=True)
            mocker.patch(
                "src.services.gmail_service.service_account.Credentials.from_service_account_file",
                return_value=mock_service_account_creds,
            )
            mock_service_account_creds.with_subject.return_value = (
                mock_creds_with_subject
            )

            def validate_side_effect(creds):
                if creds is None:
                    return None
                return mock_creds_with_subject

            mocker.patch(
                "src.services.gmail_service._validate_and_refresh_credentials",
                side_effect=validate_side_effect,
            )
            mocker.patch("src.services.gmail_service.build", return_value=mock_service)
            mock_logger = mocker.patch("flask.current_app.logger")

            result = get_gmail_service()

            assert result == mock_service
            mock_service_account_creds.with_subject.assert_called_once_with(
                "sender@example.com"
            )
            mock_logger.info.assert_called()

    def test_get_gmail_service_service_account_no_impersonation(self, mocker, app):
        """Without GMAIL_SENDER_EMAIL, service account auth does not produce credentials."""
        with app.app_context():
            mocker.patch.dict(
                os.environ,
                {
                    "GMAIL_APPLICATION_CREDENTIALS": "/path/to/sa.json",
                    "GMAIL_SENDER_EMAIL": "",  # override any real environment value
                },
            )
            mocker.patch("os.path.exists", return_value=True)
            mock_service_account_creds = Mock()
            mocker.patch(
                "src.services.gmail_service.service_account.Credentials.from_service_account_file",
                return_value=mock_service_account_creds,
            )
            mocker.patch("flask.current_app.logger")

            with pytest.raises(
                ValueError, match="Could not authenticate with Gmail API"
            ):
                get_gmail_service()

    def test_get_gmail_service_missing_gmail_app_credentials(self, mocker, app):
        """Without GMAIL_APPLICATION_CREDENTIALS, fail immediately (no other auth methods)."""
        with app.app_context():
            mocker.patch.dict(os.environ, {}, clear=True)
            mocker.patch("flask.current_app.logger")

            with pytest.raises(
                ValueError, match="GMAIL_APPLICATION_CREDENTIALS is not set"
            ):
                get_gmail_service()

    def test_get_gmail_service_no_valid_service_account_creds(self, mocker, app):
        """Path set but _authenticate_with_service_account yields nothing after validation."""
        with app.app_context():
            mocker.patch.dict(
                os.environ,
                {
                    "GMAIL_APPLICATION_CREDENTIALS": "/path/to/sa.json",
                    "GMAIL_SENDER_EMAIL": "x@y.com",
                },
            )
            mocker.patch("os.path.exists", return_value=True)
            mock_sa = Mock()
            mocker.patch(
                "src.services.gmail_service.service_account.Credentials.from_service_account_file",
                return_value=mock_sa,
            )
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = True
            mock_sa.with_subject.return_value = mock_creds
            mocker.patch(
                "src.services.gmail_service._validate_and_refresh_credentials",
                return_value=None,
            )
            mocker.patch("flask.current_app.logger")

            with pytest.raises(
                ValueError, match="Could not authenticate with Gmail API"
            ):
                get_gmail_service()

    def test_get_gmail_service_service_account_file_not_exists(self, mocker, app):
        """Missing key file yields auth failure; no user OAuth fallback."""
        with app.app_context():
            mocker.patch.dict(
                os.environ,
                {"GMAIL_APPLICATION_CREDENTIALS": "/nonexistent/path.json"},
            )
            mocker.patch("os.path.exists", return_value=False)
            mocker.patch("flask.current_app.logger")

            with pytest.raises(
                ValueError, match="Could not authenticate with Gmail API"
            ):
                get_gmail_service()

    def test_get_gmail_service_service_account_exception(self, mocker, app):
        """Exception loading the key is surfaced as auth failure (no OAuth fallback)."""
        with app.app_context():
            mocker.patch.dict(
                os.environ,
                {
                    "GMAIL_APPLICATION_CREDENTIALS": "/path/to/service_account.json",
                    "GMAIL_SENDER_EMAIL": "a@b.com",
                },
            )
            mocker.patch("os.path.exists", return_value=True)
            mocker.patch(
                "src.services.gmail_service.service_account.Credentials.from_service_account_file",
                side_effect=Exception("Service account error"),
            )
            mocker.patch("flask.current_app.logger")

            with pytest.raises(
                ValueError, match="Could not authenticate with Gmail API"
            ):
                get_gmail_service()


class TestSendEmail:
    """Test cases for send_email function."""

    def test_send_email_success(self, mocker, app):
        """Test successfully sending an email."""
        with app.app_context():
            # Setup
            to_email = "recipient@example.com"
            subject = "Test Subject"
            body_text = "Test body content"
            message_id = "test_message_id_123"

            # Mock Gmail service
            mock_service = Mock()
            mock_users = Mock()
            mock_messages = Mock()
            mock_send = Mock()
            mock_execute = Mock(return_value={"id": message_id})

            mock_service.users.return_value = mock_users
            mock_users.messages.return_value = mock_messages
            mock_messages.send.return_value = mock_send
            mock_send.execute = mock_execute

            mocker.patch(
                "src.services.gmail_service.get_gmail_service",
                return_value=mock_service,
            )
            mock_logger = mocker.patch("flask.current_app.logger")

            # Execute
            result = send_email(to_email, subject, body_text)

            # Verify
            assert result["success"] is True
            assert result["message_id"] == message_id

            # Verify message was created correctly
            mock_send.execute.assert_called_once()
            call_args = mock_messages.send.call_args
            assert call_args[1]["userId"] == "me"
            assert "raw" in call_args[1]["body"]

            # Verify encoded message contains expected content
            raw_message = call_args[1]["body"]["raw"]
            decoded_bytes = base64.urlsafe_b64decode(raw_message)
            parsed_message = message_from_bytes(decoded_bytes)

            # Check headers
            assert parsed_message["to"] == to_email
            assert parsed_message["subject"] == subject

            # Extract and decode body payload (base64 encoded)
            payload = parsed_message.get_payload()
            decoded_body = base64.b64decode(payload).decode("utf-8")
            assert body_text == decoded_body

            mock_logger.info.assert_called_once()

    def test_send_email_with_from_email(self, mocker, app):
        """Test sending email with custom from email."""
        with app.app_context():
            # Setup
            to_email = "recipient@example.com"
            from_email = "sender@example.com"
            subject = "Test Subject"
            body_text = "Test body content"
            message_id = "test_message_id_123"

            # Mock Gmail service
            mock_service = Mock()
            mock_users = Mock()
            mock_messages = Mock()
            mock_send = Mock()
            mock_execute = Mock(return_value={"id": message_id})

            mock_service.users.return_value = mock_users
            mock_users.messages.return_value = mock_messages
            mock_messages.send.return_value = mock_send
            mock_send.execute = mock_execute

            mocker.patch(
                "src.services.gmail_service.get_gmail_service",
                return_value=mock_service,
            )

            # Execute
            result = send_email(to_email, subject, body_text, from_email=from_email)

            # Verify
            assert result["success"] is True
            assert result["message_id"] == message_id

            # Verify from email is in message
            call_args = mock_messages.send.call_args
            raw_message = call_args[1]["body"]["raw"]
            decoded_message = base64.urlsafe_b64decode(raw_message).decode("utf-8")
            assert from_email in decoded_message

    def test_send_email_gmail_api_error(self, mocker, app):
        """Test handling of Gmail API errors."""
        with app.app_context():
            # Setup
            to_email = "recipient@example.com"
            subject = "Test Subject"
            body_text = "Test body content"

            # Mock Gmail service to raise error
            mock_service = Mock()
            mock_users = Mock()
            mock_messages = Mock()
            mock_send = Mock()
            mock_error = HttpError(
                resp=Mock(status=500),
                content=b'{"error": "Internal server error"}',
            )
            mock_send.execute = Mock(side_effect=mock_error)

            mock_service.users.return_value = mock_users
            mock_users.messages.return_value = mock_messages
            mock_messages.send.return_value = mock_send

            mocker.patch(
                "src.services.gmail_service.get_gmail_service",
                return_value=mock_service,
            )
            mock_logger = mocker.patch("flask.current_app.logger")

            # Execute
            result = send_email(to_email, subject, body_text)

            # Verify
            assert result["success"] is False
            assert "error" in result
            mock_logger.error.assert_called_once()

    def test_send_email_service_creation_error(self, mocker, app):
        """Test handling of service creation errors."""
        with app.app_context():
            # Setup
            to_email = "recipient@example.com"
            subject = "Test Subject"
            body_text = "Test body content"

            # Mock get_gmail_service to raise error
            mocker.patch(
                "src.services.gmail_service.get_gmail_service",
                side_effect=ValueError("Authentication failed"),
            )
            mock_logger = mocker.patch("flask.current_app.logger")

            # Execute
            result = send_email(to_email, subject, body_text)

            # Verify
            assert result["success"] is False
            assert "error" in result
            assert "Authentication failed" in result["error"]
            mock_logger.error.assert_called_once()

    def test_send_email_generic_exception(self, mocker, app):
        """Test handling of generic exceptions."""
        with app.app_context():
            # Setup
            to_email = "recipient@example.com"
            subject = "Test Subject"
            body_text = "Test body content"

            # Mock get_gmail_service to raise generic exception
            mocker.patch(
                "src.services.gmail_service.get_gmail_service",
                side_effect=Exception("Unexpected error"),
            )
            mock_logger = mocker.patch("flask.current_app.logger")

            # Execute
            result = send_email(to_email, subject, body_text)

            # Verify
            assert result["success"] is False
            assert "error" in result
            assert "Unexpected error" in result["error"]
            mock_logger.error.assert_called_once()

    def test_send_email_message_encoding(self, mocker, app):
        """Test that message encoding works correctly."""
        with app.app_context():
            # Setup
            to_email = "recipient@example.com"
            subject = "Test Subject with Special chars: áéíóú"
            body_text = "Test body with UTF-8: åäö 中文 🚀"

            # Mock Gmail service
            mock_service = Mock()
            mock_users = Mock()
            mock_messages = Mock()
            mock_send = Mock()
            mock_execute = Mock(return_value={"id": "test_id"})

            mock_service.users.return_value = mock_users
            mock_users.messages.return_value = mock_messages
            mock_messages.send.return_value = mock_send
            mock_send.execute = mock_execute

            mocker.patch(
                "src.services.gmail_service.get_gmail_service",
                return_value=mock_service,
            )

            # Execute
            result = send_email(to_email, subject, body_text)

            # Verify
            assert result["success"] is True

            # Verify encoding handles special characters
            call_args = mock_messages.send.call_args
            raw_message = call_args[1]["body"]["raw"]
            decoded_message = base64.urlsafe_b64decode(raw_message)

            parsed_message = message_from_bytes(decoded_message)

            payload = parsed_message.get_payload()
            decoded_body = base64.b64decode(payload).decode("utf-8")

            assert "åäö" in decoded_body
            assert "中文" in decoded_body
            assert "🚀" in decoded_body


class TestGmailServiceIntegration:
    """Integration-style tests for complete Gmail service workflows."""

    def test_complete_email_send_workflow(self, mocker, app):
        """Test complete workflow from service creation to email sending."""
        with app.app_context():
            # Setup
            to_email = "recipient@example.com"
            subject = "Integration Test"
            body_text = "This is an integration test"

            # Mock service
            mock_service = Mock()
            mock_users = Mock()
            mock_messages = Mock()
            mock_send = Mock()
            mock_execute = Mock(return_value={"id": "integration_test_id"})

            mock_service.users.return_value = mock_users
            mock_users.messages.return_value = mock_messages
            mock_messages.send.return_value = mock_send
            mock_send.execute = mock_execute

            mocker.patch(
                "src.services.gmail_service.get_gmail_service",
                return_value=mock_service,
            )

            # Execute
            result = send_email(to_email, subject, body_text)

            # Verify
            assert result["success"] is True
            assert result["message_id"] == "integration_test_id"
            mock_send.execute.assert_called_once()

    def test_send_email_with_service_account_mocked(self, mocker, app):
        """send_email uses get_gmail_service; the client can be mocked end-to-end."""
        with app.app_context():
            mock_service = Mock()
            mock_users = Mock()
            mock_messages = Mock()
            mock_send = Mock()
            mock_execute = Mock(return_value={"id": "refreshed_id"})

            mock_service.users.return_value = mock_users
            mock_users.messages.return_value = mock_messages
            mock_messages.send.return_value = mock_send
            mock_send.execute = mock_execute

            mocker.patch(
                "src.services.gmail_service.get_gmail_service",
                return_value=mock_service,
            )
            mock_logger = mocker.patch("flask.current_app.logger")

            result = send_email("test@example.com", "Test", "Body")

            assert result["success"] is True
            assert result["message_id"] == "refreshed_id"
            mock_logger.info.assert_called_once()
