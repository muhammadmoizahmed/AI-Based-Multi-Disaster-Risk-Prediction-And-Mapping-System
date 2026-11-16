"""LSTM flood risk inference service.

Loads the verified Flood LSTM artifacts, builds genuine per-city chronological
sequences from the flood dataset, and serves predictions. Predictions describe
the flood outcome of the next observed record for the selected city, not the
next calendar day.
"""

from __future__ import annotations

import json
import logging
import threading
from datetime import date
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "ml" / "artifacts" / "flood_lstm"
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = REPO_ROOT / "datasets" / "pakistan_flood_dataset_2020_2025 (1).csv"

FEATURE_COLUMNS = [
    "rainfall_mm",
    "river_level_m",
    "latitude",
    "longitude",
    "days_since_previous",
    "month_sin",
    "month_cos",
]
MIN_HISTORY = 14

_bundle_lock = threading.Lock()
_data_lock = threading.Lock()
_bundle: Optional[dict] = None
_history_cache: Optional[pd.DataFrame] = None

logger = logging.getLogger("disasterguard.flood_lstm")


def _validate_artifacts() -> None:
    required = [
        "flood_lstm.keras",
        "scaler.joblib",
        "feature_schema.json",
        "model_metadata.json",
        "evaluation_metrics.json",
    ]
    missing = [name for name in required if not (ARTIFACT_DIR / name).exists()]
    if missing:
        raise FileNotFoundError(
            f"Flood LSTM artifacts missing: {', '.join(missing)} in {ARTIFACT_DIR}"
        )


def _load_bundle() -> dict:
    global _bundle
    if _bundle is None:
        with _bundle_lock:
            if _bundle is None:
                _validate_artifacts()
                import tensorflow as tf

                logger.info("Loading Flood LSTM artifacts from %s", ARTIFACT_DIR)
                model = tf.keras.models.load_model(ARTIFACT_DIR / "flood_lstm.keras")
                scaler = joblib.load(ARTIFACT_DIR / "scaler.joblib")
                features = json.loads((ARTIFACT_DIR / "feature_schema.json").read_text())
                metadata = json.loads((ARTIFACT_DIR / "model_metadata.json").read_text())

                if list(features) != FEATURE_COLUMNS:
                    raise ValueError(
                        "feature_schema.json does not match the expected Flood LSTM features. "
                        f"Expected {FEATURE_COLUMNS}, got {features}"
                    )
                if metadata.get("features") and list(metadata["features"]) != FEATURE_COLUMNS:
                    raise ValueError("model_metadata.json feature order does not match schema.")
                if int(metadata.get("lookback", 0)) != MIN_HISTORY:
                    raise ValueError(
                        f"Unsupported lookback {metadata.get('lookback')}; expected {MIN_HISTORY}."
                    )
                if not hasattr(scaler, "transform"):
                    raise ValueError("Loaded scaler does not expose transform().")

                _bundle = {
                    "model": model,
                    "scaler": scaler,
                    "features": features,
                    "metadata": metadata,
                }
                logger.info(
                    "Flood LSTM loaded: version=%s lookback=%s threshold=%s",
                    metadata["model_version"],
                    metadata["lookback"],
                    metadata.get("threshold", 0.5),
                )
    return _bundle


def preload_model() -> dict:
    """Load artifacts during application startup. Raises on failure."""
    return _load_bundle()


def _risk_level(probability: float) -> str:
    if probability >= 0.75:
        return "extreme"
    if probability >= 0.50:
        return "high"
    if probability >= 0.25:
        return "moderate"
    return "low"


def _classify_probability(probability: float, threshold: float) -> dict:
    probability = float(probability)
    if not np.isfinite(probability) or probability < 0.0 or probability > 1.0:
        raise ValueError("Model returned an invalid probability.")
    return {
        "flood_probability": round(probability, 4),
        "flood_predicted": bool(probability >= threshold),
        "risk_score": int(round(probability * 100)),
        "risk_level": _risk_level(probability),
        "threshold_used": threshold,
    }


