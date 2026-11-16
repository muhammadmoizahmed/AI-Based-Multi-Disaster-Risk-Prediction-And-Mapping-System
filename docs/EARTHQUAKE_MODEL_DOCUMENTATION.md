# Earthquake Damage-Risk Model — Training, Evaluation and Integration

**Project:** DisasterGuard — AI-Based Multi-Disaster Risk Prediction and Mapping System  
**Model:** RandomForest binary classifier for earthquake damage risk  
**Dataset:** `datasets/pakistan_earthquake_2020_2025.csv`  
**Notebook:** `backend/ml/notebooks/earthquake_risk_training.ipynb`  
**Training script:** `backend/ml/train_earthquake.py`  
**Serving code:** `backend/services/earthquake_service.py`, `backend/routes/earthquake.py`  
**Artifacts:** `backend/ml/artifacts/`

---

## 1. Executive summary

The earthquake module predicts whether an earthquake event is likely to cause **reported
damage** in Pakistan. It is a binary classification problem:

- `damage_occurred = 0` → no reported damage
- `damage_occurred = 1` → damage reported

The final model is a **RandomForestClassifier** trained on 26 engineered features
derived from latitude, longitude, magnitude, depth, province, city, time of year and
historical seismicity. The deployment threshold is **0.19**, derived from out-of-fold
predictions on the training partition with an F2 score so that recall is favoured over
precision (missing a damaging event is more costly than a false alarm).

Key results on the chronological holdout (last 20% of events, never used for tuning or
threshold selection):

| Metric | Value |
| --- | ---: |
| Accuracy | 1.0000 |
| Balanced accuracy | 1.0000 |
| Precision | 1.0000 |
| Recall | 1.0000 |
| F1-score | 1.0000 |
| F2-score | 1.0000 |
| ROC-AUC | 1.0000 |
| PR-AUC | 1.0000 |
| Confusion matrix | TN 123, FP 0, FN 0, TP 6 |

Repeated 5-fold × 3 stratified CV on the training partition gives **PR-AUC 0.9824 ±
0.0237**, **recall 0.8767**, **precision 0.9071** and **F1 0.8756** for RandomForest.
Temporal `TimeSeriesSplit` validation gives **PR-AUC 0.9394**, **F1 0.8190**.

The scores are high because the dataset is small and the labels are close to a rule:
damaging events are mostly magnitude ≥ 4.7 and relatively shallow. The model is therefore
a useful prototype, but it must not be treated as a validated operational earthquake
early-warning system without more real damage data and physical risk features.

---

## 2. Problem definition

**Input:** one earthquake event with:

| Column | Type | Meaning |
| --- | --- | --- |
| `date` | date | Event date |
| `latitude` | float | Epicentre latitude |
| `longitude` | float | Epicentre longitude |
| `magnitude` | float | Local/Richter magnitude |
| `depth_km` | float | Hypocentre depth |
| `city` | string | Nearest/associated city |
| `province` | string | Province or region |
| `damage_occurred` | 0/1 | Target: reported damage |
| `deaths` | int | Reported deaths |

**Output:** probability of damage, a 0–100 risk score, a risk level
(`low`, `moderate`, `high`, `extreme`), and the main contributing factors.

`deaths` is **not** a feature. It is an outcome of the same event and leaks the target.

---

## 3. Dataset

| Property | Value |
| --- | --- |
| Rows | 643 |
| Columns | 9 |
| Date range | 2020-01-01 to 2025-12-30 |
| Positive class (`damage_occurred = 1`) | 30 (4.67%) |
| Negative class | 613 (95.33%) |
| Provinces | Balochistan, AJK, KPK, GB, Punjab, ICT |
| Cities | 15 unique cities |
| Magnitude range | 1.5 – 6.2 |
| Depth range | 4.5 – 69.8 km |

### Province distribution

