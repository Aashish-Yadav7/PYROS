"""
weather.py
Real current weather via Weatherstack API.
"""

import time
import requests
import config

CACHE_MINUTES = 15
_cache = {}  # keyed by location string


def get_weather(location: str) -> str:
    """
    Fetch real current weather for a location (city name).
    Returns readable text, or an honest failure message.
    """
    if not getattr(config, "WEATHERSTACK_API_KEY", None):
        return "(No Weatherstack API key configured, so I can't check real weather right now.)"

    cache_key = location.strip().lower()
    cached = _cache.get(cache_key)
    if cached and (time.time() - cached["timestamp"]) / 60 < CACHE_MINUTES:
        return cached["data"]

    try:
        response = requests.get(
            "http://api.weatherstack.com/current",
            params={"access_key": config.WEATHERSTACK_API_KEY, "query": location},
            timeout=6,
        )
        data = response.json()

        if data.get("error"):
            return f"(Couldn't get weather for '{location}': {data['error'].get('info', 'unknown error')})"

        current = data.get("current", {})
        loc = data.get("location", {})

        result = (
            f"Current weather in {loc.get('name', location)}, {loc.get('country', '')}:\n"
            f"- Temperature: {current.get('temperature')}°C (feels like {current.get('feelslike')}°C)\n"
            f"- Condition: {', '.join(current.get('weather_descriptions', []))}\n"
            f"- Humidity: {current.get('humidity')}%\n"
            f"- Wind: {current.get('wind_speed')} km/h\n"
            f"- Local time: {loc.get('localtime')}"
        )

        _cache[cache_key] = {"data": result, "timestamp": time.time()}
        return result

    except Exception as e:
        return f"(Couldn't fetch weather right now: {e})"


# --- Quick manual test ---
if __name__ == "__main__":
    print(get_weather("Bengaluru"))