def _load_history() -> pd.DataFrame:
    global _history_cache
    if _history_cache is None:
        with _data_lock:
            if _history_cache is None:
                if not DATA_PATH.exists():
                    raise FileNotFoundError(f"Flood dataset not found at {DATA_PATH}")
                df = pd.read_csv(DATA_PATH)
                required = {"date", "city", "latitude", "longitude", "rainfall_mm", "river_level_m", "flood_occurred"}
                missing = required - set(df.columns)
                if missing:
                    raise ValueError(f"Flood dataset is missing columns: {sorted(missing)}")
                df["date"] = pd.to_datetime(df["date"], errors="coerce")
                df = df.dropna(subset=["date", "city", "latitude", "longitude", "rainfall_mm", "river_level_m"])
                # Same aggregation as training: mean weather/coords, max flood label.
                agg = df.groupby(["city", "date"], as_index=False).agg(
                    {
                        "latitude": "first",
                        "longitude": "first",
                        "rainfall_mm": "mean",
                        "river_level_m": "mean",
                        "flood_occurred": "max",
                    }
                )
                agg = agg.sort_values(["city", "date"]).reset_index(drop=True)
                agg["days_since_previous"] = (
                    agg.groupby("city")["date"].diff().dt.days.fillna(0).astype(float)
                )
                month = agg["date"].dt.month
                agg["month_sin"] = np.sin(2 * np.pi * month / 12.0)
                agg["month_cos"] = np.cos(2 * np.pi * month / 12.0)
                _history_cache = agg
                logger.info("Flood history loaded: %s records across %s cities", len(agg), agg["city"].nunique())
    return _history_cache


def _normalize_city(city: str) -> str:
    text = str(city or "").strip()
    if not text:
        raise ValueError("City is required.")
    base = text.split(",")[0].strip().lower()
    df = _load_history()
    lookup = {str(name).strip().lower(): str(name) for name in df["city"].unique()}
    if base in lookup:
        return lookup[base]
    raise ValueError(
        f"No historical flood data for '{city}'. Supported cities: {', '.join(sorted(lookup.values()))}"
    )


def _prepare_city_history(city: str):
    bundle = _load_bundle()
    canonical = _normalize_city(city)
    df = _load_history()
    city_df = df[df["city"] == canonical].sort_values("date").reset_index(drop=True)
    if len(city_df) < MIN_HISTORY:
        raise ValueError(
            f"Insufficient history for {canonical}: need {MIN_HISTORY} observations, "
            f"found {len(city_df)}."
        )
    features = bundle["features"]
    window = city_df[features].tail(MIN_HISTORY)
    if not np.isfinite(window.to_numpy(dtype=float)).all():
        raise ValueError(f"Non-numeric or missing values in the latest history for {canonical}.")
    last = city_df.iloc[-1]
    return window.to_numpy(dtype=float), last, canonical


def _predict_array(sequence: np.ndarray) -> dict:
    bundle = _load_bundle()
    features = bundle["features"]
    if sequence.ndim != 2 or sequence.shape[1] != len(features):
        raise ValueError(f"Expected shape (timesteps, {len(features)}), got {sequence.shape}")
    lookback = int(bundle["metadata"]["lookback"])
    if sequence.shape[0] != lookback:
        raise ValueError(f"Expected {lookback} timesteps, got {sequence.shape[0]}")
    if not np.isfinite(sequence).all():
        raise ValueError("Sequence contains non-numeric or missing values.")
    flat = bundle["scaler"].transform(sequence)
    x = flat.reshape(1, lookback, len(features))
    probability = float(bundle["model"].predict(x, verbose=0).ravel()[0])
    threshold = float(bundle["metadata"].get("threshold", 0.5))
    return {
        "success": True,
        "model": {
            "name": bundle["metadata"]["model_name"],
            "version": bundle["metadata"]["model_version"],
            "lookback": lookback,
            "prediction_horizon": bundle["metadata"].get("prediction_horizon"),
        },
        "prediction": _classify_probability(probability, threshold),
    }


def predict_sequence(sequence):
    try:
        arr = np.asarray(sequence, dtype=float)
    except (TypeError, ValueError) as exc:
        raise ValueError("Sequence must contain numeric values.") from exc
    return _predict_array(arr)


