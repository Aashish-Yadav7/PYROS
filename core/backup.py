"""
core/backup.py

Full backup/restore for PYROS's structured memory.
"""
import json
import datetime
import os
import memory.history_store as history

BACKUP_DIR = "pyros_data/backups"


def create_backup() -> str:
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
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    if wipe_existing:
        history.clear_conversations()

    for person in data.get("people", []):
        history.add_person(name=person["name"], notes=person.get("notes", ""))

    for msg in data.get("conversations", []):
        history.add_message(role=msg["role"], content=msg["content"])

    return {
        "people_restored": len(data.get("people", [])),
        "messages_restored": len(data.get("conversations", [])),
    }


def list_backups() -> list:
    if not os.path.exists(BACKUP_DIR):
        return []
    files = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".json")]
    files.sort(reverse=True)
    return files