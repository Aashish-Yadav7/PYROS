"""
actions/launch.py

Opens applications on your computer, cross-platform, with browser fallback.
"""
import subprocess
import webbrowser
import platform

SYSTEM = platform.system()

WINDOWS_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "spotify": "spotify.exe",
    "vs code": "code",
    "vscode": "code",
    "word": "winword.exe",
    "excel": "excel.exe",
    "powerpoint": "powerpnt.exe",
    "chrome": "chrome.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "settings": "start ms-settings:",
    "task manager": "taskmgr.exe",
}

MAC_APPS = {
    "notes": "Notes",
    "calculator": "Calculator",
    "spotify": "Spotify",
    "vs code": "Visual Studio Code",
    "word": "Microsoft Word",
    "excel": "Microsoft Excel",
    "chrome": "Google Chrome",
    "safari": "Safari",
}

FALLBACK_URLS = {
    "spotify": "https://open.spotify.com",
    "whatsapp": "https://web.whatsapp.com",
    "instagram": "https://instagram.com",
    "gmail": "https://mail.google.com",
    "youtube": "https://youtube.com",
    "netflix": "https://netflix.com",
    "discord": "https://discord.com/app",
    "chrome": "https://google.com",
}


def open_application(app_name: str) -> str:
    key = app_name.strip().lower()

    if SYSTEM == "Windows":
        if key in WINDOWS_APPS:
            try:
                subprocess.Popen(WINDOWS_APPS[key], shell=True)
                return f"Opened {app_name}."
            except Exception:
                pass

    elif SYSTEM == "Darwin":
        if key in MAC_APPS:
            try:
                subprocess.Popen(["open", "-a", MAC_APPS[key]])
                return f"Opened {app_name}."
            except Exception:
                pass

    elif SYSTEM == "Linux":
        try:
            subprocess.Popen([key])
            return f"Opened {app_name}."
        except Exception:
            pass

    if key in FALLBACK_URLS:
        webbrowser.open(FALLBACK_URLS[key])
        return f"Opened {app_name} in your browser."

    webbrowser.open(f"https://www.google.com/search?q={app_name}")
    return f"Wasn't sure what '{app_name}' is — searched it on Google."


TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "open_application",
        "description": "Open an application on the user's computer, or its website if not installed.",
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "description": "Name of the app, e.g. 'chrome', 'spotify'"}
            },
            "required": ["app_name"],
        },
    },
}