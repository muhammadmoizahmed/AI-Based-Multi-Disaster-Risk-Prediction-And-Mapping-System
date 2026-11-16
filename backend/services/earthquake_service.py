"""Earthquake damage-risk inference service backed by the trained RandomForest model."""

from __future__ import annotations

import copy
import json
import logging
import threading
import time
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Optional

import joblib
import numpy as np
import pandas as pd

try:
    from ml.earthquake_features import build_inference_frame, haversine_km, select_columns
except ImportError:
    from backend.ml.earthquake_features import build_inference_frame, haversine_km, select_columns

try:
    from database.db_earthquake import save_earthquake_prediction
except ImportError:
    from backend.database.db_earthquake import save_earthquake_prediction

ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "ml" / "artifacts"
MODEL_PATH = ARTIFACT_DIR / "earthquake_model.joblib"

_model_lock = threading.Lock()
_bundle: Optional[dict] = None
_live_city_cache: dict[str, tuple[float, dict]] = {}
_live_city_lock = threading.Lock()
LIVE_CITY_CACHE_TTL_SECONDS = 300
# A city's *current* risk only uses nearby, recent events. Distant or old
# events are surfaced as context but never drive the score.
LIVE_RADIUS_KM = 100
LIVE_WINDOW_DAYS = 30
LIVE_REGIONAL_RADIUS_KM = 500
logger = logging.getLogger("disasterguard.earthquake")


def _load_bundle() -> dict:
    global _bundle
    if _bundle is None:
        with _model_lock:
            if _bundle is None:
                if not MODEL_PATH.exists():
                    raise FileNotFoundError(
                        f"Earthquake model not found at {MODEL_PATH}. "
                        "Run `python backend/ml/train_earthquake.py` first."
                    )
                logger.info("Loading earthquake model from %s", MODEL_PATH)
                _bundle = joblib.load(MODEL_PATH)
                logger.info(
                    "Earthquake model loaded: version=%s threshold=%s",
                    _bundle["metadata"]["model_version"],
                    _bundle["threshold"],
                )
    return _bundle


def _parse_city(city: str) -> tuple[str, Optional[str]]:
    parts = [part.strip() for part in str(city).split(",") if part.strip()]
    if not parts:
        return "Unknown", None
    return parts[0], parts[1] if len(parts) > 1 else None


def _risk_level(probability: float, boundaries: dict | None = None) -> str:
    boundaries = boundaries or {"low": 0.25, "moderate": 0.5, "high": 0.75}
    if probability < boundaries["low"]:
        return "low"
    if probability < boundaries["moderate"]:
        return "moderate"
    if probability < boundaries["high"]:
        return "high"
    return "extreme"


def _bar_color(score: float) -> str:
    if score >= 0.75:
        return "#ff1744"
    if score >= 0.5:
        return "#ff6d00"
    if score >= 0.25:
        return "#ffd600"
    return "#00c853"


def _factor(key: str, label: str, value: str, score: float) -> dict:
    score = float(np.clip(score, 0.0, 1.0))
    return {
        "key": key,
        "label": label,
        "value": value,
        "score": round(score, 4),
        "color": _bar_color(score),
    }


def _build_factors(row: pd.Series) -> list[dict]:
    magnitude = float(row.get("magnitude", 0.0))
    depth = float(row.get("depth_km", 0.0))
    fault_distance = float(row.get("fault_distance_km", 9999.0))
    prior_count_90d = float(row.get("prior_count_90d", 0.0))
    prior_max_mag_90d = float(row.get("prior_max_mag_90d", 0.0))
    local_count = float(row.get("prior_count_100km_90d", 0.0))

    magnitude_score = (magnitude - 1.5) / 4.7
    depth_score = 1.0 - min(depth, 70.0) / 70.0
    fault_score = 1.0 - min(fault_distance, 300.0) / 300.0
    activity_score = 0.6 * min(prior_count_90d / 15.0, 1.0) + 0.4 * min(prior_max_mag_90d / 6.2, 1.0)
    local_score = min(local_count / 10.0, 1.0)

    return [
        _factor("magnitude", "Magnitude Activity", f"{magnitude:.1f} ML", magnitude_score),
        _factor("depth", "Shallow Depth", f"{depth:.1f} km", depth_score),
        _factor("fault", "Fault Belt Proximity", f"{fault_distance:.0f} km", fault_score),
        _factor("activity", "Regional Seismicity (90d)", f"{int(prior_count_90d)} events", activity_score),
        _factor("local", "Local Density (100 km / 90d)", f"{int(local_count)} events", local_score),
    ]


