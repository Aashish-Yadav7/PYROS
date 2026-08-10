"""
config.py
Loads all API keys and settings from .env
Handles key rotation: if key_1 fails (rate limit/error), switch to key_2.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Each provider has a list of keys. Index 0 is tried first.
API_KEYS = {
    "groq": [os.getenv("GROQ_API_KEY_1"), os.getenv("GROQ_API_KEY_2")],
    "mistral": [os.getenv("MISTRAL_API_KEY_1"), os.getenv("MISTRAL_API_KEY_2")],
    "cerebras": [os.getenv("CEREBRAS_API_KEY_1"), os.getenv("CEREBRAS_API_KEY_2")],
    "openai": [os.getenv("OPENAI_API_KEY_1"), os.getenv("OPENAI_API_KEY_2")],
}

# Single key, no rotation needed for this one
CURRENTS_API_KEY = os.getenv("CURRENTS_API_KEY")

# Voice output engine: "edge_tts" (default, works on any machine, no GPU
# needed) or "chatterbox" (much higher quality, needs a real GPU - only
# switch to this once you have one).
TTS_ENGINE = os.getenv("TTS_ENGINE", "edge_tts")

# Tracks which key index is currently active per provider
_active_key_index = {provider: 0 for provider in API_KEYS}


def get_key(provider: str) -> str:
    """Return the currently active key for a provider."""
    idx = _active_key_index[provider]
    return API_KEYS[provider][idx]


def rotate_key(provider: str) -> str:
    """
    Switch to the next key for a provider (e.g. after a rate-limit error).
    Returns the new active key.
    """
    keys = API_KEYS[provider]
    current = _active_key_index[provider]
    next_idx = (current + 1) % len(keys)
    _active_key_index[provider] = next_idx
    print(f"[config] Rotated {provider} key -> using key index {next_idx}")
    return keys[next_idx]