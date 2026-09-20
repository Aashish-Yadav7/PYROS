"""
brain.py
Pyros's core thinking module. Sends messages to an LLM provider and returns a reply.
Handles automatic key rotation if a request fails (e.g. rate limit).

Primary provider: Groq (fast, free tier generous).
If Groq fails on both keys, you can extend this to fall back to Mistral, etc.
"""

import re
from groq import Groq
import config
import news
import self_awareness
import weather
from identity import CREATOR
from personality import get_system_prompt

MODEL_NAME = "openai/gpt-oss-120b"  # Groq deprecated llama-3.3-70b-versatile in June 2026

# Matches things like "call me Boss", "call me sir", "call me Aashish"
_CALL_ME_PATTERN = re.compile(r"call me (\w+)", flags=re.IGNORECASE)

# Matches "news from/in/about X", "what's happening in X", etc. to extract
# a region/country name for filtered news search.
_REGION_PATTERNS = [
    re.compile(r"news (?:from|in|about) ([a-zA-Z\s]+?)(?:[\?\.\!]|$)", re.IGNORECASE),
    re.compile(r"happening (?:in|with) ([a-zA-Z\s]+?)(?:[\?\.\!]|$)", re.IGNORECASE),
    re.compile(r"what'?s going on (?:in|with) ([a-zA-Z\s]+?)(?:[\?\.\!]|$)", re.IGNORECASE),
]

# Keywords that trigger a real news fetch, so we don't call the API every message
_NEWS_KEYWORDS = (
    "news", "current event", "current affairs", "affairs", "headline",
    "happening", "latest update", "what's going on", "recent update",
    "war", "conflict", "tension", "election", "attack", "crisis",
)

# Matches "weather in X", "what's the weather in X", etc.
_WEATHER_PATTERN = re.compile(r"weather (?:in|at|for) ([a-zA-Z\s]+?)(?:[\?\.\!]|$)", re.IGNORECASE)


def _detect_weather_location(user_message: str) -> str | None:
    """If the user asked about weather somewhere, return that location."""
    if "weather" not in user_message.lower():
        return None
    match = _WEATHER_PATTERN.search(user_message)
    return match.group(1).strip() if match else None


# Matches "open notepad and write/type X", "notepad: X"
_NOTEPAD_PATTERN = re.compile(
    r"notepad.*?(?:write|type)\s+(.+)", re.IGNORECASE
)

# Matches "send whatsapp to <number> saying <message>", "whatsapp <number>: <message>"
_WHATSAPP_PATTERN = re.compile(
    r"whatsapp.*?(?:to\s+)?([\+\d][\d\s\-\(\)]{6,})\s*(?:saying|:|message)\s+(.+)",
    re.IGNORECASE,
)


def detect_notepad_request(user_message: str) -> str | None:
    """If the user asked to type something in Notepad, return that text."""
    match = _NOTEPAD_PATTERN.search(user_message)
    return match.group(1).strip() if match else None


def detect_whatsapp_request(user_message: str) -> tuple[str, str] | None:
    """
    If the user asked to send a WhatsApp message, return (phone_number, message).
    Returns None if the message doesn't match the expected pattern.
    """
    match = _WHATSAPP_PATTERN.search(user_message)
    if match:
        phone = match.group(1).strip()
        message = match.group(2).strip()
        return (phone, message)
    return None


_CRASH_KEYWORDS = (
    "crash", "error", "what went wrong", "why did you close", "why did you stop",
    "bug", "broke", "broken", "exception",
)


def _wants_crash_log(user_message: str) -> bool:
    lowered = user_message.lower()
    return any(k in lowered for k in _CRASH_KEYWORDS)


def _detect_code_file_request(user_message: str) -> str | None:
    """
    If the user asks about a specific one of Pyros's own files (e.g.
    "what does memory.py do", "show me your brain.py"), return that
    filename so we can read the real content.
    """
    lowered = user_message.lower()
    for filename in self_awareness.READABLE_FILES:
        if filename.lower() in lowered:
            return filename
    return None


def _build_client() -> Groq:
    key = config.get_key("groq")
    return Groq(api_key=key)


def detect_address_preference(user_message: str) -> str | None:
    """If the user says 'call me X', return X. Otherwise return None."""
    match = _CALL_ME_PATTERN.search(user_message)
    return match.group(1) if match else None


def _wants_news(user_message: str) -> bool:
    """Check if the user's message is asking about news/current events."""
    lowered = user_message.lower()
    return any(keyword in lowered for keyword in _NEWS_KEYWORDS)


def _detect_news_region(user_message: str) -> str | None:
    """
    If the user asked for news about a specific region/country (e.g.
    "news from Japan", "what's happening in France"), return that region
    name. Otherwise return None (meaning: general/global news).
    """
    for pattern in _REGION_PATTERNS:
        match = pattern.search(user_message)
        if match:
            region = match.group(1).strip()
            # Ignore junk matches like "news happening" with no real region
            if region and len(region) > 1 and region.lower() not in ("here", "now", "today"):
                return region
    return None


