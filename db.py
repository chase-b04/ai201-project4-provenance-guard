"""
SQLite persistence layer for submissions and appeals.
"""

import sqlite3
import json

DB_PATH = "provenance.db"


def _conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)


def init_db():
    with _conn() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS submissions (
                submission_id TEXT PRIMARY KEY,
                timestamp TEXT,
                title TEXT,
                author TEXT,
                signal_a REAL,
                signal_b REAL,
                aggregated_score REAL,
                disagreement REAL,
                confidence REAL,
                label_tier TEXT,
                label_text TEXT,
                status TEXT
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS appeals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id TEXT,
                reasoning TEXT,
                timestamp TEXT,
                status TEXT
            )
        """)


def create_submission(entry: dict):
    with _conn() as con:
        con.execute("""
            INSERT INTO submissions VALUES (
                :submission_id, :timestamp, :title, :author,
                :signal_a, :signal_b, :aggregated_score, :disagreement,
                :confidence, :label_tier, :label_text, :status
            )
        """, entry)


def get_submission(submission_id: str) -> dict | None:
    with _conn() as con:
        row = con.execute(
            "SELECT * FROM submissions WHERE submission_id = ?", (submission_id,)
        ).fetchone()
    if not row:
        return None
    cols = [
        "submission_id", "timestamp", "title", "author",
        "signal_a", "signal_b", "aggregated_score", "disagreement",
        "confidence", "label_tier", "label_text", "status",
    ]
    return dict(zip(cols, row))


def create_appeal(record: dict):
    with _conn() as con:
        con.execute("""
            INSERT INTO appeals (submission_id, reasoning, timestamp, status)
            VALUES (:submission_id, :reasoning, :timestamp, :status)
        """, record)
        con.execute(
            "UPDATE submissions SET status = 'under_review' WHERE submission_id = ?",
            (record["submission_id"],)
        )
