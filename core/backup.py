"""
core/backup.py

Full backup/restore for PYROS's memory — people, feedback, and chat history
(SQLite side). Vector embeddings regenerate automatically from source docs,
so we don't need to back those up separately; if you restore an old backup,
just re-run add_document() on your PDFs to rebuild the vector index.

Usage:
    from core.backup import create_backup, restore_backup
    create_backup()                        # writes pyros_data/backup_<timestamp>.json
    restore_backup("pyros_data/backup_2026-07-22.json")
"""
import json
import datetime
import os
import memory.history_store as history

BACKUP_DIR = "pyros_data/backups"


def create_backup() -> str:
    """Dumps all structured memory (people, feedback, chat) to a timestamped JSON file."""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(BACKUP_DIR, f"backup_{timestamp}.json")

    data = {
        "created_at": timestamp,
        "people": history.get_all_people(),
        "conversations": history.get_recent_messages(limit=100000),
        "feedback_stats": history.feedback_stats(),
    }

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, default=str)

    return filepath


def restore_backup(filepath: str, wipe_existing: bool = False):
    """
    Restores people and conversation history from a backup file.
    Set wipe_existing=True to clear current data first (otherwise it merges).
    """
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if wipe_existing:
        history.clear_conversations()

    for person in data.get("people", []):
        history.add_person(
            name=person["name"],
            notes=person.get("notes", ""),
        )

    for msg in data.get("conversations", []):
        history.add_message(role=msg["role"], content=msg["content"])

    return {
        "people_restored": len(data.get("people", [])),
        "messages_restored": len(data.get("conversations", [])),
    }


def list_backups() -> list:
    """Returns available backup files, newest first — useful for a 'restore from...' menu in the UI."""
    if not os.path.exists(BACKUP_DIR):
        return []
    files = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")]
    files.sort(reverse=True)
    return files