"""Train a city-wise LSTM flood risk model (sequence model)."""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler

import tensorflow as tf
from tensorflow.keras import layers, models, callbacks

TARGET = "flood_occurred"

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = REPO_ROOT / "datasets" / "pakistan_flood_dataset_2020_2025 (1).csv"
DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts" / "flood_lstm"

LOOKBACK = 14
SEED = 42


def set_seeds():
    random.seed(SEED)
    np.random.seed(SEED)
    tf.random.set_seed(SEED)


def load_and_prepare(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"])
    # Aggregate duplicate city-date rows (justified: mean weather, max flood label)
    agg = df.groupby(["city", "date"], as_index=False).agg(
        {
            "latitude": "first",
            "longitude": "first",
            "province": "first",
            "rainfall_mm": "mean",
            "river_level_m": "mean",
            "flood_occurred": "max",
        }
    )
    agg = agg.sort_values(["city", "date"]).reset_index(drop=True)
    # time gap feature
    agg["days_since_previous"] = agg.groupby("city")["date"].diff().dt.days.fillna(0).astype(float)
    # calendar features
    agg["month_sin"] = np.sin(2 * np.pi * agg["date"].dt.month / 12.0)
    agg["month_cos"] = np.cos(2 * np.pi * agg["date"].dt.month / 12.0)
    return agg


def make_sequences(df: pd.DataFrame, lookback: int):
    feature_cols = [
        "rainfall_mm",
        "river_level_m",
        "latitude",
        "longitude",
        "days_since_previous",
        "month_sin",
        "month_cos",
    ]
    X_list, y_list, dates_list, cities_list = [], [], [], []
    for city, g in df.groupby("city"):
        g = g.sort_values("date").reset_index(drop=True)
        if len(g) <= lookback:
            continue
        vals = g[feature_cols].to_numpy(dtype=float)
        targets = g[TARGET].to_numpy(dtype=int)
        target_dates = g["date"].to_numpy()
        for i in range(lookback, len(g)):
            X_list.append(vals[i - lookback : i])
            y_list.append(targets[i])
            dates_list.append(target_dates[i])
            cities_list.append(city)
    X = np.array(X_list, dtype=float)
    y = np.array(y_list, dtype=int)
    return X, y, np.array(dates_list), cities_list, feature_cols


def main():
    set_seeds()
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", default=str(DEFAULT_DATA_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_ARTIFACT_DIR))
    args = parser.parse_args()

    data_path = Path(args.data)
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = load_and_prepare(data_path)
    X, y, dates, cities, feature_cols = make_sequences(df, LOOKBACK)
    print(f"Sequences: {len(X)} | lookback {LOOKBACK} | features {len(feature_cols)}")
    print(f"Positive rate: {y.mean():.4f}")

    # chronological split by target date
    order = np.argsort(dates)
    X, y, dates = X[order], y[order], dates[order]
    n = len(X)
    i_train = int(n * 0.70)
    i_val = int(n * 0.85)
    X_train, y_train = X[:i_train], y[:i_train]
    X_val, y_val = X[i_train:i_val], y[i_train:i_val]
    X_test, y_test = X[i_val:], y[i_val:]
    print(f"Train {len(X_train)}, Val {len(X_val)}, Test {len(X_test)}")

    # scale per feature using train only
    n_feat = X.shape[2]
    scaler = StandardScaler()
    X_train_flat = X_train.reshape(-1, n_feat)
    scaler.fit(X_train_flat)
    X_train = scaler.transform(X_train.reshape(-1, n_feat)).reshape(X_train.shape)
    X_val = scaler.transform(X_val.reshape(-1, n_feat)).reshape(X_val.shape)
    X_test = scaler.transform(X_test.reshape(-1, n_feat)).reshape(X_test.shape)

    # class weights
    pos = y_train.sum()
    neg = len(y_train) - pos
    class_weight = {0: 1.0, 1: neg / max(pos, 1)}

    # model
    model = models.Sequential(
        [
            layers.Input(shape=(LOOKBACK, n_feat)),
            layers.LSTM(32, return_sequences=False),
            layers.Dropout(0.3),
            layers.Dense(16, activation="relu"),
            layers.Dense(1, activation="sigmoid"),
        ]
    )
    model.compile(
        optimizer="adam",
        loss="binary_crossentropy",
        metrics=[
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
            tf.keras.metrics.AUC(name="auc"),
        ],
    )

    ckpt = out / "flood_lstm.keras"
    cb = [
        callbacks.EarlyStopping(monitor="val_loss", patience=10, restore_best_weights=True),
        callbacks.ModelCheckpoint(str(ckpt), monitor="val_loss", save_best_only=True),
        callbacks.ReduceLROnPlateau(monitor="val_loss", factor=0.5, patience=5),
    ]

    started = time.perf_counter()
    history = model.fit(
        X_train,
        y_train,
        validation_data=(X_val, y_val),
        epochs=50,
        batch_size=32,
        class_weight=class_weight,
        callbacks=cb,
        verbose=1,
    )
    train_time = time.perf_counter() - started

    # evaluate
    prob = model.predict(X_test, verbose=0).ravel()
    pred = (prob >= 0.5).astype(int)
    metrics = {
        "accuracy": float(accuracy_score(y_test, pred)),
        "precision": float(precision_score(y_test, pred, zero_division=0)),
        "recall": float(recall_score(y_test, pred, zero_division=0)),
        "f1": float(f1_score(y_test, pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, prob)),
        "pr_auc": float(average_precision_score(y_test, prob)),
        "confusion_matrix": confusion_matrix(y_test, pred, labels=[0, 1]).tolist(),
        "tn": int(confusion_matrix(y_test, pred, labels=[0, 1])[0, 0]),
        "fp": int(confusion_matrix(y_test, pred, labels=[0, 1])[0, 1]),
        "fn": int(confusion_matrix(y_test, pred, labels=[0, 1])[1, 0]),
        "tp": int(confusion_matrix(y_test, pred, labels=[0, 1])[1, 1]),
    }

    # save artifacts
    joblib.dump(scaler, out / "scaler.joblib")
    (out / "feature_schema.json").write_text(json.dumps(feature_cols, indent=2))
    (out / "training_history.json").write_text(
        json.dumps({k: [float(x) for x in v] for k, v in history.history.items()}, indent=2)
    )
    meta = {
        "model_name": "flood_lstm",
        "model_version": "1.0.0",
        "framework": "tensorflow",
        "framework_version": tf.__version__,
        "lookback": LOOKBACK,
        "prediction_horizon": "next observed record per city",
        "features": feature_cols,
        "threshold": 0.5,
        "split": {
            "train_sequences": int(len(X_train)),
            "val_sequences": int(len(X_val)),
            "test_sequences": int(len(X_test)),
            "train_target_date_max": str(pd.Timestamp(dates[i_train - 1]).date()),
            "val_target_date_max": str(pd.Timestamp(dates[i_val - 1]).date()),
            "test_target_date_max": str(pd.Timestamp(dates[-1]).date()),
        },
        "metrics": metrics,
        "training_seconds": float(train_time),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }
    (out / "model_metadata.json").write_text(json.dumps(meta, indent=2))
    (out / "evaluation_metrics.json").write_text(json.dumps(metrics, indent=2))

    print("Metrics:", metrics)
    print("Saved to", out)


if __name__ == "__main__":
    main()