def _observation_payload(last: pd.Series) -> dict:
    return {
        "date": str(pd.Timestamp(last["date"]).date()),
        "latitude": float(last["latitude"]),
        "longitude": float(last["longitude"]),
        "rainfall_mm": round(float(last["rainfall_mm"]), 2),
        "river_level_m": round(float(last["river_level_m"]), 2),
        "flood_occurred": bool(int(last["flood_occurred"])),
    }


def predict_by_city(city: str):
    seq, last, canonical = _prepare_city_history(city)
    result = _predict_array(seq)
    result["city"] = canonical
    result["location"] = {"city": canonical, "latitude": float(last["latitude"]), "longitude": float(last["longitude"])}
    result["observation"] = _observation_payload(last)
    result["last_observation_date"] = result["observation"]["date"]
    result["prediction_horizon"] = "next observed record for this city"
    result["prediction_timestamp"] = pd.Timestamp.utcnow().isoformat()
    result["data_source"] = "historical_dataset"
    _store_prediction(result)
    return result


def _estimate_live_river_level(last_river: float, last_rain: float, live_rain: float) -> float:
    """Estimate the current river level from the last gauge reading and live rainfall.

    There is no public live river-gauge API wired in, so the level is a bounded
    heuristic: the previous level plus a rainfall-driven rise, damped so a single
    heavy-rain day cannot exceed the physical range seen in training.
    """
    baseline = max(float(last_river), 0.3)
    historical = max(float(last_rain), 0.0)
    extra = max(float(live_rain) - historical, 0.0)
    rise = min(extra * 0.02, 3.0)  # ~1m rise per 50mm above the last reading, capped
    return float(np.clip(baseline + rise, 0.3, 9.94))


def _live_weather_for(latitude: float, longitude: float) -> dict:
    try:
        from services.weather_service import get_live_rainfall
    except ImportError:  # pragma: no cover - package-style import
        try:
            from backend.services.weather_service import get_live_rainfall
        except ImportError:
            return {"available": False, "reason": "weather service unavailable"}
    try:
        return get_live_rainfall(latitude, longitude)
    except Exception as exc:  # pragma: no cover - network must never break inference
        logger.warning("Live weather lookup failed for %s,%s: %s", latitude, longitude, exc)
        return {"available": False, "reason": str(exc)}


def predict_by_city_live(city: str):
    """Predict flood risk for a city using the latest live OpenWeather conditions.

    The final timestep of the 14-step sequence is replaced with today's live
    rainfall (and a bounded river-level estimate); the previous 13 historical
    observations preserve the city's temporal context.
    """
    seq, last, canonical = _prepare_city_history(city)
    latitude = float(last["latitude"])
    longitude = float(last["longitude"])
    live = _live_weather_for(latitude, longitude)

    if not live.get("available"):
        # Graceful fallback: serve the deterministic historical prediction.
        result = predict_by_city(city)
        result["data_source"] = "historical_dataset_fallback"
        result["live_weather"] = live
        return result

    live_rain = float(live.get("rainfall_mm") or 0.0)
    live_river = _estimate_live_river_level(float(last["river_level_m"]), float(last["rainfall_mm"]), live_rain)

    today = pd.Timestamp.utcnow().normalize()
    month = today.month
    live_row = np.array(
        [
            live_rain,
            live_river,
            latitude,
            longitude,
            1.0,
            np.sin(2 * np.pi * month / 12.0),
            np.cos(2 * np.pi * month / 12.0),
        ],
        dtype=float,
    )

    live_sequence = np.vstack([seq[1:], live_row])
    result = _predict_array(live_sequence)
    result["city"] = canonical
    result["location"] = {"city": canonical, "latitude": latitude, "longitude": longitude}
    result["observation"] = {
        "date": str(today.date()),
        "latitude": latitude,
        "longitude": longitude,
        "rainfall_mm": round(live_rain, 2),
        "river_level_m": round(live_river, 2),
        "flood_occurred": None,
    }
    result["live_weather"] = live
    result["last_observation_date"] = str(today.date())
    result["prediction_horizon"] = "next 24 hours from live conditions"
    result["prediction_timestamp"] = pd.Timestamp.utcnow().isoformat()
    result["data_source"] = "live_weather"
    _store_prediction(result)
    return result


