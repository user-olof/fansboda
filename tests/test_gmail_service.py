"""
Comprehensive test suite for Gmail service.

This module tests all Gmail service functionality including:
- Token loading and validation
- Credential refresh
- Service account authentication
- OAuth flow authentication
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
    _load_existing_token,
    _validate_and_refresh_credentials,
    get_gmail_service,
    send_email,
    SCOPES,
)


class TestLoadExistingToken:
    """Test cases for _load_existing_token function."""

    def test_load_existing_token_success(self, mocker, app):
        """Test successfully loading an existing token."""
        with app.app_context():
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = True
            token_path = "/fake/path/token.pickle"

            # Mock os.path.exists to return True
            mocker.patch("os.path.exists", return_value=True)
            # Mock pickle.load
            mocker.patch("builtins.open", mock_open())
            mock_pickle_load = mocker.patch(
                "src.services.gmail_service.pickle.load", return_value=mock_creds
            )

            result = _load_existing_token(token_path)

            assert result == mock_creds
            mock_pickle_load.assert_called_once()

    def test_load_existing_token_file_not_exists(self, mocker, app):
        """Test loading token when file doesn't exist."""
        with app.app_context():
            token_path = "/fake/path/token.pickle"

            # Mock os.path.exists to return False
            mocker.patch("os.path.exists", return_value=False)

            result = _load_existing_token(token_path)

            assert result is None

    def test_load_existing_token_load_error(self, mocker, app):
        """Test handling of pickle load errors."""
        with app.app_context():
            token_path = "/fake/path/token.pickle"
            mock_logger = mocker.patch("flask.current_app.logger")

            # Mock os.path.exists to return True
            mocker.patch("os.path.exists", return_value=True)
            # Mock pickle.load to raise an exception
            mocker.patch("builtins.open", mock_open())
            mocker.patch(
                "src.services.gmail_service.pickle.load",
                side_effect=Exception("Pickle error"),
            )

            result = _load_existing_token(token_path)

            assert result is None
            mock_logger.warning.assert_called_once()


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
            mock_request = mocker.patch("src.services.gmail_service.Request")

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

    def test_credentials_invalid_no_refresh_token(self, app):
        """Test handling of invalid credentials without refresh token."""
        with app.app_context():
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = False
            mock_creds.expired = True
            mock_creds.refresh_token = None

            result = _validate_and_refresh_credentials(mock_creds)

            assert result is None


