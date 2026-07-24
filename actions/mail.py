"""
actions/mail.py

Sends real emails through YOUR Gmail account using Google's official API.

ONE-TIME SETUP REQUIRED before this works (takes ~5 minutes):
1. Go to https://console.cloud.google.com/
2. Create a new project (any name, e.g. "PYROS")
3. Enable the "Gmail API" for that project (search it in the top search bar)
4. Go to "Credentials" -> "Create Credentials" -> "OAuth client ID"
   - Application type: Desktop app
   - Name: PYROS
5. Download the resulting JSON file, rename it to credentials.json,
   and place it in your PYROS project root (same level as main.py)
6. Add credentials.json to .gitignore immediately — this file is sensitive,
   just like your API keys, and must never be committed to GitHub

The FIRST time you send an email, a browser window will pop up asking you
to log into your Google account and approve access — this is normal and
only happens once. After that, a token.json file is saved locally so you
won't need to log in again.
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
                    "credentials.json not found. See the setup instructions "
                    "at the top of actions/mail.py to get this file from Google Cloud Console."
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        with open(TOKEN_FILE, "w") as token_file:
            token_file.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def send_email(to: str, subject: str, body: str) -> str:
    """Sends a real email through the user's Gmail account."""
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