| Province | Events | Damaging events |
| --- | ---: | ---: |
| Balochistan | 213 | 16 |
| AJK | 117 | 8 |
| KPK | 117 | 1 |
| GB | 73 | 1 |
| Punjab | 64 | 0 |
| ICT | 59 | 0 |

### Damaging-event pattern

Most damaging events have magnitude ≥ 4.7 and depth ≤ ~21 km. This is the main reason the
classifier reaches very high precision/recall on a small dataset. It also means the
dataset behaves partly like a deterministic rule rather than a noisy real-world outcome.

---

## 4. Challenges

### 4.1 Very small dataset

643 rows is small for supervised learning. The positive class has only **30 examples**.
Confidence intervals around precision, recall and F1 are wide, and a single event can
change the holdout recall by 16.7 percentage points (1/6). All results should be read with
that limitation in mind.

### 4.2 Severe class imbalance

Only 4.67% of events are positive. A model that always predicts “no damage” would score
95.3% accuracy while catching zero damaging events. For this reason:

- accuracy is not the primary metric;
- PR-AUC, recall, F1 and balanced accuracy are reported;
- class weights are used (`class_weight="balanced_subsample"` for RandomForest);
- the decision threshold is tuned separately from 0.5.

### 4.3 Leakage risk

`deaths` is strongly correlated with `damage_occurred` and is a consequence of the same
event. Including it would produce artificially perfect scores. It was removed. Historical
features were also restricted to **earlier** events only (strictly earlier dates; same-day
events are excluded), and no previous-target/damage-count feature was used.

### 4.4 Near-deterministic labels

The target is almost a function of magnitude and depth. This produces high metrics but
limits what the model has actually learned. It is not evidence that the model would
generalise to real building damage, soil conditions or population exposure.

### 4.5 Missing physical and exposure features

The dataset does not contain:

- peak ground acceleration (PGA) or intensity (MMI);
- fault geometry and distance to the rupture plane;
- soil type / Vs30 / liquefaction potential;
- building stock, construction quality and population density;
- epicentre-to-settlement distance;
- focal mechanism, rupture length and directivity.

These are the features a production earthquake risk model would need.

### 4.6 Geographic imbalance

Balochistan and AJK dominate the positive class. Only 15 cities appear in the dataset,
while the frontend searches 150+ Pakistani cities. Unknown cities are handled by the
one-hot encoder with `handle_unknown="ignore"`. In the API, known cities use their own
history, known provinces use the province centroid and recent province events, and unknown
province/city pairs use a neutral default scenario (magnitude 4.0, depth 15 km) instead of
copying a distant high-magnitude event.

### 4.7 Temporal drift and short history

Six years of data are not enough to model long-term changes in exposure, building codes or
reporting quality. Temporal validation is used to check that the model can predict later
events from earlier ones, but the last holdout contains only six positives.

### 4.8 Threshold trade-off

For disaster alerts, a false negative (missed damaging event) is usually worse than a
false positive (unnecessary warning). The F1-optimal threshold was 0.19 and the F2-based
deployment threshold is also 0.19 on this data, both derived from out-of-fold predictions
on the training partition. The deployment threshold favours recall.

### 4.9 Model-selection note

Only `RandomForestClassifier` is used. No other algorithm is trained or deployed. The
feature set, hyperparameters and threshold are all selected on the training partition.

---

## 5. Feature selection

### 5.1 Candidate feature sets

Three nested feature sets were compared.

| Set | Features |
| --- | --- |
| `raw` | latitude, longitude, magnitude, depth, province, city |
| `static` | raw + magnitude², shallow-depth flags, magnitude/depth ratio, cyclical month, cyclical day-of-year, approximate fault-belt distance, near-fault flag |
| `context` | static + past 7/30/90-day event counts, past maximum magnitude (30/90 days), past mean depth (30 days), local density within 100 km/90 days, minimum distance to a past event, days since previous event, distance to previous event |

The `context` set has 26 feature columns:

- 4 raw numeric
- 10 static engineered
- 10 historical/context
- 2 categorical (`province`, `city`)

### 5.2 Why these features?

