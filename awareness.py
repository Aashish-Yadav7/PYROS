"""
awareness.py
Gives Pyros grounding in the real world: current date/time and approximate
location (detected automatically via IP, no manual input needed).
"""

from datetime import datetime
from datetime import datetime
import requests
from identity import MANUAL_LOCATION

_location_cache = None  # avoid hitting the API on every single message
_location_attempted = False  # only try once per run, even if it fails


def get_current_datetime() -> str:
    """Returns a human-readable current date and time."""
    now = datetime.now()
    return now.strftime("%A, %d %B %Y, %I:%M %p")


def get_location() -> dict:
    """
    Returns location as: manual override (if set in identity.py) > cached
    result > freshly IP-detected result > unknown fallback.
    """
    global _location_cache, _location_attempted

    if MANUAL_LOCATION:
        parts = [p.strip() for p in MANUAL_LOCATION.split(",")]
        return {
            "city": parts[0] if len(parts) > 0 else "unknown",
            "region": parts[1] if len(parts) > 1 else "unknown",
            "country": parts[2] if len(parts) > 2 else "unknown",
        }

    if _location_cache:
        return _location_cache
    if _location_attempted:
        return {"city": "unknown", "region": "unknown", "country": "unknown"}

    _location_attempted = True

    try:
        response = requests.get("https://ip-api.com/json/", timeout=3)
        data = response.json()
        if data.get("status") == "success":
            _location_cache = {
                "city": data.get("city", "unknown"),
                "region": data.get("regionName", "unknown"),
                "country": data.get("country", "unknown"),
            }
            return _location_cache
    except Exception as e:
        print(f"[awareness] Location auto-detection failed once (won't retry this session): {e}")

    return {"city": "unknown", "region": "unknown", "country": "unknown"}


def get_context_string() -> str:
    """
    Returns a ready-to-use text block summarizing real-world context,
    meant to be injected into the system prompt so Pyros always knows
    the current date/time and where her creator is.
    """
    location = get_location()
    location_str = f"{location['city']}, {location['region']}, {location['country']}"
    return (
        f"Current date and time: {get_current_datetime()}\n"
        f"Approximate current location (auto-detected via IP): {location_str}"
    )


# --- Quick manual test ---
if __name__ == "__main__":
    print(get_context_string())