def _event_context(row: pd.Series) -> dict:
    keys = [
        "prior_count_7d",
        "prior_count_30d",
        "prior_count_90d",
        "prior_max_mag_30d",
        "prior_max_mag_90d",
        "prior_mean_depth_30d",
        "prior_count_100km_90d",
        "min_distance_past_km",
        "days_since_previous",
        "distance_to_previous_km",
        "fault_distance_km",
    ]
    context = {}
    for key in keys:
        if key in row.index:
            value = row[key]
            context[key] = None if pd.isna(value) else float(value)
    return context


def _clean_feature_name(name: str) -> str:
    cleaned = str(name).replace("numeric__", "").replace("categorical__", "")
    cleaned = cleaned.replace("remainder__", "")
    if cleaned.startswith("city_"):
        return "city = " + cleaned[len("city_"):].replace("_", " ")
    if cleaned.startswith("province_"):
        return "province = " + cleaned[len("province_"):].replace("_", " ")
    return cleaned.replace("_", " ")


def _top_features(limit: int = 12) -> list[dict]:
    path = ARTIFACT_DIR / "feature_importance.csv"
    if not path.exists():
        return []
    frame = pd.read_csv(path).head(max(1, int(limit)))
    return [
        {
            "feature": _clean_feature_name(row["feature"]),
            "raw_feature": str(row["feature"]),
            "importance": float(row["importance"]),
        }
        for _, row in frame.iterrows()
    ]


def model_info() -> dict:
    metrics_path = ARTIFACT_DIR / "earthquake_metrics.json"
    if metrics_path.exists():
        metadata = json.loads(metrics_path.read_text(encoding="utf-8"))
    else:
        metadata = _load_bundle()["metadata"]

    bundle = _load_bundle()
    evaluation = metadata["evaluation"]
    deployment = evaluation.get("holdout_deployment_threshold", {})
    repeated = metadata.get("repeated_cv", [])
    deployed_row = next(
        (row for row in repeated if row.get("model") == metadata["model_name"]),
        repeated[0] if repeated else {},
    )
    return {
        "success": True,
        "model": {
            "name": metadata["model_name"],
            "algorithm": metadata.get("model_family", "RandomForestClassifier"),
            "version": metadata["model_version"],
            "feature_set": metadata["feature_set"],
            "threshold": bundle["threshold"],
            "thresholds": bundle.get("thresholds", {}),
            "risk_level_boundaries": bundle.get("risk_level_boundaries", {}),
            "trained_at": metadata["trained_at"],
            "deployment_note": metadata.get(
                "deployment_note",
                "RandomForest is the deployed production model.",
            ),
        },
        "dataset": metadata["dataset"],
        "metrics": evaluation,
        "metrics_summary": {
            "holdout": {
                key: deployment.get(key)
                for key in (
                    "accuracy",
                    "precision",
                    "recall",
                    "f1",
                    "roc_auc",
                    "pr_auc",
                    "threshold",
                    "tn",
                    "fp",
                    "fn",
                    "tp",
                )
            },
            "repeated_cv": {
                key: deployed_row.get(key)
                for key in (
                    "accuracy",
                    "precision",
                    "recall",
                    "f1",
                    "roc_auc",
                    "pr_auc",
                    "pr_auc_std",
                    "folds",
                )
            },
            "temporal_cv": next(
                (
                    {
                        key: row.get(key)
                        for key in ("precision", "recall", "f1", "pr_auc", "roc_auc")
                    }
                    for row in metadata.get("temporal_cv", [])
                    if row.get("model") == metadata["model_name"]
                ),
                {},
            ),
        },
        "top_features": _top_features(),
        "training_runs": metadata["training_runs"],
        "feature_set_comparison": metadata.get("feature_set_comparison", []),
        "repeated_cv": repeated,
        "temporal_cv": metadata.get("temporal_cv", []),
        "hyperparameter_tuning": metadata.get("hyperparameter_tuning", []),
        "environment": metadata["environment"],
        "feature_importance_file": "backend/ml/artifacts/feature_importance.csv",
    }


