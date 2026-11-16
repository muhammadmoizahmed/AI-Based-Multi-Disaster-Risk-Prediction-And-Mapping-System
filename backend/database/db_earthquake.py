"""Database helpers for Earthquake prediction history."""

from __future__ import annotations

import os
from datetime import date
from typing import Optional

from database.db_config import get_db_connection, USE_SQLITE


def _ensure_table(cursor):
    if USE_SQLITE:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                location TEXT,
                risk_level TEXT,
                probability INTEGER,
                prediction_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    else:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS predictions (
                id SERIAL PRIMARY KEY,
                location VARCHAR(255),
                risk_level VARCHAR(50),
                probability INTEGER,
                prediction_date DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def save_earthquake_prediction(location: str, risk_level: str, probability: int, prediction_date: Optional[str] = None) -> bool:
    if os.getenv("EARTHQUAKE_STORE_PREDICTIONS", "true").lower() not in {"1", "true", "yes"}:
        return False
    try:
        with get_db_connection() as conn:
            if not conn:
                return False
            cursor = conn.cursor()
            _ensure_table(cursor)
            if prediction_date is None:
                prediction_date = date.today().isoformat()
            if USE_SQLITE:
                cursor.execute(
                    "INSERT INTO predictions (location, risk_level, probability, prediction_date) VALUES (?, ?, ?, ?)",
                    (location, risk_level, int(probability), prediction_date),
                )
            else:
                cursor.execute(
                    "INSERT INTO predictions (location, risk_level, probability, prediction_date) VALUES (%s, %s, %s, %s)",
                    (location, risk_level, int(probability), prediction_date),
                )
            conn.commit()
            return True
    except Exception:
        return False
