import json
import sqlite3
from pathlib import Path


DB_PATH = Path(__file__).resolve().parent.parent / "docshield.db"


def get_connection() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with get_connection() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS scans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                extracted_text TEXT NOT NULL,
                redacted_text TEXT NOT NULL,
                entities TEXT NOT NULL,
                extracted_attributes TEXT DEFAULT '[]',
                selected_fields TEXT DEFAULT '[]',
                photo_detected INTEGER DEFAULT 0,
                risk_score INTEGER NOT NULL,
                risk_level TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        existing = {
            row["name"] for row in connection.execute("PRAGMA table_info(scans)").fetchall()
        }
        migrations = {
            "extracted_attributes": "ALTER TABLE scans ADD COLUMN extracted_attributes TEXT DEFAULT '[]'",
            "selected_fields": "ALTER TABLE scans ADD COLUMN selected_fields TEXT DEFAULT '[]'",
            "photo_detected": "ALTER TABLE scans ADD COLUMN photo_detected INTEGER DEFAULT 0",
        }
        for column, statement in migrations.items():
            if column not in existing:
                connection.execute(statement)


def save_scan(
    filename: str,
    extracted_text: str,
    attributes: list[dict],
    selected_fields: list[str],
    result: dict,
    photo_detected: bool,
) -> int:
    with get_connection() as connection:
        cursor = connection.execute(
            """
            INSERT INTO scans (
                filename, extracted_text, redacted_text, entities, extracted_attributes,
                selected_fields, photo_detected, risk_score, risk_level
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                filename,
                extracted_text,
                result["redacted_text"],
                json.dumps(result.get("attribute_rows", [])),
                json.dumps(attributes),
                json.dumps(selected_fields),
                int(photo_detected),
                result["risk_score"],
                result["risk_level"],
            ),
        )
        return int(cursor.lastrowid)


def get_history() -> list[dict]:
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, filename, extracted_attributes, selected_fields, risk_score,
                   risk_level, photo_detected, created_at
            FROM scans
            ORDER BY created_at DESC, id DESC
            LIMIT 25
            """
        ).fetchall()

    return [
        {
            "id": row["id"],
            "filename": row["filename"],
            "attributes": json.loads(row["extracted_attributes"] or "[]"),
            "selected_fields": json.loads(row["selected_fields"] or "[]"),
            "risk_score": row["risk_score"],
            "risk_level": row["risk_level"],
            "photo_detected": bool(row["photo_detected"]),
            "created_at": row["created_at"],
        }
        for row in rows
    ]
