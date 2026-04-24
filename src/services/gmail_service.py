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
    try:
        creds.refresh(Request())
        if creds.valid:
            current_app.logger.info("Credentials refreshed successfully")
    except Exception as e:
        current_app.logger.warning("Could not refresh credentials: %s", e, exc_info=True)
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
    """Get authenticated Gmail service instance.

    Priority:
    1) Service account (domain-wide delegation) via GMAIL_APPLICATION_CREDENTIALS
    2) OAuth token cache (token.pickle)
    3) OAuth client secrets flow (credentials.json)
    """
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..")
    token_path = os.path.join(base_dir, "token.pickle")
    credentials_path = os.path.join(base_dir, "credentials.json")

    errors = []

    # 1) Service account first
    sa_path = os.getenv("GMAIL_APPLICATION_CREDENTIALS")
    if sa_path:
        current_app.logger.info("Trying Gmail auth with service account first")
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
    else:
        current_app.logger.info("GMAIL_APPLICATION_CREDENTIALS not set; skipping service account auth")

    # 2) Existing OAuth token
    try:
        current_app.logger.info("Trying existing OAuth token")
        creds = _load_existing_token(token_path)
        creds = _validate_and_refresh_credentials(creds)
        if creds:
            current_app.logger.info("OAuth token authentication successful")
            return build("gmail", "v1", credentials=creds)
        errors.append("No valid OAuth token found")
    except Exception as e:
        current_app.logger.warning("OAuth token auth failed: %s", e, exc_info=True)
        errors.append(f"OAuth token auth failed: {e}")

    # 3) OAuth client secrets fallback
    try:
        current_app.logger.info("Trying OAuth credentials.json flow")
        creds = _authenticate_with_oauth_flow(credentials_path, token_path)
        creds = _validate_and_refresh_credentials(creds)
        if creds:
            current_app.logger.info("OAuth flow authentication successful")
            return build("gmail", "v1", credentials=creds)
        errors.append("OAuth flow returned no valid credentials")
    except Exception as e:
        current_app.logger.warning("OAuth flow failed: %s", e, exc_info=True)
        errors.append(f"OAuth flow failed: {e}")

    # Final failure
    raise ValueError(
        "Could not authenticate with Gmail API. "
        + " | ".join(errors)
    )


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