def predict_event(event: dict, reference_events: Optional[pd.DataFrame] = None) -> dict:
    bundle = _load_bundle()
    payload = dict(event)
    payload.setdefault("province", "Unknown")
    payload.setdefault("city", "Unknown")
    payload.setdefault("date", date.today().isoformat())

    reference = reference_events if reference_events is not None else bundle["reference_events"]
    frame = build_inference_frame(payload, reference, include_context=True)
    X = select_columns(frame, bundle["feature_set"])
    probability = float(bundle["pipeline"].predict_proba(X)[:, 1][0])
    threshold = float(bundle["threshold"])
    boundaries = bundle.get("risk_level_boundaries", {"low": 0.25, "moderate": 0.5, "high": 0.75})
    risk_score = int(round(probability * 100))

    row = frame.iloc[0]
    factors = _build_factors(row)
    probability_band = "high" if probability >= boundaries["high"] else "medium" if probability >= threshold else "low"

    try:
        save_earthquake_prediction(
            location=f"{payload['city']}, {payload['province']}",
            risk_level=_risk_level(probability, boundaries),
            probability=risk_score,
            prediction_date=str(payload["date"]),
        )
    except Exception:
        logger.exception("Failed to store earthquake prediction")

    return {
        "success": True,
        "model": {
            "name": bundle["metadata"]["model_name"],
            "version": bundle["metadata"]["model_version"],
            "feature_set": bundle["feature_set"],
            "threshold": threshold,
        },
        "prediction": {
            "damage_probability": round(probability, 4),
            "damage_predicted": bool(probability >= threshold),
            "risk_score": risk_score,
            "risk_level": _risk_level(probability, boundaries),
            "confidence_band": probability_band,
            "threshold_used": threshold,
        },
        "factors": factors,
        "historical_context": _event_context(row),
        "event": {
            "magnitude": float(payload["magnitude"]),
            "depth_km": float(payload["depth_km"]),
            "latitude": float(payload["latitude"]),
            "longitude": float(payload["longitude"]),
            "province": payload["province"],
            "city": payload["city"],
            "date": str(payload["date"]),
        },
    }


def _recent_window(reference: pd.DataFrame, as_of: pd.Timestamp, days: int = 365) -> pd.DataFrame:
    dates = pd.to_datetime(reference["date"])
    return reference[dates >= (as_of - pd.Timedelta(days=days))]


def _scenario_event(
    reference: pd.DataFrame, city: str, province_hint: Optional[str], as_of: pd.Timestamp
) -> tuple[dict, str, pd.DataFrame, str]:
    reference = reference.copy()
    reference["date"] = pd.to_datetime(reference["date"])
    city_name, _ = _parse_city(city)

    city_events = reference[reference["city"].str.lower() == city_name.lower()]
    if len(city_events):
        recent = _recent_window(city_events, as_of)
        pool = recent if len(recent) else city_events
        scenario = pool.loc[pool["magnitude"].idxmax()]
        basis = "largest magnitude in the most recent 12 months of city history"
        return scenario.to_dict(), basis, city_events, "city"

    if province_hint:
        province_events = reference[reference["province"].str.lower() == province_hint.lower()]
        if len(province_events):
            recent = _recent_window(province_events, as_of)
            pool = recent if len(recent) else province_events
            scenario = pool.loc[pool["magnitude"].idxmax()]
            basis = "largest magnitude in the most recent 12 months of province history"
            return scenario.to_dict(), basis, province_events, "province"

    recent = _recent_window(reference, as_of)
    pool = recent if len(recent) else reference
    scenario = pool.loc[pool["magnitude"].idxmax()]
    basis = "default scenario because the city and province are not in the training data"
    return scenario.to_dict(), basis, reference, "national"