def predict_by_city_auto(city: str, live: bool = False):
    """Dispatch to live or historical prediction, falling back safely."""
    if live:
        return predict_by_city_live(city)
    return predict_by_city(city)


def _store_prediction(result: dict) -> None:
    try:
        from database.db_flood_lstm import save_flood_lstm_prediction
    except ImportError:
        try:
            from backend.database.db_flood_lstm import save_flood_lstm_prediction
        except ImportError:
            return
    try:
        save_flood_lstm_prediction(result)
    except Exception as exc:  # pragma: no cover - persistence must never break inference
        logger.warning("Flood LSTM prediction persistence failed: %s", exc)


def model_info():
    bundle = _load_bundle()
    meta = bundle["metadata"]
    metrics = meta.get("metrics", {})
    return {
        "success": True,
        "model": {
            "name": meta["model_name"],
            "type": "LSTM",
            "version": meta["model_version"],
            "framework": meta["framework"],
            "framework_version": meta.get("framework_version"),
            "lookback": meta["lookback"],
            "feature_count": len(bundle["features"]),
            "features": bundle["features"],
            "threshold": meta.get("threshold", 0.5),
            "prediction_horizon": meta.get("prediction_horizon"),
            "trained_at": meta.get("trained_at"),
        },
        "metrics": metrics,
        "training": meta.get("split", {}),
        "artifact_status": {
            "model": (ARTIFACT_DIR / "flood_lstm.keras").exists(),
            "scaler": (ARTIFACT_DIR / "scaler.joblib").exists(),
            "evaluation_metrics": (ARTIFACT_DIR / "evaluation_metrics.json").exists(),
        },
    }


def list_cities():
    df = _load_history()
    rows = []
    for city, group in df.groupby("city"):
        group = group.sort_values("date")
        rows.append(
            {
                "city": str(city),
                "province": None,
                "records": int(len(group)),
                "min_date": str(group["date"].min().date()),
                "max_date": str(group["date"].max().date()),
                "latitude": float(group["latitude"].iloc[-1]),
                "longitude": float(group["longitude"].iloc[-1]),
                "history_available": bool(len(group) >= MIN_HISTORY),
                "required_records": MIN_HISTORY,
            }
        )
    return {
        "success": True,
        "lookback": MIN_HISTORY,
        "cities": sorted(rows, key=lambda row: row["city"]),
    }


def get_city_history(city: str, limit: int = 10):
    canonical = _normalize_city(city)
    df = _load_history()
    city_df = df[df["city"] == canonical].sort_values("date", ascending=False).head(max(1, min(limit, 100)))
    records = []
    for _, row in city_df.iterrows():
        records.append(
            {
                "date": str(pd.Timestamp(row["date"]).date()),
                "city": canonical,
                "rainfall_mm": round(float(row["rainfall_mm"]), 2),
                "river_level_m": round(float(row["river_level_m"]), 2),
                "flood_occurred": bool(int(row["flood_occurred"])),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
            }
        )
    return {"success": True, "city": canonical, "records": records, "count": len(records)}


def overview(limit: int = 50):
    df = _load_history()
    results = []
    for city in sorted(df["city"].unique()):
        try:
            prediction = predict_by_city(city)
        except ValueError:
            continue
        results.append(
            {
                "city": prediction["city"],
                "latitude": prediction["location"]["latitude"],
                "longitude": prediction["location"]["longitude"],
                "probability": prediction["prediction"]["flood_probability"],
                "risk_level": prediction["prediction"]["risk_level"],
                "predicted": prediction["prediction"]["flood_predicted"],
                "rainfall_mm": prediction["observation"]["rainfall_mm"],
                "river_level_m": prediction["observation"]["river_level_m"],
                "last_observation_date": prediction["last_observation_date"],
            }
        )
    results = sorted(results, key=lambda row: row["probability"], reverse=True)[: max(1, min(limit, 200))]
    return {"success": True, "model": "flood_lstm", "cities": results, "count": len(results)}
