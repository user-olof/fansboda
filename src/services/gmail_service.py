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


def get_gmail_service():
    """Get authenticated Gmail service instance."""
    creds = None

    # Path to token file (stores user access/refresh tokens)
    token_path = os.path.join(os.path.dirname(__file__), "..", "..", "token.pickle")
    credentials_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "credentials.json"
    )

    # Try to load existing token
    creds = _load_existing_token(token_path)

    # Validate and refresh if needed
    creds = _validate_and_refresh_credentials(creds)

    # If no valid credentials, try service account or OAuth
    if not creds:
        # Try service account first (for server-to-server with DWD)
        service_account_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
        gmail_sender_email = os.getenv("GMAIL_SENDER_EMAIL")

        if service_account_path and os.path.exists(service_account_path):
            try:
                # Load service account credentials
                service_account_creds = (
                    service_account.Credentials.from_service_account_file(
                        service_account_path, scopes=SCOPES
                    )
                )

                # If GMAIL_SENDER_EMAIL is set, impersonate that user (Domain-Wide Delegation)
                if gmail_sender_email:
                    creds = service_account_creds.with_subject(gmail_sender_email)
                    current_app.logger.info(
                        f"Using service account with DWD to impersonate {gmail_sender_email}"
                    )
                else:
                    # Without impersonation, service account won't work for Gmail API
                    current_app.logger.warning(
                        "GMAIL_SENDER_EMAIL not set. Service account requires domain-wide delegation "
                        "and user impersonation for Gmail API."
                    )
                    creds = None
            except Exception as e:
                current_app.logger.warning(f"Service account auth failed: {e}")
                creds = None

        # Fall back to OAuth flow if service account doesn't work
        creds = _validate_and_refresh_credentials(creds)
        if not creds:
            if os.path.exists(credentials_path):
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, SCOPES
                    )
                    # In production/Docker, this won't work - need stored credentials
                    creds = flow.run_local_server(port=8080)

                    # Save credentials for next run
                    with open(token_path, "wb") as token:
                        pickle.dump(creds, token)
                except Exception as e:
                    current_app.logger.error(f"OAuth flow failed: {e}")
                    raise ValueError(
                        "Could not authenticate with Gmail API. Please ensure credentials.json exists and is valid."
                    )

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
