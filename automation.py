"""
automation.py
Lets Pyros actually DO things on your computer: type into whatever window
has focus, open and write in Notepad, and send real WhatsApp messages.

WHATSAPP: uses WhatsApp's own official "click-to-chat" link format
(wa.me/<number>?text=<message>) rather than trying to script WhatsApp's
UI directly. This is far more reliable - Meta's own feature does the
work of opening the right chat with the message pre-filled; we only need
to press Enter to actually send it. WhatsApp deliberately never
auto-sends from this link (that's their own anti-spam design), so we
simulate the Enter press ourselves after the page loads.
"""

import re
import subprocess
import time
import urllib.parse
import webbrowser

import pyautogui

# Small safety delay so a window has time to actually open/focus before
# we start typing into it - typing too fast can lose the first few chars.
WINDOW_OPEN_DELAY = 1.5
WHATSAPP_LOAD_DELAY = 4.0  # WhatsApp Web/Desktop needs longer to load a chat

pyautogui.FAILSAFE = True  # moving mouse to a screen corner aborts - safety net


def type_into_focused_window(text: str, interval: float = 0.02) -> None:
    """
    Types the given text into whatever window currently has focus.
    Does NOT open or switch windows - the user (or another function)
    is responsible for making sure the right window is focused first.
    """
    pyautogui.write(text, interval=interval)


def press_enter() -> None:
    """Presses Enter in the currently focused window."""
    pyautogui.press("enter")


# ---------- NOTEPAD ----------

def open_notepad() -> None:
    """Opens a fresh Notepad window."""
    subprocess.Popen(["notepad.exe"])
    time.sleep(WINDOW_OPEN_DELAY)


def open_notepad_and_type(text: str) -> None:
    """Opens Notepad and types the given text into it."""
    open_notepad()
    type_into_focused_window(text)


# ---------- WHATSAPP ----------

def _clean_phone_number(phone: str) -> str:
    """
    WhatsApp's click-to-chat link needs digits only - no +, spaces,
    dashes, or parentheses. This strips all of that.
    """
    return re.sub(r"[^\d]", "", phone)


def send_whatsapp_message(phone_number: str, message: str) -> str:
    """
    Opens a WhatsApp chat with the given phone number, with the message
    pre-filled, then automatically presses Enter to actually send it.

    phone_number: full international format, e.g. "+91 98765 43210" or
                  "919876543210" - punctuation/spaces are cleaned automatically.
    message: the text to send.

    Returns a status string describing what happened.
    """
    clean_number = _clean_phone_number(phone_number)
    if not clean_number:
        return "That doesn't look like a valid phone number - couldn't send."

    encoded_message = urllib.parse.quote(message)
    url = f"https://wa.me/{clean_number}?text={encoded_message}"

    webbrowser.open(url)
    time.sleep(WHATSAPP_LOAD_DELAY)  # give WhatsApp time to open and load the chat

    press_enter()  # WhatsApp only pre-fills the message - this is what actually sends it

    return f"Sent to {phone_number}: \"{message}\""


# --- Quick manual test ---
if __name__ == "__main__":
    print("Testing automation.py")
    print()
    print("1. Testing Notepad...")
    open_notepad_and_type("This was typed automatically by Pyros.")
    print("   Check if Notepad opened with that text.")
    print()
    print("2. Testing WhatsApp (edit the number below to your own first!)...")
    # result = send_whatsapp_message("+91XXXXXXXXXX", "This is a test message from Pyros.")
    # print("  ", result)
    print("   (commented out by default - uncomment and add a real number to test)")