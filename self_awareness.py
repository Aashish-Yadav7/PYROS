"""
self_awareness.py
Lets Pyros read her own source code and crash logs directly - so you can
ask her things like "what does your memory.py do" or "why did you crash
earlier" and she can actually look at the real file/log and answer,
without you ever needing to open a terminal.
"""

import os

PYROS_DIR = os.path.dirname(os.path.abspath(__file__))

# Files Pyros is allowed to read about herself. Deliberately a fixed list
# (not "read anything on the computer") - she can see her own code, not
# your entire filesystem.
READABLE_FILES = [
    "main.py", "brain.py", "memory.py", "personality.py", "identity.py",
    "awareness.py", "news.py", "voice.py", "config.py", "self_awareness.py",
    "globe.html", "crash_log.txt",
]

MAX_FILE_CHARS = 6000  # keep file contents from blowing up the prompt


def list_own_files() -> list[str]:
    """Returns the list of files Pyros can read about herself."""
    return [f for f in READABLE_FILES if os.path.exists(os.path.join(PYROS_DIR, f))]


def read_own_file(filename: str) -> str:
    """
    Read one of Pyros's own source files. Returns the content (truncated
    if very long), or an error message if the file isn't allowed/found.
    """
    filename = filename.strip()
    if filename not in READABLE_FILES:
        return f"(I don't have '{filename}' in my readable file list.)"

    path = os.path.join(PYROS_DIR, filename)
    if not os.path.exists(path):
        return f"(I don't see '{filename}' on disk right now.)"

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) > MAX_FILE_CHARS:
            content = content[:MAX_FILE_CHARS] + "\n... (truncated, file is longer)"
        return content
    except Exception as e:
        return f"(Couldn't read '{filename}': {e})"


def get_recent_crash_log(max_chars: int = 3000) -> str:
    """
    Reads the tail of crash_log.txt (if it exists) - the actual errors
    from any recent crashes, so Pyros can explain what went wrong.
    """
    path = os.path.join(PYROS_DIR, "crash_log.txt")
    if not os.path.exists(path):
        return "(No crash log exists yet - nothing has crashed.)"

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            return "(Crash log exists but is empty - no crashes recorded.)"
        return content[-max_chars:]
    except Exception as e:
        return f"(Couldn't read crash log: {e})"


# --- Quick manual test ---
if __name__ == "__main__":
    print("Readable files:", list_own_files())
    print()
    print("--- Reading identity.py ---")
    print(read_own_file("identity.py")[:300])
    print()
    print("--- Crash log ---")
    print(get_recent_crash_log())