class TestGetGmailService:
    """Test cases for get_gmail_service function."""

    def test_get_gmail_service_with_existing_valid_token(self, mocker, app):
        """Test getting service with existing valid token."""
        with app.app_context():
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = True
            mock_service = Mock()

            # Mock paths
            mocker.patch(
                "src.services.gmail_service.os.path.join",
                side_effect=lambda *args: "/".join(args),
            )
            # Mock token loading
            mocker.patch(
                "src.services.gmail_service._load_existing_token",
                return_value=mock_creds,
            )
            mocker.patch(
                "src.services.gmail_service._validate_and_refresh_credentials",
                return_value=mock_creds,
            )
            # Mock Gmail API build
            mocker.patch("src.services.gmail_service.build", return_value=mock_service)

            result = get_gmail_service()

            assert result == mock_service

    def test_get_gmail_service_with_service_account(self, mocker, app):
        """Test getting service using service account credentials."""
        with app.app_context():
            mock_service_account_creds = Mock()
            mock_creds_with_subject = Mock(spec=Credentials)
            mock_creds_with_subject.valid = True
            mock_service = Mock()

            # Mock paths
            mocker.patch(
                "src.services.gmail_service.os.path.join",
                side_effect=lambda *args: "/".join(args),
            )
            # Mock no existing token
            mocker.patch(
                "src.services.gmail_service._load_existing_token", return_value=None
            )
            # Mock environment variables
            mocker.patch.dict(
                os.environ,
                {
                    "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service_account.json",
                    "GMAIL_SENDER_EMAIL": "sender@example.com",
                },
            )
            mocker.patch("os.path.exists", return_value=True)
            # Mock service account credentials
            mocker.patch(
                "src.services.gmail_service.service_account.Credentials.from_service_account_file",
                return_value=mock_service_account_creds,
            )
            mock_service_account_creds.with_subject.return_value = (
                mock_creds_with_subject
            )

            # Mock _validate_and_refresh_credentials to return None for None input,
            # so service account path is executed, then return valid creds after with_subject
            def validate_side_effect(creds):
                if creds is None:
                    return None
                return mock_creds_with_subject

            mocker.patch(
                "src.services.gmail_service._validate_and_refresh_credentials",
                side_effect=validate_side_effect,
            )
            # Mock Gmail API build
            mocker.patch("src.services.gmail_service.build", return_value=mock_service)
            mock_logger = mocker.patch("flask.current_app.logger")

            result = get_gmail_service()

            assert result == mock_service
            mock_service_account_creds.with_subject.assert_called_once_with(
                "sender@example.com"
            )
            mock_logger.info.assert_called()

    def test_get_gmail_service_service_account_no_impersonation(self, mocker, app):
        """Test service account without GMAIL_SENDER_EMAIL (should fail)."""
        with app.app_context():
            # Mock paths
            mocker.patch(
                "src.services.gmail_service.os.path.join",
                side_effect=lambda *args: "/".join(args),
            )
            # Mock no existing token
            mocker.patch(
                "src.services.gmail_service._load_existing_token", return_value=None
            )
            # Mock environment variables (no GMAIL_SENDER_EMAIL)
            mocker.patch.dict(
                os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/sa.json"}
            )

            # Mock os.getenv to return None for GMAIL_SENDER_EMAIL to ensure it's not set
            def getenv_side_effect(key, default=None):
                if key == "GMAIL_SENDER_EMAIL":
                    return None
                # For other keys, use the actual environment (which we've patched)
                return os.environ.get(key, default)

            mocker.patch(
                "src.services.gmail_service.os.getenv",
                side_effect=getenv_side_effect,
            )
            mock_service_account_creds = Mock()
            mocker.patch(
                "src.services.gmail_service.service_account.Credentials.from_service_account_file",
                return_value=mock_service_account_creds,
            )
            # Mock OAuth flow as fallback
            mock_oauth_creds = Mock(spec=Credentials)
            mock_oauth_creds.valid = True
            # Mock os.path.exists to return True for service account path and credentials.json
            mocker.patch(
                "src.services.gmail_service.os.path.exists",
                side_effect=lambda path: path == "/path/to/sa.json"
                or path.endswith("credentials.json"),
            )
            mock_flow = Mock()
            mock_flow.run_local_server.return_value = mock_oauth_creds
            mocker.patch(
                "src.services.gmail_service.InstalledAppFlow.from_client_secrets_file",
                return_value=mock_flow,
            )

            # Mock _validate_and_refresh_credentials to return None for None input,
            # so service account path is executed, then return valid creds after OAuth fallback
            def validate_side_effect(creds):
                if creds is None:
                    return None
                return mock_oauth_creds

            mocker.patch(
                "src.services.gmail_service._validate_and_refresh_credentials",
                side_effect=validate_side_effect,
            )
            # Mock file writing to prevent pickle errors with Mock objects
            mock_file = Mock()
            mock_file.__enter__ = Mock(return_value=mock_file)
            mock_file.__exit__ = Mock(return_value=None)
            mocker.patch(
                "builtins.open",
                return_value=mock_file,
            )
            # Mock pickle.dump to prevent trying to serialize Mock objects
            mocker.patch("src.services.gmail_service.pickle.dump")
            mock_service = Mock()
            mocker.patch("src.services.gmail_service.build", return_value=mock_service)
            mock_logger = mocker.patch("flask.current_app.logger")

            result = get_gmail_service()

            assert result == mock_service
            mock_logger.warning.assert_called()

    def test_get_gmail_service_oauth_flow(self, mocker, app):
        """Test getting service using OAuth flow."""
        with app.app_context():
            mock_oauth_creds = Mock(spec=Credentials)
            mock_oauth_creds.valid = True
            mock_service = Mock()

            # Mock paths
            mocker.patch(
                "src.services.gmail_service.os.path.join",
                side_effect=lambda *args: "/".join(args),
            )
            # Mock no existing token and no service account
            mocker.patch(
                "src.services.gmail_service._load_existing_token", return_value=None
            )
            mocker.patch.dict(os.environ, {}, clear=True)
            # Mock os.path.exists to return True for credentials.json
            mocker.patch(
                "src.services.gmail_service.os.path.exists",
                side_effect=lambda path: path.endswith("credentials.json"),
            )
            # Mock OAuth flow
            mock_flow = Mock()
            mock_flow.run_local_server.return_value = mock_oauth_creds
            mocker.patch(
                "src.services.gmail_service.InstalledAppFlow.from_client_secrets_file",
                return_value=mock_flow,
            )

            # Mock _validate_and_refresh_credentials to return None for None input,
            # so OAuth path is executed, then return valid creds after OAuth flow
            def validate_side_effect(creds):
                if creds is None:
                    return None
                return mock_oauth_creds

            mocker.patch(
                "src.services.gmail_service._validate_and_refresh_credentials",
                side_effect=validate_side_effect,
            )
            # Mock file writing for token save
            mocker.patch("builtins.open", mock_open())
            # Mock pickle.dump to prevent trying to serialize Mock objects
            mocker.patch("src.services.gmail_service.pickle.dump")
            # Mock Gmail API build
            mocker.patch("src.services.gmail_service.build", return_value=mock_service)

            result = get_gmail_service()

            assert result == mock_service
            mock_flow.run_local_server.assert_called_once_with(port=8080)

    def test_get_gmail_service_oauth_flow_failure(self, mocker, app):
        """Test OAuth flow failure."""
        with app.app_context():
            # Mock paths
            mocker.patch(
                "src.services.gmail_service.os.path.join",
                side_effect=lambda *args: "/".join(args),
            )
            # Mock no existing token and no service account
            mocker.patch(
                "src.services.gmail_service._load_existing_token", return_value=None
            )
            mocker.patch.dict(os.environ, {}, clear=True)
            mocker.patch(
                "os.path.exists",
                side_effect=lambda path: path.endswith("credentials.json"),
            )
            # Mock OAuth flow to fail
            mock_flow = Mock()
            mock_flow.run_local_server.side_effect = Exception("OAuth error")
            mocker.patch(
                "src.services.gmail_service.InstalledAppFlow.from_client_secrets_file",
                return_value=mock_flow,
            )
            mock_logger = mocker.patch("flask.current_app.logger")

            with pytest.raises(
                ValueError, match="Could not authenticate with Gmail API"
            ):
                get_gmail_service()

            mock_logger.error.assert_called_once()

    def test_get_gmail_service_no_valid_credentials(self, mocker, app):
        """Test failure when no valid credentials are found."""
        with app.app_context():
            # Mock paths
            mocker.patch(
                "src.services.gmail_service.os.path.join",
                side_effect=lambda *args: "/".join(args),
            )
            # Mock no existing token and no service account
            mocker.patch(
                "src.services.gmail_service._load_existing_token", return_value=None
            )
            mocker.patch.dict(os.environ, {}, clear=True)
            mocker.patch("os.path.exists", return_value=False)
            mocker.patch(
                "src.services.gmail_service._validate_and_refresh_credentials",
                return_value=None,
            )

            with pytest.raises(
                ValueError, match="Could not authenticate with Gmail API"
            ):
                get_gmail_service()

    def test_get_gmail_service_service_account_file_not_exists(self, mocker, app):
        """Test service account path that doesn't exist."""
        with app.app_context():
            # Mock paths
            mocker.patch(
                "src.services.gmail_service.os.path.join",
                side_effect=lambda *args: "/".join(args),
            )
            # Mock no existing token
            mocker.patch(
                "src.services.gmail_service._load_existing_token", return_value=None
            )
            # Mock environment variables
            mocker.patch.dict(
                os.environ, {"GOOGLE_APPLICATION_CREDENTIALS": "/nonexistent/path.json"}
            )
            mocker.patch("os.path.exists", return_value=False)
            # Should fall back to OAuth or fail
            mock_oauth_creds = Mock(spec=Credentials)
            mock_oauth_creds.valid = True
            mocker.patch(
                "os.path.exists",
                side_effect=lambda path: path.endswith("credentials.json"),
            )
            mock_flow = Mock()
            mock_flow.run_local_server.return_value = mock_oauth_creds
            mocker.patch(
                "src.services.gmail_service.InstalledAppFlow.from_client_secrets_file",
                return_value=mock_flow,
            )
            mocker.patch(
                "src.services.gmail_service._validate_and_refresh_credentials",
                return_value=mock_oauth_creds,
            )
            mocker.patch("builtins.open", mock_open())
            mock_service = Mock()
            mocker.patch("src.services.gmail_service.build", return_value=mock_service)

            result = get_gmail_service()

            assert result == mock_service

    def test_get_gmail_service_service_account_exception(self, mocker, app):
        """Test service account loading exception handling."""
        with app.app_context():
            # Mock paths
            mocker.patch(
                "src.services.gmail_service.os.path.join",
                side_effect=lambda *args: "/".join(args),
            )
            # Mock no existing token
            mocker.patch(
                "src.services.gmail_service._load_existing_token", return_value=None
            )
            # Mock environment variables
            mocker.patch.dict(
                os.environ,
                {"GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service_account.json"},
            )
            # Mock os.path.exists to return True for service account path and credentials.json
            mocker.patch(
                "src.services.gmail_service.os.path.exists",
                side_effect=lambda path: path == "/path/to/service_account.json"
                or path.endswith("credentials.json"),
            )
            # Mock service account to raise exception
            mocker.patch(
                "src.services.gmail_service.service_account.Credentials.from_service_account_file",
                side_effect=Exception("Service account error"),
            )
            mock_logger = mocker.patch("flask.current_app.logger")
            # Should fall back to OAuth
            mock_oauth_creds = Mock(spec=Credentials)
            mock_oauth_creds.valid = True
            mock_flow = Mock()
            mock_flow.run_local_server.return_value = mock_oauth_creds
            mocker.patch(
                "src.services.gmail_service.InstalledAppFlow.from_client_secrets_file",
                return_value=mock_flow,
            )

            # Mock _validate_and_refresh_credentials to return None for None input,
            # so service account path executes, then return valid creds after OAuth
            def validate_side_effect(creds):
                if creds is None:
                    return None
                return mock_oauth_creds

            mocker.patch(
                "src.services.gmail_service._validate_and_refresh_credentials",
                side_effect=validate_side_effect,
            )
            # Mock file writing for token save
            mocker.patch("builtins.open", mock_open())
            # Mock pickle.dump to prevent trying to serialize Mock objects
            mocker.patch("src.services.gmail_service.pickle.dump")
            mock_service = Mock()
            mocker.patch("src.services.gmail_service.build", return_value=mock_service)

            result = get_gmail_service()

            assert result == mock_service
            mock_logger.warning.assert_called()


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

            # Mock credentials
            mock_creds = Mock(spec=Credentials)
            mock_creds.valid = True

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

            # Mock all authentication steps
            mocker.patch(
                "src.services.gmail_service.os.path.join",
                side_effect=lambda *args: "/".join(args),
            )
            mocker.patch(
                "src.services.gmail_service._load_existing_token",
                return_value=mock_creds,
            )
            mocker.patch(
                "src.services.gmail_service._validate_and_refresh_credentials",
                return_value=mock_creds,
            )
            mocker.patch("src.services.gmail_service.build", return_value=mock_service)

            # Execute
            result = send_email(to_email, subject, body_text)

            # Verify
            assert result["success"] is True
            assert result["message_id"] == "integration_test_id"
            mock_send.execute.assert_called_once()

    def test_credential_refresh_during_send(self, mocker, app):
        """Test that credentials are refreshed if expired during email send."""
        with app.app_context():
            # Setup - credentials need refresh
            expired_creds = Mock(spec=Credentials)
            expired_creds.valid = False
            expired_creds.expired = True
            expired_creds.refresh_token = "refresh_token"
            refreshed_creds = Mock(spec=Credentials)
            refreshed_creds.valid = True

            # Mock service
            mock_service = Mock()
            mock_users = Mock()
            mock_messages = Mock()
            mock_send = Mock()
            mock_execute = Mock(return_value={"id": "refreshed_id"})

            mock_service.users.return_value = mock_users
            mock_users.messages.return_value = mock_messages
            mock_messages.send.return_value = mock_send
            mock_send.execute = mock_execute

            # Mock authentication with refresh
            mocker.patch(
                "src.services.gmail_service.os.path.join",
                side_effect=lambda *args: "/".join(args),
            )
            mocker.patch(
                "src.services.gmail_service._load_existing_token",
                return_value=expired_creds,
            )
            mocker.patch(
                "src.services.gmail_service._validate_and_refresh_credentials",
                return_value=refreshed_creds,
            )
            mocker.patch("src.services.gmail_service.build", return_value=mock_service)

            mock_logger = mocker.patch("flask.current_app.logger")

            # Execute
            result = send_email("test@example.com", "Test", "Body")

            # Verify
            assert result["success"] is True
            assert result["message_id"] == "refreshed_id"
            mock_logger.info.assert_called_once()
