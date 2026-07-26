"""
actions/launch.py

Opens applications. On Windows, tries the 'start' command first (finds
installed apps via the registry regardless of PATH), then built-in exe
names, then falls back to the app's website, then a Google search.
"""
import subprocess
import webbrowser
import platform

SYSTEM = platform.system()

WINDOWS_START_NAMES = {
    "chrome": "chrome",
    "spotify": "spotify",
    "vs code": "code",
    "vscode": "code",
    "word": "winword",
    "excel": "excel",
    "powerpoint": "powerpnt",
    "discord": "discord",
    "steam": "steam",
    "whatsapp": "whatsapp",
}

WINDOWS_BUILTIN = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "settings": "start ms-settings:",
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


def _try_windows_start(name: str) -> bool:
    try:
        result = subprocess.run(
            f'start "" "{name}"', shell=True, capture_output=True, timeout=5, text=True
        )
        return result.returncode == 0
    except Exception:
        return False


def open_application(app_name: str) -> str:
    key = app_name.strip().lower()

    if SYSTEM == "Windows":
        if key in WINDOWS_START_NAMES:
            if _try_windows_start(WINDOWS_START_NAMES[key]):
                return f"Opened {app_name}."

        if key in WINDOWS_BUILTIN:
            try:
                subprocess.Popen(WINDOWS_BUILTIN[key], shell=True)
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
        return f"Couldn't find {app_name} installed — opened it in your browser instead."

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