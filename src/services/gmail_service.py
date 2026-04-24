"""Gmail API service for sending emails."""

import os
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.auth.transport.requests import Request
from email.utils import formataddr
from flask import current_app


# Gmail API scope
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def _validate_and_refresh_credentials(creds):
    """
    Validate credentials and refresh if expired.

    Args:
        creds: Credentials object to validate

    Returns:
        Valid credentials object, or None if invalid and cannot be refreshed
    """
    if not creds:
        return None

    # If credentials are valid, return them
    if creds.valid:
        return creds

    # Try to refresh if expired and has refresh token
    try:
        creds.refresh(Request())
        if creds.valid:
            current_app.logger.info("Credentials refreshed successfully")
    except Exception as e:
        current_app.logger.warning(
            "Could not refresh credentials: %s", e, exc_info=True
        )
        return None

    return creds if creds.valid else None


def _authenticate_with_service_account():
    """
    Authenticate using service account with domain-wide delegation.

    Returns:
        Credentials object if successful, None otherwise
    """
    service_account_path = os.getenv("GMAIL_APPLICATION_CREDENTIALS")
    gmail_sender_email = os.getenv("GMAIL_SENDER_EMAIL")

    current_app.logger.info(
        f"Attempting service account authentication. "
        f"GMAIL_APPLICATION_CREDENTIALS={service_account_path}, "
        f"GMAIL_SENDER_EMAIL={'set' if gmail_sender_email else 'not set'}"
    )

    if not service_account_path:
        current_app.logger.warning(
            "GMAIL_APPLICATION_CREDENTIALS environment variable not set"
        )
        return None

    if not os.path.exists(service_account_path):
        current_app.logger.warning(
            f"Service account key file not found: {service_account_path}"
        )
        return None

    try:
        service_account_creds = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=SCOPES
        )

        if gmail_sender_email:
            creds = service_account_creds.with_subject(gmail_sender_email)
            current_app.logger.info(
                f"Service account credentials created with DWD for {gmail_sender_email}"
            )
            return creds
        else:
            current_app.logger.warning(
                "GMAIL_SENDER_EMAIL not set. Service account requires domain-wide delegation "
                "and user impersonation for Gmail API."
            )
            return None
    except Exception as e:
        current_app.logger.error(f"Service account auth failed: {e}", exc_info=True)
        return None


def get_gmail_service():
    """Get an authenticated Gmail API client.

    Only service-account authentication is supported: set
    ``GMAIL_APPLICATION_CREDENTIALS`` to the service account JSON key path and
    ``GMAIL_SENDER_EMAIL`` to the user to impersonate (domain-wide delegation).
    There is no interactive or installed-app user OAuth flow.
    """
    sa_path = os.getenv("GMAIL_APPLICATION_CREDENTIALS")
    if not sa_path:
        raise ValueError(
            "Could not authenticate with Gmail API. "
            "GMAIL_APPLICATION_CREDENTIALS is not set (service account JSON path required)."
        )

    errors = []
    current_app.logger.info("Authenticating to Gmail API with service account")
    try:
        creds = _authenticate_with_service_account()
        creds = _validate_and_refresh_credentials(creds)
        if creds:
            current_app.logger.info("Service account authentication successful")
            return build("gmail", "v1", credentials=creds)
        errors.append("Service account returned no valid credentials")
    except Exception as e:
        current_app.logger.warning("Service account auth failed: %s", e, exc_info=True)
        errors.append(f"Service account auth failed: {e}")

    raise ValueError("Could not authenticate with Gmail API. " + " | ".join(errors))


def send_email(to_email, subject, body_text, from_email=None):
    """
    Send an email using Gmail API.

    Args:
        to_email: Recipient email address
        subject: Email subject
        body_text: Email body text
        from_email: Sender email (defaults to authenticated user)

    Returns:
        dict: Message response from Gmail API
    """
    try:
        service = get_gmail_service()

        # Create message
        message = MIMEText(body_text, "plain", "utf-8")
        message["to"] = to_email
        message["subject"] = subject
        if from_email:
            message["from"] = formataddr(("Metallen AB", os.getenv("GMAIL_SENDER_EMAIL")))

        # Encode message
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        # Send message
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body={"raw": raw_message})
            .execute()
        )

        current_app.logger.info(
            f"Email sent successfully. Message Id: {send_message['id']}"
        )
        return {"success": True, "message_id": send_message["id"]}

    except Exception as e:
        current_app.logger.error(f"Error sending email: {str(e)}")
        return {"success": False, "error": str(e)}
