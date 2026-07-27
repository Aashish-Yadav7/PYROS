"""
news.py
Fetches real, current news headlines from multiple sources:
1. Currents API (primary) - richer, filterable by category/country, needs a free key.
2. RSS feeds (fallback) - used automatically if Currents fails or hits its daily limit.

CACHING: results are cached for CACHE_MINUTES. Repeated news questions within
that window reuse the cached result instead of calling the API again — this
keeps usage far below the free daily limit no matter how much you chat.

To add more providers later (GNews, NewsData.io, etc.), just add a new
_get_from_x() function and add it to the fallback chain in get_all_current_news().
"""

import time
import requests
import feedparser
import config

# Free, no-key RSS feeds — used as a reliable fallback.
FEEDS = {
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "Reuters World": "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
}

CACHE_MINUTES = 20  # how long a fetched result stays valid before refreshing
_cache = {"data": None, "timestamp": 0}


# ---------- PRIMARY: Currents API ----------

def _get_from_currents(limit: int = 10) -> list[str] | None:
    """Try fetching headlines from Currents API. Returns None if it fails."""
    if not config.CURRENTS_API_KEY:
        return None

    try:
        response = requests.get(
            "https://api.currentsapi.services/v1/latest-news",
            params={"apiKey": config.CURRENTS_API_KEY, "language": "en"},
            timeout=5,
        )
        data = response.json()
        if data.get("status") == "ok":
            return [article["title"] for article in data["news"][:limit]]
    except Exception as e:
        print(f"[news] Currents API failed: {e}")

    return None


# ---------- FALLBACK: RSS ----------

def _get_from_rss(limit_per_source: int = 5) -> list[str]:
    """Fetch headlines from RSS feeds. Always works, no key needed."""
    all_headlines = []
    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit_per_source]:
                all_headlines.append(f"{entry.title} ({source})")
        except Exception as e:
            print(f"[news] RSS fetch failed for {source}: {e}")
    return all_headlines


# ---------- PUBLIC INTERFACE (with caching) ----------

def get_all_current_news(limit: int = 10) -> str:
    """
    Fetch current headlines, using a cached result if it's still fresh
    (within CACHE_MINUTES). Only calls the actual APIs when the cache
    has expired, to avoid burning through daily request limits.
    """
    now = time.time()
    cache_age_minutes = (now - _cache["timestamp"]) / 60

    if _cache["data"] and cache_age_minutes < CACHE_MINUTES:
        return _cache["data"]  # reuse cached result, no API call made

    headlines = _get_from_currents(limit)
    source_used = "Currents API"

    if not headlines:
        headlines = _get_from_rss(limit_per_source=5)
        source_used = "RSS (fallback)"

    if not headlines:
        return _cache["data"] or "(Couldn't fetch news from any source right now.)"

    headline_lines = "\n".join(f"- {h}" for h in headlines)
    result = f"Current headlines (source: {source_used}):\n{headline_lines}"

    _cache["data"] = result
    _cache["timestamp"] = now
    return result


# --- Quick manual test ---
if __name__ == "__main__":
    print(get_all_current_news())
    print("\n--- calling again immediately (should be instant, from cache) ---")
    print(get_all_current_news())