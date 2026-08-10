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

# Free, no-key RSS feeds — used as a reliable fallback AND to help reach
# a larger total headline count for the GUI news panel.
FEEDS = {
    "BBC World": "http://feeds.bbci.co.uk/news/world/rss.xml",
    "BBC Business": "http://feeds.bbci.co.uk/news/business/rss.xml",
    "BBC Technology": "http://feeds.bbci.co.uk/news/technology/rss.xml",
    "Reuters World": "https://www.reutersagency.com/feed/?best-topics=world&post_type=best",
    "NYT World": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
}

CACHE_MINUTES = 20  # how long a fetched result stays valid before refreshing
_cache = {"data": None, "timestamp": 0}
_gui_cache = {"data": None, "timestamp": 0}
_region_cache = {}  # keyed by region query string, each entry {"data":..., "timestamp":...}

# Common country name -> 2-letter ISO code, for Currents API's country filter.
# Not exhaustive - anything not listed here falls back to keyword search,
# which still works for regions/cities/countries not in this short list.
COUNTRY_CODES = {
    "united states": "US", "usa": "US", "america": "US",
    "united kingdom": "GB", "uk": "GB", "britain": "GB",
    "india": "IN", "japan": "JP", "china": "CN", "france": "FR",
    "germany": "DE", "italy": "IT", "spain": "ES", "russia": "RU",
    "canada": "CA", "australia": "AU", "brazil": "BR", "mexico": "MX",
    "south korea": "KR", "korea": "KR", "pakistan": "PK", "israel": "IL",
    "iran": "IR", "iraq": "IQ", "ukraine": "UA", "egypt": "EG",
    "south africa": "ZA", "nigeria": "NG", "indonesia": "ID",
    "saudi arabia": "SA", "turkey": "TR", "netherlands": "NL",
    "sweden": "SE", "norway": "NO", "poland": "PL", "philippines": "PH",
    "vietnam": "VN", "thailand": "TH", "singapore": "SG", "argentina": "AR",
}


# ---------- PRIMARY: Currents API ----------

def _get_from_currents(limit: int = 10) -> list[dict] | None:
    """Try fetching headlines + descriptions + URLs from Currents API. Returns None if it fails."""
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
            return [
                {
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "category": ", ".join(article.get("category", [])) or "general",
                    "url": article.get("url", ""),
                }
                for article in data["news"][:limit]
            ]
    except Exception as e:
        print(f"[news] Currents API failed: {e}")

    return None


# ---------- FALLBACK: RSS ----------

def _get_from_rss(limit_per_source: int = 5) -> list[dict]:
    """Fetch headlines + summaries + URLs from RSS feeds. Always works, no key needed."""
    all_articles = []
    for source, url in FEEDS.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:limit_per_source]:
                all_articles.append({
                    "title": entry.title,
                    "description": getattr(entry, "summary", ""),
                    "category": source,
                    "url": getattr(entry, "link", ""),
                })
        except Exception as e:
            print(f"[news] RSS fetch failed for {source}: {e}")
    return all_articles


# ---------- REGION-SPECIFIC: Currents /v1/search ----------

def _get_from_currents_search(region: str, limit: int = 10) -> list[dict] | None:
    """
    Search Currents API for news about a specific region/country/topic.
    Uses the proper country code if we recognize the name, otherwise falls
    back to free-text keyword search (still works for cities, regions,
    or countries not in our short COUNTRY_CODES list).
    """
    if not config.CURRENTS_API_KEY:
        return None

    region_lower = region.strip().lower()
    country_code = COUNTRY_CODES.get(region_lower)

    params = {"apiKey": config.CURRENTS_API_KEY, "language": "en"}
    if country_code:
        params["country"] = country_code
    else:
        params["keywords"] = region

    try:
        response = requests.get(
            "https://api.currentsapi.services/v1/search",
            params=params,
            timeout=6,
        )
        data = response.json()
        if data.get("status") == "ok":
            return [
                {
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "category": ", ".join(article.get("category", [])) or "general",
                    "url": article.get("url", ""),
                }
                for article in data["news"][:limit]
            ]
    except Exception as e:
        print(f"[news] Currents region search failed: {e}")

    return None


def get_news_for_region(region: str, limit: int = 10) -> str:
    """
    Fetch current news specifically about a region/country (e.g. "Japan",
    "France", "Mumbai"), formatted as readable text for the LLM. Cached per
    region so repeated questions about the same place don't re-hit the API.
    """
    now = time.time()
    cache_key = region.strip().lower()
    cached = _region_cache.get(cache_key)
    if cached and (now - cached["timestamp"]) / 60 < CACHE_MINUTES:
        return cached["data"]

    articles = _get_from_currents_search(region, limit)

    if not articles:
        result = f"(Couldn't find current news specifically about {region} right now.)"
        return result

    blocks = []
    for i, article in enumerate(articles, 1):
        desc = article["description"].strip()
        block = f"{i}. {article['title']} [{article['category']}]"
        if desc:
            block += f"\n   Details: {desc}"
        blocks.append(block)

    result = f"Current news about {region} (source: Currents API):\n" + "\n".join(blocks)
    _region_cache[cache_key] = {"data": result, "timestamp": now}
    return result


# ---------- PUBLIC INTERFACE for the LLM (with caching) ----------

def get_all_current_news(limit: int = 10) -> str:
    """
    Fetch current news (headline + description) as readable text for the LLM.
    Cached for CACHE_MINUTES to avoid burning through daily API limits.
    """
    now = time.time()
    cache_age_minutes = (now - _cache["timestamp"]) / 60

    if _cache["data"] and cache_age_minutes < CACHE_MINUTES:
        return _cache["data"]

    articles = _get_from_currents(limit)
    source_used = "Currents API"

    if not articles:
        articles = _get_from_rss(limit_per_source=5)
        source_used = "RSS (fallback)"

    if not articles:
        return _cache["data"] or "(Couldn't fetch news from any source right now.)"

    blocks = []
    for i, article in enumerate(articles, 1):
        desc = article["description"].strip()
        block = f"{i}. {article['title']} [{article['category']}]"
        if desc:
            block += f"\n   Details: {desc}"
        blocks.append(block)

    result = f"Current news (source: {source_used}):\n" + "\n".join(blocks)

    _cache["data"] = result
    _cache["timestamp"] = now
    return result


# ---------- PUBLIC INTERFACE for the GUI news panel ----------

def get_headlines_for_display(target_count: int = 200) -> list[dict]:
    """
    Returns a list of real article dicts (title, url, category) for the GUI
    news panel, each with a real clickable link. Combines Currents API +
    multiple RSS feeds to get as close to target_count as real data allows
    (RSS feeds only contain what's currently published — an exact 200 isn't
    guaranteed, this returns everything genuinely available, deduplicated).
    Cached for CACHE_MINUTES.
    """
    now = time.time()
    cache_age_minutes = (now - _gui_cache["timestamp"]) / 60

    if _gui_cache["data"] and cache_age_minutes < CACHE_MINUTES:
        return _gui_cache["data"]

    combined = []
    seen_titles = set()

    currents_articles = _get_from_currents(limit=target_count) or []
    for article in currents_articles:
        if article["title"] not in seen_titles:
            combined.append(article)
            seen_titles.add(article["title"])

    if len(combined) < target_count:
        rss_articles = _get_from_rss(limit_per_source=50)
        for article in rss_articles:
            if article["title"] not in seen_titles:
                combined.append(article)
                seen_titles.add(article["title"])
            if len(combined) >= target_count:
                break

    _gui_cache["data"] = combined
    _gui_cache["timestamp"] = now
    return combined