- **Magnitude** is the strongest physical driver of damage.
- **Depth** controls how much energy reaches the surface; shallow events are more damaging.
- **Latitude/longitude** capture the tectonic belt (Himalayan thrust, Chaman fault,
  Balochistan) and regional differences.
- **Magnitude² and magnitude/depth ratio** give the model non-linear and attenuation-aware
  combinations.
- **Cyclical month/day-of-year** encode seasonality without treating December and January
  as far apart.
- **Fault-belt distance** is an approximate domain feature built from a polyline through
  the main Himalayan/Chaman seismic belt. It is a proxy, not a real fault database.
- **Historical context** captures aftershock sequences and local clustering: recent event
  counts, recent maximum magnitude and local density.
- **Province/city** capture reporting and exposure differences.

### 5.3 Leakage features excluded

- `deaths` — outcome of the same event.
- Any historical count of past `damage_occurred` — would leak target information during
  validation and is hard to justify for a new event.
- The raw `date` string — replaced by cyclical time features.

### 5.4 Selection method

Each set was evaluated with 5-fold stratified CV using RandomForest, and the set with the
best mean PR-AUC was selected (training data only):

| Feature set | PR-AUC | Precision | Recall | F1 | Accuracy |
| --- | ---: | ---: | ---: | ---: | ---: |
| `raw` | 0.9853 | 0.9600 | 0.9100 | 0.9314 | — |
| `static` | 0.9248 | 0.8433 | 0.7400 | 0.7854 | — |
| `context` | **0.9886** | 0.9667 | 0.8300 | 0.8810 | — |

`context` won. Magnitude/depth already carry most of the signal and historical context
adds a small amount of information.

---

## 6. Training methodology

### 6.1 Preprocessing

All preprocessing is inside a scikit-learn `Pipeline`, so it is fitted only on training
folds and cannot leak test information:

- numeric: median imputation → standard scaling;
- categorical: most-frequent imputation → one-hot encoding with `handle_unknown="ignore"`;
- no SMOTE or synthetic positive samples were used because the dataset is very small and
  synthetic positives could distort the decision boundary.

### 6.2 Model

| Item | Value |
| --- | --- |
| Algorithm | RandomForestClassifier |
| Class weight | balanced_subsample |
| Random state | 42 |
| n_jobs | -1 |

### 6.3 Validation design

| Stage | Purpose |
| --- | --- |
| 5-fold stratified CV | Feature-set comparison and hyperparameter tuning (training only) |
| Repeated 5-fold × 3 CV | Stable estimate on the training partition |
| `TimeSeriesSplit(5)` | Temporal validation: train on past, test on future |
| Chronological 80/20 holdout | Final untouched test set (last 129 events, 6 positives) |

### 6.4 Hyperparameter tuning

`GridSearchCV` with scoring `average_precision` (PR-AUC) and 5-fold stratified CV on the
training partition. 36 candidate parameter sets.

Best parameters:

```text
n_estimators      = 300
max_depth         = None
min_samples_leaf  = 1
max_features      = 0.5
class_weight      = balanced_subsample
```

Best CV PR-AUC: 0.9933.

### 6.5 Threshold selection

Out-of-fold probabilities from 5-fold CV on the training partition were used to search
thresholds from 0.05 to 0.95.

| Criterion | Threshold | OOF score |
| --- | ---: | ---: |
| Default | 0.50 | — |
| Best F1 | 0.19 | F1 0.8889 |
| Best F2 (deployment) | 0.19 | F2 0.9524 |

The deployment threshold is **0.19**. F2 weights recall twice as much as precision, which
matches the disaster-alert use case.

---

## 7. Training runs — how many times was the model trained?

The pipeline performs **221 model fits** (verified from the executed run):