def _last_reply_was_news(chat_history: list) -> bool:
    """
    Check if the previous assistant reply was news-based. If so, treat the
    current message as a likely follow-up about news too, even if it doesn't
    contain an obvious keyword (e.g. "these are old" or "give me more").
    """
    if not chat_history:
        return False
    last = chat_history[-1]
    return last.get("role") == "assistant" and "Current news" in last.get("content", "")


def ask_pyros(user_message: str, chat_history: list, preferred_address: str | None) -> str:
    """
    user_message: latest thing the user typed
    chat_history: list of {"role": "user"/"assistant", "content": "..."} dicts
    preferred_address: what to call the user (e.g. "Boss"), or None if not set yet
    Returns Pyros's reply as a string.
    """
    system_content = get_system_prompt(preferred_address)

    # Self-awareness: if asked about her own code or a specific crash/error,
    # give her the REAL file content or crash log instead of letting her guess
    requested_file = _detect_code_file_request(user_message)
    if requested_file:
        file_content = self_awareness.read_own_file(requested_file)
        system_content += f"""

The user is asking about your own file '{requested_file}'. Here is its REAL
current content - use this to answer accurately, don't guess or make up
what the code does:

{file_content}
"""
    elif _wants_crash_log(user_message):
        crash_content = self_awareness.get_recent_crash_log()
        system_content += f"""

The user is asking about an error/crash. Here is the REAL recent crash log
content - use this to explain what actually happened, don't guess:

{crash_content}
"""

    weather_location = _detect_weather_location(user_message)
    if weather_location:
        weather_data = weather.get_weather(weather_location)
        system_content += f"""

The user is asking about real weather. Here is the REAL current weather
data - use this, don't guess or make up conditions:

{weather_data}
"""

    # Fetch real news if the user is asking about it directly, OR if the
    # previous reply was already news-based (likely a follow-up question)
    if _wants_news(user_message) or _last_reply_was_news(chat_history):
        region = _detect_news_region(user_message)
        if region:
            headlines = news.get_news_for_region(region)
        else:
            headlines = news.get_all_current_news()
        system_content += f"""

Here is real, current news data to use in your answer:
{headlines}

Rules for answering this news question:
- Only report what's actually in the data above (titles AND details). Do NOT invent or
  guess additional information, even if the user asks about a specific country/topic
  that isn't well represented above — if it's not there, say you don't have current
  coverage on that specific thing rather than making something up.
- This news feed only has what's listed above — if the user says "these are old" or
  asks for "different" or "more" news, explain that this is everything currently
  available from the feed right now (it refreshes periodically), rather than
  inventing new headlines that aren't in the list.
- By default, format as a clean numbered list of headlines, one per line, like:
  1. Headline one
  2. Headline two
  If the user asks for more detail/content on a specific one, use the "Details" text
  provided for that article to give a real substantive answer, not just the headline.
"""

    messages = [{"role": "system", "content": system_content}]
    messages.extend(chat_history)
    messages.append({"role": "user", "content": user_message})

    client = _build_client()

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            temperature=0.8,
        )
        return response.choices[0].message.content

    except Exception as e:
        print(f"[brain] Groq key failed ({e}), rotating key and retrying...")
        config.rotate_key("groq")
        client = _build_client()
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.8,
            )
            return response.choices[0].message.content
        except Exception as e2:
            return f"(PYROS couldn't get that right now — {e2})"


# --- Quick manual test ---
if __name__ == "__main__":
    import memory

    history = memory.load_history()
    user_name = memory.get_user_name()
    preferred_address = memory.get_preferred_address()

    print("=" * 50)
    print(" PYROS")
    print("=" * 50)

    # --- First-run onboarding: ask name and preferred address directly ---
    if not user_name:
        user_name = input("Pyros: Hey! Before we start, what's your name?\nYou: ").strip()
        memory.set_user_name(user_name)

        # Check if this matches the known creator from identity.py
        if user_name.strip().lower() == CREATOR["name"].strip().lower():
            print(f"[memory] Recognized {user_name} as creator (matches identity.py).")
        else:
            print(f"[memory] Note: '{user_name}' does not match the creator name in identity.py.")

    if not preferred_address:
        preferred_address = input(
            f"Pyros: Nice to meet you, {user_name}. What would you like me to call you "
            f"going forward — your name, \"Boss\", \"Sir\", or anything else?\nYou: "
        ).strip()
        memory.set_preferred_address(preferred_address)

    print(f"\nPyros: Got it, {preferred_address}. Type 'quit' or 'exit' anytime to stop.\n")

    if history:
        print(f"(Loaded {len(history)} previous exchanges)\n")

    while True:
        user_input = input("You: ")
        if user_input.lower() in ("quit", "exit"):
            break

        # Check if the user wants to change their preferred address mid-conversation
        new_preference = detect_address_preference(user_input)
        if new_preference:
            memory.set_preferred_address(new_preference)
            preferred_address = new_preference

        reply = ask_pyros(user_input, history, preferred_address)
        print(f"Pyros: {reply}\n")

        memory.log_exchange(user_input, reply)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})

        # Only store to long-term memory when explicitly asked, to keep storage low
        if "remember" in user_input.lower():
            memory.remember_fact(user_input)