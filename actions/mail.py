"""
actions/mail.py

Sends real emails through the user's Gmail account via the Gmail API.
Requires credentials.json in the project root (see setup instructions
given separately) and the account added as a test user in Google Cloud
Console while the app is unverified.
"""
import os
import base64
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "pyros_data/token.json"


def _get_gmail_service():
    creds = None
    os.makedirs("pyros_data", exist_ok=True)

    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(
                    "credentials.json not found in project root. Gmail sending is not set up yet."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token_file:
            token_file.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def send_email(to: str, subject: str, body: str) -> str:
    try:
        service = _get_gmail_service()

        message = MIMEText(body)
        message["to"] = to
        message["subject"] = subject
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        service.users().messages().send(userId="me", body={"raw": raw_message}).execute()
        return f"Email sent to {to} with subject '{subject}'."

    except FileNotFoundError as e:
        return str(e)
    except Exception as e:
        return f"Failed to send email: {e}"


TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_email",
        "description": "Compose and send a real email through the user's Gmail account.",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email address"},
                "subject": {"type": "string", "description": "Email subject line"},
                "body": {"type": "string", "description": "Email body text"},
            },
            "required": ["to", "subject", "body"],
        },
    },
}