| Stage | Fits |
| --- | ---: |
| Feature-set comparison: 3 sets × 5 folds | 15 |
| Hyperparameter tuning: 36 candidate parameter sets × 5 folds | 180 |
| Out-of-fold threshold search: 5 folds | 5 |
| Repeated CV: 5 folds × 3 repeats | 15 |
| Temporal CV: 5 folds | 5 |
| Chronological holdout: 1 fit | 1 |
| Final refit on all data | 0 |
| **Total** | **221** |

The final RandomForest model uses **300 trees** (`n_estimators=300`). There are no
deep-learning epochs in this pipeline. Fixed random seeds make the results reproducible.

---

## 8. Results

### 8.1 Repeated stratified CV — 5 folds × 3 repeats (training partition)

| Metric | Value |
| --- | ---: |
| PR-AUC | 0.9824 ± 0.0237 |
| Precision | 0.9071 |
| Recall | 0.8767 |
| F1 | 0.8756 |
| ROC-AUC | 0.9990 |
| Accuracy | 0.9883 |

### 8.2 Temporal validation — TimeSeriesSplit, 5 folds

| Metric | Value |
| --- | ---: |
| PR-AUC | 0.9394 ± 0.0782 |
| Precision | 0.8667 |
| Recall | 0.7833 |
| F1 | 0.8190 |
| ROC-AUC | 0.9955 |
| Accuracy | 0.9859 |

### 8.3 Chronological holdout — last 20%

| Evaluation | Threshold | Accuracy | Balanced accuracy | Precision | Recall | F1 | ROC-AUC | PR-AUC | TP | FP | FN | TN |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Default | 0.50 | 0.9845 | 0.8333 | 1.0000 | 0.6667 | 0.8000 | 1.0000 | 1.0000 | 4 | 0 | 2 | 123 |
| Best F1 | 0.19 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 6 | 0 | 0 | 123 |
| **Deployment (F2)** | **0.19** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **1.0000** | **6** | **0** | **0** | **123** |

Classification report at the deployment threshold:

| Class | Precision | Recall | F1 | Support |
| --- | ---: | ---: | ---: | ---: |
| No damage | 1.000 | 1.000 | 1.000 | 123 |
| Damage | 1.000 | 1.000 | 1.000 | 6 |
| Macro average | 1.000 | 1.000 | 1.000 | 129 |
| Weighted average | 1.000 | 1.000 | 1.000 | 129 |

The CSV report uses the deployment threshold 0.19; the table above matches that report.
`earthquake_metrics.json` also stores the default and F1-optimal evaluations for
comparison.

### 8.4 Feature importance

Top tree-model importances from the final RandomForest model (trained on first 80%):

| Feature | Importance |
| --- | ---: |
| magnitude squared | 0.4092 |
| magnitude | 0.4033 |
| mag depth ratio | 0.0673 |
| min distance past km | 0.0473 |
| depth km | 0.0170 |
| distance to previous km | 0.0104 |
| prior max mag 30d | 0.0103 |
| prior mean depth 30d | 0.0050 |
| city = Quetta | 0.0043 |
| prior count 7d | 0.0041 |

Permutation importance on the holdout is dominated by magnitude. The holdout has only six
positives, so permutation importance is noisy and is reported for interpretation only.

---

## 9. Final model and decision rule

| Item | Value |
| --- | --- |
| Algorithm | RandomForestClassifier |
| Feature set | `context` |
| Final training rows | 514 |
| Trees | 300 |
| Max features | 0.5 |
| Max depth | None |
| Min samples leaf | 1 |
| Class weight | balanced_subsample |
| Deployment threshold | 0.19 |
| F1-optimal threshold | 0.19 |
| Default threshold | 0.50 |

Risk levels returned by the API:

| Probability | Risk level |
| --- | --- |
| < 0.25 | low |
| 0.25 – 0.499 | moderate |
| 0.50 – 0.749 | high |
| ≥ 0.75 | extreme |

The binary `damage_predicted` flag uses the deployment threshold (0.19). Risk level and
binary prediction are distinct outputs.

---

## 10. How the `.ipynb` trains the data

Notebook: `backend/ml/notebooks/earthquake_risk_training.ipynb`

