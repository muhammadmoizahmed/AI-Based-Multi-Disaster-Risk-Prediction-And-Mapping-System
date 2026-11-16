# Flood LSTM Verification Report

## 1. Artifact Loading
- `flood_lstm.keras` loaded successfully with TensorFlow 2.15.0.
- Input shape verified: `(None, 14, 7)`.

## 2. Scaler and Feature Schema
- Scaler loaded successfully.
- Feature schema: rainfall_mm, river_level_m, latitude, longitude, days_since_previous, month_sin, month_cos.
- Feature count: 7.

## 3. Sequence Dimensions
- Lookback: 14 observed records.
- Features per step: 7.
- Shape verified: `(samples, 14, 7)`.

## 4. Chronology and Leakage
- Sequences are built per city from chronologically sorted records.
- Duplicate city-date rows were aggregated before sequence creation.
- Train/validation/test split is chronological by target date.
- Scaler was fit only on training data.
- No random splitting used.

## 5. API Verification
- `GET /api/flood-lstm/model-info` returns model metadata and metrics.
- `POST /api/flood-lstm/predict` returns valid probability and prediction.
- Invalid dimensions return HTTP 422.

## 6. Metric Reproduction
Reproduced test metrics from saved model:
- Accuracy: 0.8244
- Precision: 0.7321
- Recall: 0.8367
- F1: 0.7810
- ROC-AUC: 0.8654
- PR-AUC: 0.7650
- Confusion matrix: TN 67, FP 15, FN 8, TP 41

These match `evaluation_metrics.json`.

## 7. Existing RandomForest Flood Model
- The original RandomForest Flood model was removed earlier at user request.
- No RandomForest Flood artifacts or service remain.
- Only the LSTM Flood module is present.

## 8. Test Results
- Project test suite: 12 passed, 4 warnings.

## 9. Earthquake Module
- Earthquake module and artifacts were not modified.
- Earthquake tests pass.

## Notes
- The sequence predicts the next observed record, not necessarily the next calendar day.
- The dataset is irregularly sampled and small; metrics are not evidence of real-world reliability.
- This is not a validated flood early-warning system.