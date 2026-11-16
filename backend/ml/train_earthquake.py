"""Train and evaluate the Pakistan earthquake damage-risk model (RandomForest only).

Usage:
    python -m backend.ml.train_earthquake
    python backend/ml/train_earthquake.py
"""

from __future__ import annotations

import argparse
import json
import platform
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import (
    GridSearchCV,
    RepeatedStratifiedKFold,
    StratifiedKFold,
    TimeSeriesSplit,
    cross_val_predict,
    cross_validate,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from .earthquake_features import (
        CATEGORICAL_FEATURES,
        FEATURE_SETS,
        TARGET,
        engineer_features,
        load_data,
        select_columns,
    )
except ImportError:
    from earthquake_features import (
        CATEGORICAL_FEATURES,
        FEATURE_SETS,
        TARGET,
        engineer_features,
        load_data,
        select_columns,
    )

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATA_PATH = REPO_ROOT / "datasets" / "pakistan_earthquake_2020_2025.csv"
DEFAULT_ARTIFACT_DIR = Path(__file__).resolve().parent / "artifacts"

SCORING = {
    "accuracy": "accuracy",
    "balanced_accuracy": "balanced_accuracy",
    "precision": "precision",
    "recall": "recall",
    "f1": "f1",
    "roc_auc": "roc_auc",
    "pr_auc": "average_precision",
}

RISK_LEVEL_BOUNDARIES = {"low": 0.25, "moderate": 0.5, "high": 0.75}


def _json_ready(value):
    if isinstance(value, dict):
        return {str(k): _json_ready(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_ready(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.ndarray,)):
        return value.tolist()
    if isinstance(value, (pd.Timestamp,)):
        return value.isoformat()
    return value


def make_preprocessor(X: pd.DataFrame) -> ColumnTransformer:
    categorical = [c for c in CATEGORICAL_FEATURES if c in X.columns]
    numeric = [c for c in X.columns if c not in categorical]

    numeric_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        [
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
        ]
    )
    return ColumnTransformer(
        [
            ("numeric", numeric_pipeline, numeric),
            ("categorical", categorical_pipeline, categorical),
        ],
        remainder="drop",
    )


def build_model(X: pd.DataFrame) -> Pipeline:
    model = RandomForestClassifier(
        n_estimators=400,
        class_weight="balanced_subsample",
        max_features="sqrt",
        min_samples_leaf=1,
        random_state=42,
        n_jobs=-1,
    )
    return Pipeline([("preprocessor", make_preprocessor(X)), ("model", model)])


def model_grids() -> dict:
    return {
        "random_forest": {
            "model__n_estimators": [300, 600],
            "model__max_depth": [None, 6, 10],
            "model__min_samples_leaf": [1, 2, 4],
            "model__max_features": ["sqrt", 0.5],
        }
    }


def evaluate_predictions(y_true, probabilities, threshold=0.5) -> dict:
    predictions = (probabilities >= threshold).astype(int)
    cm = confusion_matrix(y_true, predictions, labels=[0, 1])
    return {
        "threshold": float(threshold),
        "accuracy": float(accuracy_score(y_true, predictions)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, predictions)),
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1": float(f1_score(y_true, predictions, zero_division=0)),
        "f2": float(
            (5 * precision_score(y_true, predictions, zero_division=0) * recall_score(y_true, predictions, zero_division=0))
            / (4 * precision_score(y_true, predictions, zero_division=0) + recall_score(y_true, predictions, zero_division=0) + 1e-12)
        ),
        "roc_auc": float(roc_auc_score(y_true, probabilities)),
        "pr_auc": float(average_precision_score(y_true, probabilities)),
        "confusion_matrix": cm.tolist(),
        "tn": int(cm[0, 0]),
        "fp": int(cm[0, 1]),
        "fn": int(cm[1, 0]),
        "tp": int(cm[1, 1]),
    }


def best_f1_threshold(y_true, probabilities) -> tuple[float, float]:
    best_threshold, best_score = 0.5, -1.0
    for threshold in np.arange(0.05, 0.951, 0.01):
        score = f1_score(y_true, (probabilities >= threshold).astype(int), zero_division=0)
        if score > best_score:
            best_threshold, best_score = float(round(threshold, 2)), float(score)
    return best_threshold, best_score


