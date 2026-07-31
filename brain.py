]"""
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
from identity import CREATOR
from personality import get_system_prompt

MODEL_NAME = "llama-3.3-70b-versatile"  # good general-purpose Groq model

# Matches things like "call me Boss", "call me sir", "call me Aashish"
_CALL_ME_PATTERN = re.compile(r"call me (\w+)", flags=re.IGNORECASE)

# Keywords that trigger a real news fetch, so we don't call the API every message
_NEWS_KEYWORDS = (
    "news", "current event", "headline", "happening", "latest update",
    "what's going on", "recent update", "war", "conflict", "tension",
    "election", "attack", "crisis",
)


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


def ask_pyros(user_message: str, chat_history: list, preferred_address: str | None) -> str:
    """
    user_message: latest thing the user typed
    chat_history: list of {"role": "user"/"assistant", "content": "..."} dicts
    preferred_address: what to call the user (e.g. "Boss"), or None if not set yet
    Returns Pyros's reply as a string.
    """
    system_content = get_system_prompt(preferred_address)

    # Only fetch real news if the user is actually asking about it
    if _wants_news(user_message):
        headlines = news.get_all_current_news()
        system_content += f"""

Here is real, current news data to use in your answer:
{headlines}

Rules for answering this news question:
- Only report what's actually in the headlines above. Do NOT invent or guess
  additional headlines, even if the user asks about a specific country/topic
  that isn't well represented above — if it's not there, say you don't have
  current coverage on that specific thing rather than making something up.
- Format your answer as a clean numbered list, one headline per line, like:
  1. Headline one
  2. Headline two
  Do not merge them into a paragraph.
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
            return f"(Pyros couldn't think just now — both keys failed: {e2})"


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