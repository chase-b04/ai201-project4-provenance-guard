"""
Audit Logger: writes structured entries to audit_log.json.

Submission entries are immutable once written. Appeal entries are appended
alongside them and reference the original content_id.
"""

import json
import os
from threading import Lock

LOG_PATH = "audit_log.json"
_lock = Lock()


def _load() -> list:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []


def _save(entries: list):
    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)


def log_entry(entry: dict):
    with _lock:
        entries = _load()
        entries.append({"type": "submission", **entry})
        _save(entries)


def log_appeal(record: dict):
    """Append an appeal entry and mark the original submission as under_review."""
    with _lock:
        entries = _load()
        # Mark the original submission entry as under_review
        for e in entries:
            if e.get("type") == "submission" and e.get("content_id") == record["content_id"]:
                e["status"] = "under_review"
                break
        entries.append({"type": "appeal", **record})
        _save(entries)


def get_entry_by_content_id(content_id: str) -> dict | None:
    with _lock:
        for e in _load():
            if e.get("type") == "submission" and e.get("content_id") == content_id:
                return e
    return None


def get_log() -> list:
    with _lock:
        return _load()
