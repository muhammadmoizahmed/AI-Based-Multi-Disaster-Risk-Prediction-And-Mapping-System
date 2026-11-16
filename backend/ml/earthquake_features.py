"""Feature engineering utilities for the Pakistan earthquake risk model."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

TARGET = "damage_occurred"

RAW_NUMERIC_FEATURES = ["latitude", "longitude", "magnitude", "depth_km"]
CATEGORICAL_FEATURES = ["province", "city"]

STATIC_ENGINEERED_FEATURES = [
    "magnitude_squared",
    "is_shallow",
    "is_very_shallow",
    "mag_depth_ratio",
    "month_sin",
    "month_cos",
    "doy_sin",
    "doy_cos",
    "fault_distance_km",
    "near_fault",
]

CONTEXT_FEATURES = [
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
]

FEATURE_SETS = {
    "raw": RAW_NUMERIC_FEATURES + CATEGORICAL_FEATURES,
    "static": RAW_NUMERIC_FEATURES + STATIC_ENGINEERED_FEATURES + CATEGORICAL_FEATURES,
    "context": RAW_NUMERIC_FEATURES + STATIC_ENGINEERED_FEATURES + CONTEXT_FEATURES + CATEGORICAL_FEATURES,
}

FAULT_BELT_POINTS = [
    (36.10, 74.30),
    (35.60, 73.80),
    (35.00, 73.30),
    (34.50, 72.80),
    (34.00, 72.30),
    (33.50, 71.80),
    (33.00, 71.20),
    (32.30, 70.60),
    (31.50, 69.80),
    (30.60, 69.00),
    (29.70, 68.20),
    (28.80, 67.40),
    (27.90, 66.70),
    (27.00, 66.20),
]


def haversine_km(lat1, lon1, lat2, lon2):
    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)
    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    return 6371.0 * 2.0 * np.arcsin(np.sqrt(np.clip(a, 0.0, 1.0)))


def load_data(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)
    return df


def _fault_distance(latitude: np.ndarray, longitude: np.ndarray) -> np.ndarray:
    distances = []
    for lat, lon in zip(latitude, longitude):
        d = haversine_km(lat, lon, np.array([p[0] for p in FAULT_BELT_POINTS]), np.array([p[1] for p in FAULT_BELT_POINTS]))
        distances.append(float(np.min(d)))
    return np.array(distances)


def _context_features(df: pd.DataFrame) -> pd.DataFrame:
    n = len(df)
    dates = df["date"].to_numpy()
    latitudes = df["latitude"].to_numpy()
    longitudes = df["longitude"].to_numpy()
    magnitudes = df["magnitude"].to_numpy()
    depths = df["depth_km"].to_numpy()

    out = {
        "prior_count_7d": np.zeros(n),
        "prior_count_30d": np.zeros(n),
        "prior_count_90d": np.zeros(n),
        "prior_max_mag_30d": np.zeros(n),
        "prior_max_mag_90d": np.zeros(n),
        "prior_mean_depth_30d": np.full(n, np.nan),
        "prior_count_100km_90d": np.zeros(n),
        "min_distance_past_km": np.full(n, 9999.0),
        "days_since_previous": np.full(n, 9999.0),
        "distance_to_previous_km": np.full(n, 9999.0),
    }

    for i in range(n):
        past_mask = dates < dates[i]
        if not past_mask.any():
            continue
        past_indices = np.flatnonzero(past_mask)
        past_days = (dates[i] - dates[past_mask]) / np.timedelta64(1, "D")
        last_7 = past_days <= 7
        last_30 = past_days <= 30
        last_90 = past_days <= 90

        out["prior_count_7d"][i] = int(last_7.sum())
        out["prior_count_30d"][i] = int(last_30.sum())
        out["prior_count_90d"][i] = int(last_90.sum())

        if last_30.any():
            out["prior_max_mag_30d"][i] = float(np.max(magnitudes[past_mask][last_30]))
            out["prior_mean_depth_30d"][i] = float(np.mean(depths[past_mask][last_30]))
        if last_90.any():
            out["prior_max_mag_90d"][i] = float(np.max(magnitudes[past_mask][last_90]))

        d_all = haversine_km(latitudes[i], longitudes[i], latitudes[past_mask], longitudes[past_mask])
        out["min_distance_past_km"][i] = float(np.min(d_all))
        prev_idx = int(past_indices[-1])
        out["distance_to_previous_km"][i] = float(
            haversine_km(latitudes[i], longitudes[i], latitudes[prev_idx], longitudes[prev_idx])
        )
        out["days_since_previous"][i] = float((dates[i] - dates[prev_idx]) / np.timedelta64(1, "D"))
        out["prior_count_100km_90d"][i] = int((last_90 & (d_all <= 100.0)).sum())

    return pd.DataFrame(out, index=df.index)


def engineer_features(df: pd.DataFrame, include_context: bool = True) -> pd.DataFrame:
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"])

    out["magnitude_squared"] = out["magnitude"] ** 2
    out["is_shallow"] = (out["depth_km"] < 30).astype(int)
    out["is_very_shallow"] = (out["depth_km"] < 15).astype(int)
    out["mag_depth_ratio"] = out["magnitude"] / out["depth_km"].clip(lower=1.0)

    month = out["date"].dt.month
    day_of_year = out["date"].dt.dayofyear
    out["month_sin"] = np.sin(2 * np.pi * month / 12.0)
    out["month_cos"] = np.cos(2 * np.pi * month / 12.0)
    out["doy_sin"] = np.sin(2 * np.pi * day_of_year / 365.25)
    out["doy_cos"] = np.cos(2 * np.pi * day_of_year / 365.25)

    out["fault_distance_km"] = _fault_distance(out["latitude"].to_numpy(), out["longitude"].to_numpy())
    out["near_fault"] = (out["fault_distance_km"] <= 100.0).astype(int)

    if include_context:
        out = pd.concat([out, _context_features(out)], axis=1)

    return out


def build_inference_frame(event: dict, reference_events: pd.DataFrame, include_context: bool = True) -> pd.DataFrame:
    event_row = dict(event)
    event_row["_is_new"] = 1
    reference = reference_events.copy()
    reference["_is_new"] = 0
    if TARGET not in reference.columns:
        reference[TARGET] = 0
    if TARGET not in event_row:
        event_row[TARGET] = 0

    combined = pd.concat([reference, pd.DataFrame([event_row])], ignore_index=True)
    combined["date"] = pd.to_datetime(combined["date"])
    combined = combined.sort_values(["date", "_is_new"], ascending=[True, False], kind="mergesort").reset_index(drop=True)
    features = engineer_features(combined, include_context=include_context)
    row = features[features["_is_new"] == 1].tail(1).drop(columns=["_is_new"])
    return row


def select_columns(frame: pd.DataFrame, feature_set: str) -> pd.DataFrame:
    columns = FEATURE_SETS[feature_set]
    return frame[columns].copy()


def split_X_y(frame: pd.DataFrame, feature_set: str):
    X = select_columns(frame, feature_set)
    y = frame[TARGET].astype(int)
    return X, y