def best_fbeta_threshold(y_true, probabilities, beta: float = 2.0) -> tuple[float, float]:
    best_threshold, best_score = 0.5, -1.0
    for threshold in np.arange(0.05, 0.951, 0.01):
        predictions = (probabilities >= threshold).astype(int)
        precision = precision_score(y_true, predictions, zero_division=0)
        recall = recall_score(y_true, predictions, zero_division=0)
        beta_squared = beta ** 2
        score = (1 + beta_squared) * precision * recall / (beta_squared * precision + recall + 1e-12)
        if score > best_score:
            best_threshold, best_score = float(round(threshold, 2)), float(score)
    return best_threshold, best_score


def cv_summary(pipeline, X, y, cv) -> dict:
    scores = cross_validate(pipeline, X, y, cv=cv, scoring=SCORING, n_jobs=-1, error_score="raise")
    result = {}
    for metric in SCORING:
        values = scores[f"test_{metric}"]
        result[metric] = float(np.mean(values))
        result[f"{metric}_std"] = float(np.std(values))
    result["folds"] = int(len(scores["fit_time"]))
    result["fit_seconds"] = float(np.sum(scores["fit_time"]))
    return result


def model_feature_importance(pipeline: Pipeline) -> pd.DataFrame | None:
    model = pipeline.named_steps["model"]
    if not hasattr(model, "feature_importances_"):
        return None
    names = pipeline.named_steps["preprocessor"].get_feature_names_out()
    values = model.feature_importances_
    return (
        pd.DataFrame({"feature": names, "importance": values})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )


