"""
memory.py
Gives Pyros persistent memory across sessions.

Two plain-text log files, both using numbered exchange blocks:
    1.
    User= hey
    PYROS= hey there

    2.
    User= ...
    PYROS= ...

- full_log.txt        -> every exchange, forever, never deleted.
- chat_history.txt     -> only the last 35 exchanges (rolling window),
                          used to give the LLM recent context without
                          reading the entire history every time.

Long-term facts (ChromaDB) are separate: important things only, saved
just when explicitly asked to "remember" something.

Also handles a simple saved preference: what the user wants to be called
(e.g. "Boss", "Sir", or their name).
"""

import os
import re
from datetime import datetime
import chromadb

# --- Where everything is stored ---
MEMORY_DIR = "memory_store"
FULL_LOG_FILE = os.path.join(MEMORY_DIR, "full_log.txt")
RECENT_LOG_FILE = os.path.join(MEMORY_DIR, "chat_history.txt")
PREFERENCE_FILE = os.path.join(MEMORY_DIR, "preferred_address.txt")

RECENT_EXCHANGE_LIMIT = 35  # how many numbered exchanges chat_history.txt keeps

os.makedirs(MEMORY_DIR, exist_ok=True)

# --- ChromaDB setup (long-term memory) ---
_chroma_client = chromadb.PersistentClient(path=os.path.join(MEMORY_DIR, "chroma_db"))
_memory_collection = _chroma_client.get_or_create_collection(name="pyros_memories")


# ---------- EXCHANGE LOGGING (numbered, plain text) ----------

def _get_next_exchange_number() -> int:
    """Look at the full log to figure out the next exchange number."""
    if not os.path.exists(FULL_LOG_FILE):
        return 1
    with open(FULL_LOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()
    numbers = re.findall(r"^(\d+)\.\s*$", content, flags=re.MULTILINE)
    return int(numbers[-1]) + 1 if numbers else 1


def log_exchange(user_message: str, assistant_reply: str) -> None:
    """
    Write one numbered exchange block to BOTH log files.
    full_log.txt keeps every exchange forever.
    chat_history.txt keeps only the most recent RECENT_EXCHANGE_LIMIT.
    """
    number = _get_next_exchange_number()
    block = f"{number}.\nUser= {user_message}\nPYROS= {assistant_reply}\n\n"

    with open(FULL_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(block)

    _append_and_trim_recent(block)


def _append_and_trim_recent(block: str) -> None:
    """Add a new block to chat_history.txt, keeping only the last N exchanges."""
    existing = ""
    if os.path.exists(RECENT_LOG_FILE):
        with open(RECENT_LOG_FILE, "r", encoding="utf-8") as f:
            existing = f.read()

    combined = existing + block
    blocks = [b for b in combined.strip().split("\n\n") if b.strip()]
    blocks = blocks[-RECENT_EXCHANGE_LIMIT:]

    with open(RECENT_LOG_FILE, "w", encoding="utf-8") as f:
        f.write("\n\n".join(blocks) + "\n\n")


def load_history() -> list:
    """
    Read chat_history.txt and convert it into the {"role", "content"}
    format the LLM expects, for conversation continuity.
    """
    if not os.path.exists(RECENT_LOG_FILE):
        return []

    with open(RECENT_LOG_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    history = []
    for block in content.strip().split("\n\n"):
        for line in block.split("\n"):
            if line.startswith("User= "):
                history.append({"role": "user", "content": line[len("User= "):]})
            elif line.startswith("PYROS= "):
                history.append({"role": "assistant", "content": line[len("PYROS= "):]})
    return history


# ---------- PREFERRED ADDRESS (what to call the user) ----------

USER_NAME_FILE = os.path.join(MEMORY_DIR, "user_name.txt")


def get_user_name() -> str | None:
    """Returns the user's actual name, or None if never set."""
    if not os.path.exists(USER_NAME_FILE):
        return None
    with open(USER_NAME_FILE, "r", encoding="utf-8") as f:
        value = f.read().strip()
    return value if value else None


def set_user_name(name: str) -> None:
    """Save the user's actual name."""
    with open(USER_NAME_FILE, "w", encoding="utf-8") as f:
        f.write(name.strip())


def get_preferred_address() -> str | None:
    """Returns saved preference (e.g. 'Boss') or None if never set."""
    if not os.path.exists(PREFERENCE_FILE):
        return None
    with open(PREFERENCE_FILE, "r", encoding="utf-8") as f:
        value = f.read().strip()
    return value if value else None


def set_preferred_address(name: str) -> None:
    """Save what the user wants to be called."""
    with open(PREFERENCE_FILE, "w", encoding="utf-8") as f:
        f.write(name.strip())
    print(f"[memory] Will address user as: {name.strip()}")


# ---------- LONG-TERM MEMORY (semantic, important facts only) ----------

def remember_fact(fact: str) -> None:
    """Store an important fact permanently, searchable by meaning later."""
    fact_id = f"fact_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
    _memory_collection.add(documents=[fact], ids=[fact_id])
    print(f"[memory] Remembered: {fact}")


def recall_facts(query: str, n_results: int = 3) -> list:
    """Search long-term memory for facts relevant to the query."""
    count = _memory_collection.count()
    if count == 0:
        return []
    results = _memory_collection.query(
        query_texts=[query],
        n_results=min(n_results, count),
    )
    return results["documents"][0] if results["documents"] else []


# --- Quick manual test ---
if __name__ == "__main__":
    print("Testing memory.py...")
    log_exchange("hey", "hey there!")
    log_exchange("how are you", "doing great, thanks for asking!")

    print("--- full_log.txt ---")
    print(open(FULL_LOG_FILE).read())
    print("--- chat_history.txt ---")
    print(open(RECENT_LOG_FILE).read())
    print("--- reloaded history ---")
    print(load_history())