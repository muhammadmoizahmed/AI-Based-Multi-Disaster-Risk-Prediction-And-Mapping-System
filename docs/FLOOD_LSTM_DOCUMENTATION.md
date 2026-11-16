# Flood LSTM Documentation

## Overview

DisasterGuard now includes a Flood LSTM module alongside the existing
Earthquake module. The LSTM predicts the flood outcome for the **next observed
record** of a selected city. It is not a daily forecast and must not be
presented as one.

## Dataset

Source: `datasets/pakistan_flood_dataset_2020_2025 (1).csv`

- 1,105 rows, 19 cities, dates from 2020-01-01 to 2025-12-30.
- Target: `flood_occurred` (374 positive, 731 negative).
- Sampling is irregular (1-30 days between observations).
- 16 duplicate city-date rows were aggregated before training.

## Sequence Preparation

- Group by `city` and `date`.
- Aggregate duplicates with mean weather and max flood label.
- Sort chronologically per city.
- Build 7 features per observation:
  1. rainfall_mm
  2. river_level_m
  3. latitude
  4. longitude
  5. days_since_previous
  6. month_sin
  7. month_cos
- Use 14 consecutive observations as one sequence.
- Predict the flood label of the 15th observed record.
- Chronological split by target date: 70% train, 15% validation, 15% test.
- StandardScaler fitted on training sequences only.

## Model

- Framework: TensorFlow/Keras 2.15.0.
- Architecture: LSTM(32), Dropout(0.3), Dense(16), Dense(1, sigmoid).
- Lookback: 14 observed records.
- Features: 7.
- Input shape: `(14, 7)`.
- Threshold: 0.50.

## Verified Metrics

- Accuracy: 0.8244
- Precision: 0.7321
- Recall: 0.8367
- F1: 0.7810
- ROC-AUC: 0.8654
- PR-AUC: 0.7650
- Confusion matrix: TN 67, FP 15, FN 8, TP 41.

These are lower than the previous RandomForest Flood baseline. The LSTM is
provided as an additional experimental model and is not claimed to be more
accurate.

## Artifacts

`backend/ml/artifacts/flood_lstm/`

- `flood_lstm.keras`
- `scaler.joblib`
- `feature_schema.json`
- `model_metadata.json`
- `evaluation_metrics.json`
- `training_history.json`

## Backend Integration

Service: `backend/services/flood_lstm_service.py`

- Loads and caches the Keras model and scaler.
- Validates artifact schema, feature order, lookback, and scaler.
- Builds genuine city-specific histories from the dataset.
- Applies the same aggregation and feature engineering used in training.
- Requires 14 observations; returns a clear error otherwise.
- Calculates risk level from probability.
- Persists predictions when database writes are enabled.

Routes: `backend/routes/flood_lstm.py`

- `GET /api/flood-lstm/model-info`
- `GET /api/flood-lstm/cities`
- `GET /api/flood-lstm/history`
- `GET /api/flood-lstm/overview`
- `POST /api/flood-lstm/predict`
- `GET /api/flood-lstm/predict-by-city`

Startup: `backend/main.py` preloads the Earthquake and Flood LSTM bundles and
includes both in `/ready`.

Database: `backend/database/db_flood_lstm.py`

- Table: `flood_lstm_predictions`.
- Stores city, coordinates, model version, probability, predicted class, risk
  level, threshold, observation date, timestamp, and input metadata.

## Frontend Integration

`frontend/pages/flood.html`

- Uses supported cities from `/api/flood-lstm/cities`.
- Runs `/api/flood-lstm/predict-by-city` for the selected city.
- Displays probability, predicted class, risk level, model version, horizon, and
  latest observation.
- Loads historical observations and charts real rainfall values.
- Renders city-wise risk markers on the map using dataset coordinates.
- Responsive layout for desktop, tablet, and mobile.

Admin: `frontend/admin/models.html`

- Loads real Flood LSTM metrics and version from `/api/flood-lstm/model-info`.
- Keeps Earthquake metrics separate.

Dashboard: `frontend/dashboard.html`

- Shows the highest current city risk from `/api/flood-lstm/overview`.

## Tests

- `backend/tests/test_flood_lstm.py`: 18 tests.
- Full backend suite: 30 tests passing.

## Limitations

- Predicts the next observed record, not the next calendar day.
- Requires 14 prior observations for the same city.
- Dataset is small and irregularly sampled.
- Metrics are below the prior RandomForest baseline.
- Not a validated flood early-warning system.