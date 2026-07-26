"""
brain.py
Pyros's core thinking module. Sends messages to an LLM provider and returns a reply.
Handles automatic key rotation if a request fails (e.g. rate limit).

Primary provider: Groq (fast, free tier generous).
If Groq fails on both keys, you can extend this to fall back to Mistral, etc.
"""

from groq import Groq
import config
from personality import get_system_prompt

MODEL_NAME = "llama-3.3-70b-versatile"  # good general-purpose Groq model


def _build_client() -> Groq:
    key = config.get_key("groq")
    return Groq(api_key=key)


def ask_pyros(user_message: str, chat_history: list) -> str:
    """
    user_message: latest thing the user typed
    chat_history: list of {"role": "user"/"assistant", "content": "..."} dicts
    Returns Pyros's reply as a string.
    """
    messages = [{"role": "system", "content": get_system_prompt()}]
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
    history = []
    print("Pyros brain test. Type 'quit' to stop.\n")
    while True:
        user_input = input("You: ")
        if user_input.lower() == "quit":
            break
        reply = ask_pyros(user_input, history)
        print(f"Pyros: {reply}\n")
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": reply})