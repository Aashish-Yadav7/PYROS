"""
core/settings.py

Loads all API keys and configuration from .env.
Every other file imports from here — never reads .env directly.
"""
from dotenv import load_dotenv
import os

load_dotenv()

GROQ_API_KEY1 = os.getenv("GROQ_API_KEY1")
GROQ_API_KEY2 = os.getenv("GROQ_API_KEY2")

MISTRAL_API_KEY1 = os.getenv("MISTRAL_API_KEY1")
MISTRAL_API_KEY2 = os.getenv("MISTRAL_API_KEY2")

CEREBRAS_API_KEY1 = os.getenv("CEREBRAS_API_KEY1")
CEREBRAS_API_KEY2 = os.getenv("CEREBRAS_API_KEY2")

OPENROUTER_API_KEY1 = os.getenv("OPENROUTER_API_KEY1")
OPENROUTER_API_KEY2 = os.getenv("OPENROUTER_API_KEY2")

COHERE_API_KEY1 = os.getenv("COHERE_API_KEY1")
COHERE_API_KEY2 = os.getenv("COHERE_API_KEY2")

# HPC — placeholder until we confirm what this provider actually is and its
# base URL / SDK. Loaded here so nothing breaks, but NOT yet wired into
# model_router.py. Tell Claude the provider name and we'll finish this. 


HPC_API_KEY1 = os.getenv("HPC_API_KEY1")
HPC_API_KEY2 = os.getenv("HPC_API_KEY2")

# --- Tunable behavior settings ---
MAX_REQUESTS_PER_MINUTE = 5
CONVERSATION_HISTORY_LIMIT = 20
RAG_TOP_K = 5
APP_NAME = "PYROS"


def check_keys_loaded(verbose: bool = True) -> bool:
    required = {
        "GROQ_API_KEY1": GROQ_API_KEY1,
        "GROQ_API_KEY2": GROQ_API_KEY2,
        "MISTRAL_API_KEY1": MISTRAL_API_KEY1,
        "MISTRAL_API_KEY2": MISTRAL_API_KEY2,
        "CEREBRAS_API_KEY1": CEREBRAS_API_KEY1,
        "CEREBRAS_API_KEY2": CEREBRAS_API_KEY2,
        "OPENROUTER_API_KEY1": OPENROUTER_API_KEY1,
        "OPENROUTER_API_KEY2": OPENROUTER_API_KEY2,
        "COHERE_API_KEY1": COHERE_API_KEY1,
        "COHERE_API_KEY2": COHERE_API_KEY2,
    }
    missing = [name for name, value in required.items() if not value]

    if missing and verbose:
        print(f"[PYROS] WARNING: missing keys in .env: {', '.join(missing)}")
    elif verbose:
        print("[PYROS] All core API keys loaded successfully.")

    return len(missing) == 0