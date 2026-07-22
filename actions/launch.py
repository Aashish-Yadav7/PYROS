"""
actions/launch.py

Opens applications on your computer. If an app isn't found locally,
falls back to opening its web version in your browser, and if that's
not known either, falls back to a Google search — so the request never
just fails silently.

This file also defines TOOL_SCHEMA, the JSON description the model uses
to know this tool exists and how to call it. This is the "function calling"
concept from your notes — the model doesn't run Python code itself, it just
outputs a request like {"app_name": "spotify"} and orchestrator.py runs
the actual function.
"""
import subprocess
import webbrowser
import platform
import shutil

SYSTEM = platform.system()  # "Windows", "Darwin" (Mac), or "Linux"

# Map common spoken names to actual executable names per OS.
# Add more entries here as you find apps you use often.
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
}


def _is_installed_windows(exe_name: str) -> bool:
    """Checks if the executable actually exists on PATH before trying to launch it."""
    return shutil.which(exe_name) is not None or exe_name.startswith("start ")


def open_application(app_name: str) -> str:
    """
    Main entry point. Tries, in order:
    1. Launch it as an installed desktop app
    2. Open its website if we have one mapped
    3. Google search for it as a last resort
    """
    key = app_name.strip().lower()

    if SYSTEM == "Windows":
        if key in WINDOWS_APPS:
            command = WINDOWS_APPS[key]
            try:
                subprocess.Popen(command, shell=True)
                return f"Opened {app_name}."
            except Exception:
                pass  # fall through to next option

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
    return f"Wasn't sure what '{app_name}' is — searched it on Google so you can find it."


# ---------------------------------------------------------------------------
# Tool schema — this is what gets registered with the model router so the
# model knows this capability exists and exactly what arguments to send.
# ---------------------------------------------------------------------------

TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "open_application",
        "description": (
            "Open an application on the user's computer, such as Spotify, Notepad, "
            "VS Code, Word, or a browser. Falls back to the web version or a Google "
            "search if the app isn't found locally."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "app_name": {
                    "type": "string",
                    "description": "Name of the app to open, e.g. 'spotify', 'notepad', 'chrome'",
                }
            },
            "required": ["app_name"],
        },
    },
}