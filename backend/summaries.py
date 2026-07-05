import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

SUMMARIES_FILE = os.path.join(os.path.dirname(__file__), "summaries.json")


def _load_raw() -> list[dict]:
    try:
        with open(SUMMARIES_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _save_raw(entries: list[dict]) -> None:
    with open(SUMMARIES_FILE, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def register_summary(filename: str, path: str, title: str) -> dict:
    """Record a saved summary .txt file for the Summaries panel."""
    entry = {
        "filename": filename,
        "path": path,
        "title": title.strip() or "Summary",
        "created_at": datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
    }
    entries = _load_raw()
    entries.append(entry)
    _save_raw(entries)
    return entry


def list_summaries() -> list[dict]:
    entries = _load_raw()
    entries.sort(key=lambda item: item.get("created_at", ""), reverse=True)
    return entries


def delete_summary(index: int) -> list[dict]:
    sorted_entries = list_summaries()
    if not 0 <= index < len(sorted_entries):
        return sorted_entries

    remove_path = sorted_entries[index].get("path")
    entries = [entry for entry in _load_raw() if entry.get("path") != remove_path]
    _save_raw(entries)
    return list_summaries()


def clear_summaries() -> None:
    if os.path.exists(SUMMARIES_FILE):
        os.remove(SUMMARIES_FILE)