def city_risk(city: str) -> dict:
    bundle = _load_bundle()
    reference = bundle["reference_events"].copy()
    reference["date"] = pd.to_datetime(reference["date"])
    as_of = reference["date"].max()
    city_name, province_hint = _parse_city(city)

    scenario, basis, pool, scope = _scenario_event(reference, city, province_hint, as_of)
    if scope == "city":
        latitude = float(scenario["latitude"])
        longitude = float(scenario["longitude"])
        magnitude = float(scenario["magnitude"])
        depth = float(scenario["depth_km"])
        province = scenario.get("province") or (province_hint or "Unknown")
    elif scope == "province":
        latitude = float(pool["latitude"].mean())
        longitude = float(pool["longitude"].mean())
        magnitude = float(scenario["magnitude"])
        depth = float(scenario["depth_km"])
        province = province_hint or scenario.get("province") or "Unknown"
    else:
        latitude = float(reference["latitude"].mean())
        longitude = float(reference["longitude"].mean())
        magnitude = 4.0
        depth = 15.0
        province = province_hint or "Unknown"

    scenario_payload = {
        "magnitude": magnitude,
        "depth_km": depth,
        "latitude": latitude,
        "longitude": longitude,
        "province": province,
        "city": city_name,
        "date": (as_of + pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
    }
    prediction = predict_event(scenario_payload)

    recent_events = []
    if scope != "national":
        recent = pool.sort_values("date", ascending=False).head(5)
        for _, row in recent.iterrows():
            recent_events.append(
                {
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "magnitude": float(row["magnitude"]),
                    "depth_km": float(row["depth_km"]),
                    "latitude": float(row["latitude"]),
                    "longitude": float(row["longitude"]),
                    "city": row["city"],
                    "province": row["province"],
                }
            )

    prediction["location"] = {
        "city": city_name,
        "province": scenario_payload["province"],
        "latitude": float(scenario_payload["latitude"]),
        "longitude": float(scenario_payload["longitude"]),
        "as_of": as_of.strftime("%Y-%m-%d"),
        "basis": basis,
        "scope": scope,
        "events_in_scope": int(len(pool)) if scope != "national" else 0,
    }
    prediction["recent_events"] = recent_events
    prediction["data_source"] = "historical_dataset"
    return prediction


def _load_live_usgs_events(
    latitude: float, longitude: float, radius_km: int = 300, days: int = 365, minmagnitude: float = 2.5
) -> list[dict]:
    """Filter the cached regional USGS feed down to events near one city.

    The regional feed is fetched once per cache window and shared by every
    city, so many dashboard/page loads cost a single USGS request.
    """
    try:
        from services.usgs_earthquake_service import fetch_pakistan_events
    except ImportError:
        try:
            from backend.services.usgs_earthquake_service import fetch_pakistan_events
        except ImportError:
            return []
    try:
        data = fetch_pakistan_events(days=days, minmagnitude=minmagnitude)
    except Exception as exc:  # pragma: no cover - network must never break inference
        logger.warning("Live USGS lookup failed near %s,%s: %s", latitude, longitude, exc)
        return []

    events = []
    for event in data.get("events", []):
        if event.get("magnitude") is None or event.get("latitude") is None or event.get("longitude") is None:
            continue
        distance = haversine_km(latitude, longitude, event["latitude"], event["longitude"])
        if float(distance) <= radius_km:
            events.append(event)
    return events


def _live_events_frame(events: list[dict], city_name: str, province: str) -> pd.DataFrame:
    from datetime import datetime, timezone

    rows = []
    for event in events:
        timestamp = event.get("time")
        if timestamp:
            event_date = datetime.fromtimestamp(timestamp / 1000.0, tz=timezone.utc).strftime("%Y-%m-%d")
        else:
            event_date = date.today().isoformat()
        depth = event.get("depth_km")
        rows.append(
            {
                "date": event_date,
                "latitude": float(event["latitude"]),
                "longitude": float(event["longitude"]),
                "magnitude": float(event["magnitude"]),
                "depth_km": float(depth) if depth is not None else 10.0,
                "province": province or "Unknown",
                "city": city_name or "Unknown",
                "place": event.get("place"),
                "time": event.get("time"),
            }
        )
    return pd.DataFrame(rows)


def _event_time(event: dict) -> Optional[datetime]:
    timestamp = event.get("time")
    if not timestamp:
        return None
    try:
        return datetime.fromtimestamp(timestamp / 1000.0, tz=timezone.utc)
    except (TypeError, ValueError, OSError):
        return None


def _event_age_days(event: dict, now: Optional[datetime] = None) -> Optional[float]:
    event_time = _event_time(event)
    if event_time is None:
        return None
    now = now or datetime.now(timezone.utc)
    return max(0.0, (now - event_time).total_seconds() / 86400.0)


def _event_summary(event: dict, distance_km: float, now: Optional[datetime] = None) -> dict:
    event_time = _event_time(event)
    return {
        "magnitude": float(event["magnitude"]),
        "depth_km": float(event.get("depth_km") or 10.0),
        "latitude": float(event["latitude"]),
        "longitude": float(event["longitude"]),
        "distance_km": round(float(distance_km), 1),
        "date": event_time.date().isoformat() if event_time else None,
        "age_days": round(_event_age_days(event, now) or 0.0, 1),
        "place": event.get("place"),
    }


def _city_anchor(reference: pd.DataFrame, city_name: str, province_hint: Optional[str]) -> tuple[float, float, str]:
    city_events = reference[reference["city"].str.lower() == city_name.lower()]
    if len(city_events):
        province_series = city_events["province"].dropna()
        province = province_series.mode().iloc[0] if len(province_series) else (province_hint or "Unknown")
        return float(city_events["latitude"].mean()), float(city_events["longitude"].mean()), str(province)

    # Fall back to the general Pakistan city gazetteer so live USGS events are
    # fetched around the real city rather than the country centroid.
    try:
        from utils.helpers import find_pakistan_city
    except ImportError:  # pragma: no cover - package-style import
        try:
            from backend.utils.helpers import find_pakistan_city
        except ImportError:
            find_pakistan_city = None
    if find_pakistan_city is not None:
        match = find_pakistan_city(city_name)
        if match:
            return float(match["lat"]), float(match["lng"]), str(match.get("province") or province_hint or "Unknown")

    if province_hint:
        province_events = reference[reference["province"].str.lower() == province_hint.lower()]
        if len(province_events):
            return (
                float(province_events["latitude"].mean()),
                float(province_events["longitude"].mean()),
                province_hint,
            )
    return float(reference["latitude"].mean()), float(reference["longitude"].mean()), province_hint or "Unknown"


def city_risk_live(city: str) -> dict:
    """Predict current earthquake risk from nearby, recent USGS events.

    Only events within ``LIVE_RADIUS_KM`` and ``LIVE_WINDOW_DAYS`` drive the
    scenario, so an old or far-away quake can no longer make a quiet city look
    dangerous. When the feed is reachable but has no local events, a low-risk
    "quiet" prediction is returned; the historical model is used only when the
    feed itself is unavailable.
    """
    bundle = _load_bundle()
    reference = bundle["reference_events"].copy()
    reference["date"] = pd.to_datetime(reference["date"])
    city_name, province_hint = _parse_city(city)

    cache_key = city_name.strip().lower()
    with _live_city_lock:
        cached = _live_city_cache.get(cache_key)
        if cached and time.time() - cached[0] < LIVE_CITY_CACHE_TTL_SECONDS:
            return copy.deepcopy(cached[1])

    latitude, longitude, province = _city_anchor(reference, city_name, province_hint)
    now = datetime.now(timezone.utc)

    regional_events = _load_live_usgs_events(
        latitude, longitude, radius_km=LIVE_REGIONAL_RADIUS_KM, days=365
    )
    if not regional_events:
        result = city_risk(city)
        result["data_source"] = "historical_dataset_fallback"
        result["live_source"] = {
            "available": False,
            "reason": "USGS feed unavailable or no regional events",
            "radius_km": LIVE_REGIONAL_RADIUS_KM,
            "window_days": 365,
        }
        return result

    local_events: list[dict] = []
    nearest_event: Optional[dict] = None
    nearest_distance: Optional[float] = None
    regional_recent: Optional[dict] = None
    radius = LIVE_RADIUS_KM
    window = LIVE_WINDOW_DAYS
    for event in regional_events:
        distance = float(haversine_km(latitude, longitude, event["latitude"], event["longitude"]))
        if nearest_distance is None or distance < nearest_distance:
            nearest_event, nearest_distance = event, distance
        age = _event_age_days(event, now)
        if age is not None and age <= window:
            if regional_recent is None or float(event["magnitude"]) > regional_recent["magnitude"]:
                regional_recent = _event_summary(event, distance, now)
        if distance <= radius and age is not None and age <= window:
            local_events.append(event)

    nearest_summary = (
        _event_summary(nearest_event, nearest_distance, now) if nearest_event is not None else None
    )

    if local_events:
        live_frame = _live_events_frame(local_events, city_name, province)
        scenario_row = live_frame.loc[live_frame["magnitude"].idxmax()]
        combined = pd.concat([reference, live_frame], ignore_index=True)
        payload = {
            "magnitude": float(scenario_row["magnitude"]),
            "depth_km": float(scenario_row["depth_km"]),
            "latitude": latitude,
            "longitude": longitude,
            "province": province,
            "city": city_name,
            "date": str(scenario_row["date"]),
        }
        prediction = predict_event(payload, reference_events=combined)
        scenario_distance = float(
            haversine_km(latitude, longitude, scenario_row["latitude"], scenario_row["longitude"])
        )
        scenario = {
            "magnitude": float(scenario_row["magnitude"]),
            "depth_km": float(scenario_row["depth_km"]),
            "latitude": float(scenario_row["latitude"]),
            "longitude": float(scenario_row["longitude"]),
            "distance_km": round(scenario_distance, 1),
            "date": str(scenario_row["date"]),
            "place": scenario_row.get("place"),
        }
        basis = f"strongest USGS event within {radius} km in the last {window} days"
        events_in_scope = len(local_events)
        recent = [
            {
                "date": row["date"],
                "magnitude": float(row["magnitude"]),
                "depth_km": float(row["depth_km"]),
                "latitude": float(row["latitude"]),
                "longitude": float(row["longitude"]),
                "distance_km": round(
                    float(haversine_km(latitude, longitude, row["latitude"], row["longitude"])), 1
                ),
                "place": row.get("place"),
                "city": city_name,
                "province": province,
            }
            for _, row in live_frame.sort_values("time", ascending=False).head(5).iterrows()
        ]
    else:
        # Feed is alive but no local activity: a quiet, low-risk state. Regional
        # events still feed the context factors so seismicity stays visible.
        regional_frame = _live_events_frame(regional_events, city_name, province)
        combined = pd.concat([reference, regional_frame], ignore_index=True)
        prediction = predict_event(
            {
                "magnitude": 0.0,
                "depth_km": 10.0,
                "latitude": latitude,
                "longitude": longitude,
                "province": province,
                "city": city_name,
                "date": date.today().isoformat(),
            },
            reference_events=combined,
        )
        for factor in prediction.get("factors", []):
            if factor.get("key") == "magnitude":
                factor["value"] = "No local event"
                factor["score"] = 0.0
                factor["color"] = _bar_color(0.0)
            elif factor.get("key") == "depth":
                factor["value"] = "--"
                factor["score"] = 0.0
                factor["color"] = _bar_color(0.0)
            elif factor.get("key") == "local":
                factor["label"] = f"Local Density ({radius} km / {window}d)"
        scenario = None
        basis = f"no USGS events within {radius} km in the last {window} days"
        events_in_scope = 0
        recent = []

    prediction["location"] = {
        "city": city_name,
        "province": province,
        "latitude": latitude,
        "longitude": longitude,
        "as_of": date.today().isoformat(),
        "basis": basis,
        "scope": "live",
        "events_in_scope": int(events_in_scope),
        "radius_km": radius,
        "window_days": window,
        "nearest_event_km": round(nearest_distance, 1) if nearest_distance is not None else None,
        "scenario": scenario,
    }
    prediction["recent_events"] = recent
    prediction["data_source"] = "live_usgs"
    prediction["live_source"] = {
        "available": True,
        "source": "USGS FDSN Event Web Service",
        "count": int(events_in_scope),
        "regional_count": int(len(regional_events)),
        "radius_km": radius,
        "window_days": window,
        "nearest_event": nearest_summary,
        "regional_recent": regional_recent,
    }

    with _live_city_lock:
        _live_city_cache[cache_key] = (time.time(), copy.deepcopy(prediction))
    return prediction


def city_risk_auto(city: str, live: bool = False) -> dict:
    """Dispatch to live or historical earthquake prediction, falling back safely."""
    if live:
        return city_risk_live(city)
    return city_risk(city)


def clear_live_city_cache() -> None:
    """Reset the short-lived per-city live cache (used by tests)."""
    with _live_city_lock:
        _live_city_cache.clear()


def _event_record(row: pd.Series) -> dict:
    magnitude = float(row["magnitude"])
    depth = float(row["depth_km"])
    if magnitude >= 5:
        intensity = "Strong"
    elif magnitude >= 4:
        intensity = "Moderate"
    elif magnitude >= 3:
        intensity = "Light"
    else:
        intensity = "Minor"
    return {
        "date": row["date"].strftime("%Y-%m-%d"),
        "latitude": float(row["latitude"]),
        "longitude": float(row["longitude"]),
        "magnitude": magnitude,
        "depth_km": depth,
        "city": row["city"],
        "province": row["province"],
        "damage_occurred": int(row["damage_occurred"]),
        "deaths": int(row["deaths"]),
        "intensity": intensity,
    }


def _events_summary(events: pd.DataFrame) -> dict:
    if not len(events):
        return {
            "events": 0,
            "damaging_events": 0,
            "deaths": 0,
            "max_magnitude": 0.0,
            "mean_magnitude": 0.0,
            "mean_depth_km": 0.0,
            "date_min": None,
            "date_max": None,
        }
    return {
        "events": int(len(events)),
        "damaging_events": int(events["damage_occurred"].sum()),
        "deaths": int(events["deaths"].sum()),
        "max_magnitude": float(events["magnitude"].max()),
        "mean_magnitude": float(events["magnitude"].mean()),
        "mean_depth_km": float(events["depth_km"].mean()),
        "date_min": events["date"].min().strftime("%Y-%m-%d"),
        "date_max": events["date"].max().strftime("%Y-%m-%d"),
    }


def recent_events(city: Optional[str] = None, limit: int = 10) -> dict:
    bundle = _load_bundle()
    events = bundle["historical_events"].copy()
    events["date"] = pd.to_datetime(events["date"])

    scope = "national"
    if city:
        city_name, province_hint = _parse_city(city)
        mask = events["city"].str.lower() == city_name.lower()
        scope = "city"
        if not mask.any() and province_hint:
            mask = events["province"].str.lower() == province_hint.lower()
            scope = "province"
        events = events[mask]

    summary = _events_summary(events)
    events = events.sort_values("date", ascending=False).head(max(1, min(limit, 100)))
    return {
        "success": True,
        "scope": scope,
        "city": _parse_city(city)[0] if city else None,
        "count": int(len(events)),
        "summary": summary,
        "events": [_event_record(row) for _, row in events.iterrows()],
    }


def overview(limit: int = 60) -> dict:
    bundle = _load_bundle()
    events = bundle["historical_events"].copy()
    events["date"] = pd.to_datetime(events["date"])
    events = events.sort_values("date", ascending=False)

    summary = _events_summary(events)
    province_counts = (
        events.groupby("province")
        .agg(events=("magnitude", "size"), max_magnitude=("magnitude", "max"))
        .sort_values(["events", "max_magnitude"], ascending=False)
        .head(8)
        .reset_index()
    )
    city_counts = (
        events.groupby(["city", "province"])
        .agg(events=("magnitude", "size"), max_magnitude=("magnitude", "max"))
        .sort_values(["events", "max_magnitude"], ascending=False)
        .head(10)
        .reset_index()
    )
    latest = events.iloc[0]
    return {
        "success": True,
        "scope": "national",
        "summary": summary,
        "latest_event": _event_record(latest),
        "recent_events": [
            _event_record(row) for _, row in events.head(max(1, min(limit, 100))).iterrows()
        ],
        "provinces": [
            {
                "province": row["province"],
                "events": int(row["events"]),
                "max_magnitude": float(row["max_magnitude"]),
            }
            for _, row in province_counts.iterrows()
        ],
        "cities": [
            {
                "city": row["city"],
                "province": row["province"],
                "events": int(row["events"]),
                "max_magnitude": float(row["max_magnitude"]),
            }
            for _, row in city_counts.iterrows()
        ],
    }


def list_cities() -> dict:
    bundle = _load_bundle()
    events = bundle["historical_events"].copy()
    rows = []
    for (city, province), group in events.groupby(["city", "province"]):
        group = group.sort_values("date")
        rows.append(
            {
                "city": str(city),
                "province": str(province),
                "events": int(len(group)),
                "latitude": float(group["latitude"].mean()),
                "longitude": float(group["longitude"].mean()),
                "max_magnitude": float(group["magnitude"].max()),
            }
        )
    return {"success": True, "cities": sorted(rows, key=lambda item: item["city"])}
