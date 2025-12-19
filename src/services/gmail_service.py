"""Gmail API service for sending emails."""

import os
import base64
from email.mime.text import MIMEText
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
from flask import current_app


# Gmail API scope
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def _load_existing_token(token_path):
    """
    Load existing OAuth token from pickle file.

    Args:
        token_path: Path to the token.pickle file

    Returns:
        Credentials object if token exists and is valid, None otherwise
    """
    if not os.path.exists(token_path):
        return None

    try:
        with open(token_path, "rb") as token:
            creds = pickle.load(token)
            return creds
    except Exception as e:
        current_app.logger.warning(f"Could not load token from {token_path}: {e}")
        return None


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
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            current_app.logger.info("Credentials refreshed successfully")
            return creds
        except Exception as e:
            current_app.logger.warning(f"Could not refresh token: {e}")
            return None

    # Credentials are invalid and cannot be refreshed
    return None


def _authenticate_with_service_account():
    """
    Authenticate using service account with domain-wide delegation.

    Returns:
        Credentials object if successful, None otherwise
    """
    service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    gmail_sender_email = os.getenv("GMAIL_SENDER_EMAIL")

    if not service_account_path or not os.path.exists(service_account_path):
        return None

    try:
        service_account_creds = service_account.Credentials.from_service_account_file(
            service_account_path, scopes=SCOPES
        )

        if gmail_sender_email:
            creds = service_account_creds.with_subject(gmail_sender_email)
            current_app.logger.info(
                f"Using service account with DWD to impersonate {gmail_sender_email}"
            )
            return creds
        else:
            current_app.logger.warning(
                "GMAIL_SENDER_EMAIL not set. Service account requires domain-wide delegation "
                "and user impersonation for Gmail API."
            )
            return None
    except Exception as e:
        current_app.logger.warning(f"Service account auth failed: {e}")
        return None


def _authenticate_with_oauth_flow(credentials_path, token_path):
    """
    Authenticate using OAuth flow.

    Args:
        credentials_path: Path to credentials.json file
        token_path: Path to save token.pickle file

    Returns:
        Credentials object if successful

    Raises:
        ValueError: If OAuth flow fails
    """
    if not os.path.exists(credentials_path):
        raise ValueError(
            "Could not authenticate with Gmail API. Please ensure credentials.json exists and is valid."
        )

    try:
        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        creds = flow.run_local_server(port=8080)

        # Save credentials for next run
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

        return creds
    except Exception as e:
        current_app.logger.error(f"OAuth flow failed: {e}")
        raise ValueError(
            "Could not authenticate with Gmail API. Please ensure credentials.json exists and is valid."
        ) from e


def get_gmail_service():
    """Get authenticated Gmail service instance."""
    token_path = os.path.join(os.path.dirname(__file__), "..", "..", "token.pickle")
    credentials_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "credentials.json"
    )

    # Try to load existing token
    creds = _load_existing_token(token_path)
    creds = _validate_and_refresh_credentials(creds)

    # If no valid credentials, try service account or OAuth
    if not creds:
        creds = _authenticate_with_service_account()
        creds = _validate_and_refresh_credentials(creds)

        if not creds:
            creds = _authenticate_with_oauth_flow(credentials_path, token_path)

    # Final validation check
    creds = _validate_and_refresh_credentials(creds)
    if not creds:
        raise ValueError(
            "No valid Gmail API credentials found. Please authenticate first."
        )

    service = build("gmail", "v1", credentials=creds)
    return service


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
            message["from"] = from_email

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