Step-by-step:

1. **Setup** — locate the repository root and import `earthquake_features` and
   `train_earthquake`.
2. **EDA** — load the CSV, inspect shape, date range, class balance, province distribution
   and damaging events.
3. **Feature engineering** — call `engineer_features(df, include_context=True)` to build
   the 26 features.
4. **Training** — call `run_training(DATA_PATH, ARTIFACT_DIR)`. This runs all 221 fits,
   tunes the model, evaluates the holdout and writes the artifacts.
5. **Results** — display feature-set comparison, tuning results, repeated CV, temporal CV,
   holdout metrics, confusion matrix, classification report, feature importance and
   permutation importance.
6. **Integration demo** — call `predict_event()` from
   `backend/services/earthquake_service.py` and print the API-shaped response.

To re-run:

```bash
python -m jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=900 \
  backend/ml/notebooks/earthquake_risk_training.ipynb
```

Or train from the command line:

```bash
python backend/ml/train_earthquake.py
```

Both produce the same artifacts because all random seeds are fixed.

---

## 11. Integration with the project

### 11.1 Backend endpoints

Registered in `backend/main.py` via `backend/routes/earthquake.py`:

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/api/earthquake/predict` | Predict damage risk for a single event |
| GET | `/api/earthquake/risk-by-city?city=Harnai, Balochistan` | City-level scenario risk |
| GET | `/api/earthquake/events?city=Islamabad&limit=10` | Historical events |
| GET | `/api/earthquake/model-info` | Model metadata and metrics |

Example request:

```bash
curl -X POST http://localhost:5000/api/earthquake/predict \
  -H "Content-Type: application/json" \
  -d '{
    "magnitude": 5.8,
    "depth_km": 12.9,
    "latitude": 30.0,
    "longitude": 67.0,
    "province": "Balochistan",
    "city": "Harnai",
    "date": "2025-03-03"
  }'
```

Example response (abridged):

```json
{
  "success": true,
  "model": {
    "name": "random_forest",
    "version": "3.0.0",
    "feature_set": "context",
    "threshold": 0.19
  },
  "prediction": {
    "damage_probability": 0.942,
    "damage_predicted": true,
    "risk_score": 94,
    "risk_level": "extreme",
    "confidence_band": "high",
    "threshold_used": 0.19
  }
}
```

### 11.2 Frontend integration

`frontend/pages/earthquake.html` now calls the API:

- on load and on city selection, it calls `/api/earthquake/risk-by-city`;
- updates the risk score, risk badge and risk-factor bars;
- fills the recent-events panel and history table;
- updates the seismic-activity chart and magnitude-distribution chart;
- moves the Leaflet map markers to the returned events.

`frontend/admin/models.html` calls `/api/earthquake/model-info` and replaces the
randomised earthquake card values with the real holdout precision, recall and accuracy.

### 11.3 Model artifacts

| File | Purpose |
| --- | --- |
| `earthquake_model.joblib` | RandomForest pipeline trained on first 80% (deployment) |
| `earthquake_model_holdout.joblib` | Same pipeline retained for audit/reporting |
| `earthquake_metrics.json` | Full metrics, parameters and training-run counts |
| `feature_set_comparison.csv` | Feature-set comparison table |
| `hyperparameter_tuning.csv` | Tuning results |
| `repeated_cv_results.csv` | Repeated CV table |
| `temporal_cv_results.csv` | TimeSeriesSplit table |
| `holdout_classification_report.csv` | Holdout classification report |
| `feature_importance.csv` | Tree-model importance |
| `permutation_importance.csv` | Holdout permutation importance |
| `historical_events.csv` | Historical events used by the events endpoint |

---

## 12. Reproducibility

Environment used (from the executed run):

| Package | Version |
| --- | --- |
| Python | 3.11.0 |
| scikit-learn | 1.4.0 |
| pandas | 2.2.0 |
| numpy | 1.26.3 |

Install:

```bash
pip install -r backend/requirements.txt
```

Train:

```bash
python backend/ml/train_earthquake.py
```

Run the API:

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 5000 --reload
```

