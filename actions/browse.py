"""
actions/browse.py

Opens a specific URL, or searches Google if given a topic instead of a link.
"""
import webbrowser
import re

URL_PATTERN = re.compile(r"^https?://|^www\.")


def open_url(query: str) -> str:
    query = query.strip()

    if URL_PATTERN.match(query):
        url = query if query.startswith("http") else f"https://{query}"
        webbrowser.open(url)
        return f"Opened {url}"

    webbrowser.open(f"https://www.google.com/search?q={query}")
    return f"Searched Google for: {query}"


TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "open_url",
        "description": "Open a specific website URL, or search Google if given a topic instead of a link.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "A URL like 'youtube.com', or a search topic"}
            },
            "required": ["query"],
        },
    },
}