def run_training(data_path: str | Path = DEFAULT_DATA_PATH, artifact_dir: str | Path = DEFAULT_ARTIFACT_DIR) -> dict:
    started_at = datetime.now(timezone.utc)
    started_clock = time.perf_counter()
    data_path = Path(data_path)
    artifact_dir = Path(artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)

    df = load_data(data_path)
    y_all = df[TARGET].astype(int)
    positive = int(y_all.sum())
    negative = int(len(y_all) - positive)
    scale_pos_weight = negative / max(positive, 1)

    engineered = engineer_features(df, include_context=True)
    print(f"Dataset: {len(df)} rows | {positive} positives | {negative} negatives ({positive / len(df):.2%})")

    # Chronological split: the final 20% is held out and never used for feature-set
    # selection, tuning, threshold selection or CV.
    split_index = int(len(engineered) * 0.8)
    train_frame = engineered.iloc[:split_index].copy()
    test_frame = engineered.iloc[split_index:].copy()
    train_positives = int(train_frame[TARGET].sum())
    test_positives = int(test_frame[TARGET].sum())
    print(f"Train: {len(train_frame)} rows | {train_positives} positives")
    print(f"Test:  {len(test_frame)} rows | {test_positives} positives")

    baseline_cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    # Stage 1 - feature-set comparison (RandomForest only, training data only)
    comparison_rows = []
    comparison_runs = 0
    print("\nStage 1 - feature-set comparison with RandomForest")
    for feature_set in FEATURE_SETS:
        X, y = _xy(train_frame, feature_set)
        pipeline = build_model(X)
        summary = cv_summary(pipeline, X, y, baseline_cv)
        comparison_runs += summary["folds"]
        row = {"feature_set": feature_set, "model": "random_forest", **summary}
        comparison_rows.append(row)
        print(
            f"  {feature_set:8s} random_forest       "
            f"PR-AUC={summary['pr_auc']:.4f} F1={summary['f1']:.4f} "
            f"Recall={summary['recall']:.4f} Precision={summary['precision']:.4f}"
        )

    comparison = pd.DataFrame(comparison_rows)
    comparison.to_csv(artifact_dir / "feature_set_comparison.csv", index=False)

    feature_set_scores = comparison.groupby("feature_set")["pr_auc"].mean().sort_values(ascending=False)
    selected_feature_set = str(feature_set_scores.index[0])
    print(f"\nSelected feature set: {selected_feature_set} (mean PR-AUC {feature_set_scores.iloc[0]:.4f})")

    # Stage 2 - hyperparameter tuning (RandomForest only, training data only)
    X, y = _xy(train_frame, selected_feature_set)
    grids = model_grids()
    tuning_rows = []
    tuning_runs = 0
    print("\nStage 2 - hyperparameter tuning (5-fold stratified)")
    search = GridSearchCV(
        build_model(X),
        grids["random_forest"],
        scoring="average_precision",
        cv=baseline_cv,
        n_jobs=-1,
        refit=True,
        error_score="raise",
    )
    search.fit(X, y)
    tuning_runs += len(search.cv_results_["params"]) * baseline_cv.get_n_splits()
    tuned_pipeline = search.best_estimator_
    tuning_rows.append(
        {
            "model": "random_forest",
            "feature_set": selected_feature_set,
            "best_cv_pr_auc": float(search.best_score_),
            "best_params": json.dumps(search.best_params_),
            "candidate_parameter_sets": int(len(search.cv_results_["params"])),
            "cv_folds": int(baseline_cv.get_n_splits()),
        }
    )
    tuning = pd.DataFrame(tuning_rows)
    tuning.to_csv(artifact_dir / "hyperparameter_tuning.csv", index=False)
    print(f"  random_forest       best CV PR-AUC={search.best_score_:.4f} params={search.best_params_}")

    # Stage 3 - repeated stratified CV (RandomForest only, training data only)
    repeated_cv = RepeatedStratifiedKFold(n_splits=5, n_repeats=3, random_state=42)
    repeated_rows = []
    repeated_runs = 0
    print("\nStage 3 - repeated stratified CV (5 folds x 3 repeats)")
    summary = cv_summary(tuned_pipeline, X, y, repeated_cv)
    repeated_runs += summary["folds"]
    repeated_rows.append({"model": "random_forest", "feature_set": selected_feature_set, **summary})
    print(
        f"  random_forest       PR-AUC={summary['pr_auc']:.4f} +/- {summary['pr_auc_std']:.4f} | "
        f"F1={summary['f1']:.4f} | Recall={summary['recall']:.4f} | Precision={summary['precision']:.4f}"
    )
    repeated = pd.DataFrame(repeated_rows)
    repeated.to_csv(artifact_dir / "repeated_cv_results.csv", index=False)

    # Stage 4 - temporal validation (RandomForest only, training data only)
    print("\nStage 4 - temporal validation (TimeSeriesSplit, 5 folds)")
    temporal_rows = []
    temporal_runs = 0
    temporal_summary = cv_summary(tuned_pipeline, X, y, TimeSeriesSplit(n_splits=5))
    temporal_runs += temporal_summary["folds"]
    temporal_rows.append({"model": "random_forest", "feature_set": selected_feature_set, **temporal_summary})
    print(
        f"  random_forest       PR-AUC={temporal_summary['pr_auc']:.4f} | "
        f"F1={temporal_summary['f1']:.4f} | Recall={temporal_summary['recall']:.4f}"
    )
    temporal = pd.DataFrame(temporal_rows)
    temporal.to_csv(artifact_dir / "temporal_cv_results.csv", index=False)

    best_model_name = "random_forest"
    best_pipeline_tuned = tuned_pipeline

    # Stage 5 - chronological holdout (last 20%, untouched until now)
    X_train, y_train = _xy(train_frame, selected_feature_set)
    X_test, y_test = _xy(test_frame, selected_feature_set)

    holdout_pipeline = clone(best_pipeline_tuned)
    holdout_pipeline.fit(X_train, y_train)
    holdout_fits = 1

    print("\nStage 5 - chronological holdout (last 20%)")
    holdout_probabilities = holdout_pipeline.predict_proba(X_test)[:, 1]
    holdout_default = evaluate_predictions(y_test, holdout_probabilities, 0.5)

    # Threshold selection from out-of-fold predictions on TRAINING DATA ONLY.
    oof_probabilities = cross_val_predict(
        best_pipeline_tuned,
        X_train,
        y_train,
        cv=baseline_cv,
        method="predict_proba",
        n_jobs=-1,
    )[:, 1]
    oof_fits = baseline_cv.get_n_splits()
    tuned_threshold, oof_best_f1 = best_f1_threshold(y_train, oof_probabilities)
    deployment_threshold, oof_best_f2 = best_fbeta_threshold(y_train, oof_probabilities, beta=2.0)
    holdout_tuned = evaluate_predictions(y_test, holdout_probabilities, tuned_threshold)
    holdout_deployment = evaluate_predictions(y_test, holdout_probabilities, deployment_threshold)
    print(
        f"  Holdout @0.50: PR-AUC={holdout_default['pr_auc']:.4f} "
        f"P={holdout_default['precision']:.4f} R={holdout_default['recall']:.4f} F1={holdout_default['f1']:.4f}"
    )
    print(
        f"  Holdout @{tuned_threshold:.2f} (best F1): P={holdout_tuned['precision']:.4f} "
        f"R={holdout_tuned['recall']:.4f} F1={holdout_tuned['f1']:.4f}"
    )
    print(
        f"  Holdout @{deployment_threshold:.2f} (best F2/safety): P={holdout_deployment['precision']:.4f} "
        f"R={holdout_deployment['recall']:.4f} F1={holdout_deployment['f1']:.4f}"
    )
    print(f"  OOF best F1: {oof_best_f1:.4f} at threshold {tuned_threshold:.2f}")
    print(f"  OOF best F2: {oof_best_f2:.4f} at threshold {deployment_threshold:.2f}")

    holdout_report = pd.DataFrame(
        classification_report(
            y_test,
            (holdout_probabilities >= deployment_threshold).astype(int),
            output_dict=True,
            zero_division=0,
        )
    ).transpose()
    holdout_report.to_csv(artifact_dir / "holdout_classification_report.csv")

    # Stage 6 - permutation importance on chronological holdout
    print("\nStage 6 - permutation importance on chronological holdout")
    importance = permutation_importance(
        holdout_pipeline,
        X_test,
        y_test,
        scoring="average_precision",
        n_repeats=20,
        random_state=42,
        n_jobs=-1,
    )
    permutation = (
        pd.DataFrame(
            {
                "feature": X_test.columns,
                "importance_mean": importance.importances_mean,
                "importance_std": importance.importances_std,
            }
        )
        .sort_values("importance_mean", ascending=False)
        .reset_index(drop=True)
    )
    permutation.to_csv(artifact_dir / "permutation_importance.csv", index=False)
    print(permutation.head(10).to_string(index=False))

    # Deployed model = trained on first 80% only (no refit on all data).
    deployed_pipeline = holdout_pipeline
    tree_importance = model_feature_importance(deployed_pipeline)
    if tree_importance is not None:
        tree_importance.to_csv(artifact_dir / "feature_importance.csv", index=False)

    metadata = {
        "model_name": best_model_name,
        "model_family": "RandomForestClassifier",
        "model_version": "3.0.0",
        "deployment_note": (
            "RandomForest-only pipeline. Model trained on the first 80% of chronological "
            "data; evaluation uses the untouched final 20%. No refit on all data."
        ),
        "feature_set": selected_feature_set,
        "feature_columns": list(FEATURE_SETS[selected_feature_set]),
        "threshold": float(deployment_threshold),
        "thresholds": {
            "default": 0.5,
            "f1_optimal": float(tuned_threshold),
            "deployment_f2_safety": float(deployment_threshold),
        },
        "risk_level_boundaries": dict(RISK_LEVEL_BOUNDARIES),
        "trained_at": started_at.isoformat(),
        "dataset": {
            "path": str(data_path.relative_to(REPO_ROOT)) if data_path.is_relative_to(REPO_ROOT) else str(data_path),
            "rows": int(len(df)),
            "positives": positive,
            "negatives": negative,
            "positive_rate": float(positive / len(df)),
            "date_min": str(df["date"].min().date()),
            "date_max": str(df["date"].max().date()),
            "training_rows": int(len(train_frame)),
            "training_positives": train_positives,
            "test_rows": int(len(test_frame)),
            "test_positives": test_positives,
        },
        "evaluation": {
            "holdout_default_threshold": holdout_default,
            "holdout_f1_optimal_threshold": holdout_tuned,
            "holdout_deployment_threshold": holdout_deployment,
            "oof_threshold_search_best_f1": float(oof_best_f1),
            "oof_threshold_search_best_f2": float(oof_best_f2),
        },
        "feature_set_comparison": comparison.to_dict(orient="records"),
        "repeated_cv": repeated.to_dict(orient="records"),
        "temporal_cv": temporal.to_dict(orient="records"),
        "hyperparameter_tuning": tuning.to_dict(orient="records"),
        "training_runs": {
            "feature_set_comparison_fits": int(comparison_runs),
            "hyperparameter_candidate_sets": int(sum(tuning["candidate_parameter_sets"])),
            "hyperparameter_fits": int(tuning_runs),
            "oof_threshold_fits": int(oof_fits),
            "repeated_cv_fits": int(repeated_runs),
            "temporal_cv_fits": int(temporal_runs),
            "holdout_fits": int(holdout_fits),
            "final_refit_fits": 0,
            "total_fits": int(
                comparison_runs + tuning_runs + oof_fits + repeated_runs + temporal_runs + holdout_fits
            ),
        },
        "environment": {
            "python": platform.python_version(),
            "scikit_learn": sklearn.__version__,
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
        "training_seconds": float(time.perf_counter() - started_clock),
    }

    historical_events = df.copy()
    historical_events["date"] = historical_events["date"].dt.strftime("%Y-%m-%d")
    reference_events = historical_events.drop(columns=[TARGET, "deaths"], errors="ignore")
    historical_events.to_csv(artifact_dir / "historical_events.csv", index=False)

    bundle = {
        "pipeline": deployed_pipeline,
        "feature_set": selected_feature_set,
        "feature_columns": list(FEATURE_SETS[selected_feature_set]),
        "threshold": float(deployment_threshold),
        "thresholds": {
            "default": 0.5,
            "f1_optimal": float(tuned_threshold),
            "deployment_f2_safety": float(deployment_threshold),
        },
        "risk_level_boundaries": dict(RISK_LEVEL_BOUNDARIES),
        "metadata": metadata,
        "reference_events": reference_events,
        "historical_events": historical_events,
    }
    joblib.dump(bundle, artifact_dir / "earthquake_model.joblib", compress=3)

    holdout_bundle = dict(bundle)
    holdout_bundle["pipeline"] = holdout_pipeline
    holdout_bundle["metadata"] = dict(metadata)
    holdout_bundle["metadata"]["deployment_note"] = (
        "Trained on first 80% of chronological data for holdout reporting and audit."
    )
    joblib.dump(holdout_bundle, artifact_dir / "earthquake_model_holdout.joblib", compress=3)

    artifacts = {
        "model_file": "earthquake_model.joblib",
        "holdout_model_file": "earthquake_model_holdout.joblib",
        "metrics_file": "earthquake_metrics.json",
        "historical_events_file": "historical_events.csv",
    }
    metadata["artifacts"] = artifacts
    (artifact_dir / "earthquake_metrics.json").write_text(
        json.dumps(_json_ready(metadata), indent=2), encoding="utf-8"
    )

    print(f"\nSaved artifacts to {artifact_dir}")
    print(f"Total model fits: {metadata['training_runs']['total_fits']}")
    print(f"Training time: {metadata['training_seconds']:.1f}s")
    return metadata


def _xy(frame: pd.DataFrame, feature_set: str):
    X = select_columns(frame, feature_set)
    y = frame[TARGET].astype(int)
    return X, y


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the earthquake damage-risk model (RandomForest only)")
    parser.add_argument("--data", default=str(DEFAULT_DATA_PATH), help="Path to the earthquake CSV")
    parser.add_argument("--output-dir", default=str(DEFAULT_ARTIFACT_DIR), help="Artifact output directory")
    args = parser.parse_args()
    run_training(args.data, args.output_dir)


if __name__ == "__main__":
    main()