Run tests:

```bash
cd backend
python -m pytest tests -v
```

Then open `http://localhost:5000/pages/earthquake.html`.

---

## 13. Limitations and future work

1. **Collect more data** — more events, more years, and verified damage labels from NDMA,
   USGS, EMSC and PMD.
2. **Add physical features** — PGA/MMI, fault geometry, Vs30/soil, liquefaction,
   topographic amplification and rupture directivity.
3. **Add exposure features** — building type and age, population density, distance to
   settlements, critical infrastructure.
4. **Validate on a future year** — keep a truly unseen year for final testing.
5. **Calibrate probabilities** — Platt scaling or isotonic regression, then review alert
   thresholds with domain experts.
6. **Live data** — poll the USGS earthquake feed and retrain on a schedule.
7. **Cost-sensitive learning** — explicitly encode the relative cost of false negatives
   and false positives instead of relying only on threshold tuning.
8. **Spatial cross-validation** — group folds by region to test performance in unseen
   provinces.
9. **Small sample uncertainty** — 30 positives; metrics are optimistic and unstable.
10. **No validated early-warning claim** — this is a damage-risk prototype, not a
    validated earthquake early-warning system.

---

## 14. File map

```text
backend/
  ml/
    earthquake_features.py              # feature engineering and inference frame builder
    train_earthquake.py                 # RandomForest-only training/evaluation pipeline
    notebooks/
      earthquake_risk_training.ipynb    # executed notebook with outputs
    artifacts/
      earthquake_model.joblib
      earthquake_model_holdout.joblib
      earthquake_metrics.json
      feature_set_comparison.csv
      hyperparameter_tuning.csv
      repeated_cv_results.csv
      temporal_cv_results.csv
      holdout_classification_report.csv
      feature_importance.csv
      permutation_importance.csv
      historical_events.csv
  services/
    earthquake_service.py               # model loading and prediction service
  routes/
    earthquake.py                       # FastAPI endpoints
  models/
    disaster_models.py                  # request model
  tests/
    conftest.py
    test_earthquake.py
frontend/
  pages/earthquake.html                 # live risk UI
  admin/models.html                     # real earthquake metrics
docs/
  EARTHQUAKE_MODEL_DOCUMENTATION.md     # this document
```

---

## 15. Verification log

### Changed files

- `backend/ml/train_earthquake.py` — rewritten to RandomForest-only; chronological split
  before selection; train-only tuning/thresholds; no refit on all data.
- `backend/ml/earthquake_features.py` — strict-date context features; same-day exclusion
  in inference frame ordering.
- `backend/services/earthquake_service.py` — risk boundaries from metadata; consistency.
- `backend/tests/conftest.py` — new.
- `backend/tests/test_earthquake.py` — new (11 tests).
- `backend/ml/notebooks/earthquake_risk_training.ipynb` — updated and executed.
- `docs/EARTHQUAKE_MODEL_DOCUMENTATION.md` — rewritten with verified results.

### Training command

```bash
python backend/ml/train_earthquake.py
```

Result: completed in 114.4s; 221 model fits; selected feature set `context`; deployment
threshold 0.19; holdout accuracy/precision/recall/F1/ROC-AUC/PR-AUC all 1.0000 (TN 123,
FP 0, FN 0, TP 6).

### Test command

```bash
cd backend
python -m pytest tests -v
```

Result: **11 passed, 0 failed** (2 warnings: pyarrow deprecation, anyio deprecation).

### Unresolved limitations

- Only 30 positive cases; metrics are optimistic and unstable.
- No probability calibration.
- No geographic (spatial) cross-validation.
- No live USGS data feed.
- Threshold derived from a very small OOF sample.

### Steps still requiring manual verification

- Visual inspection of the frontend risk display after deployment.
- Domain-expert review of the 0.19 alert threshold.
- Validation on a truly unseen future year of data.
