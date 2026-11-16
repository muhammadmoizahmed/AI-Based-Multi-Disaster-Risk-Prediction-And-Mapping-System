"""Database helpers for Flood LSTM prediction history."""

from __future__ import annotations

import json
import os
from datetime import date
from typing import Optional

from database.db_config import get_db_connection, USE_SQLITE


def _ensure_table(cursor):
    if USE_SQLITE:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS flood_lstm_predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                city TEXT NOT NULL,
                latitude REAL,
                longitude REAL,
                model_version TEXT,
                probability REAL,
                predicted INTEGER,
                risk_level TEXT,
                threshold REAL,
                observation_date DATE,
                prediction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                input_metadata TEXT
            )
            """
        )
    else:
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS flood_lstm_predictions (
                id SERIAL PRIMARY KEY,
                city VARCHAR(255) NOT NULL,
                latitude DOUBLE PRECISION,
                longitude DOUBLE PRECISION,
                model_version VARCHAR(50),
                probability DOUBLE PRECISION,
                predicted INTEGER,
                risk_level VARCHAR(50),
                threshold DOUBLE PRECISION,
                observation_date DATE,
                prediction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                input_metadata TEXT
            )
            """
        )


def save_flood_lstm_prediction(result: dict, observation_date: Optional[str] = None) -> bool:
    if os.getenv("FLOOD_LSTM_STORE_PREDICTIONS", "true").lower() not in {"1", "true", "yes"}:
        return False
    try:
        prediction = result.get("prediction", {})
        location = result.get("location", {})
        observation = result.get("observation", {})
        city = result.get("city") or location.get("city")
        if not city:
            return False
        metadata = json.dumps(
            {
                "rainfall_mm": observation.get("rainfall_mm"),
                "river_level_m": observation.get("river_level_m"),
                "lookback": result.get("model", {}).get("lookback"),
                "prediction_horizon": result.get("prediction_horizon"),
            }
        )
        values = (
            city,
            location.get("latitude"),
            location.get("longitude"),
            result.get("model", {}).get("version"),
            prediction.get("flood_probability"),
            int(bool(prediction.get("flood_predicted"))),
            prediction.get("risk_level"),
            prediction.get("threshold_used"),
            observation_date or observation.get("date") or date.today().isoformat(),
            metadata,
        )
        with get_db_connection() as conn:
            if not conn:
                return False
            cursor = conn.cursor()
            _ensure_table(cursor)
            if USE_SQLITE:
                cursor.execute(
                    """
                    INSERT INTO flood_lstm_predictions
                    (city, latitude, longitude, model_version, probability, predicted,
                     risk_level, threshold, observation_date, input_metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    values,
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO flood_lstm_predictions
                    (city, latitude, longitude, model_version, probability, predicted,
                     risk_level, threshold, observation_date, input_metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    values,
                )
            conn.commit()
        return True
    except Exception:
        return False
