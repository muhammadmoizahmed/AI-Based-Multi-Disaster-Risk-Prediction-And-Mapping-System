import json
from pathlib import Path

import joblib
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sklearn.ensemble import RandomForestClassifier

from ml.earthquake_features import FEATURE_SETS, TARGET, select_columns
from services.earthquake_service import _load_bundle, _risk_level, model_info, predict_event

ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "ml" / "artifacts"


@pytest.fixture(scope="session")
def bundle():
    return _load_bundle()


@pytest.fixture(scope="session")
def metrics():
    return json.loads((ARTIFACT_DIR / "earthquake_metrics.json").read_text(encoding="utf-8"))


def test_saved_model_is_random_forest(bundle):
    pipeline = bundle["pipeline"]
    model = pipeline.named_steps["model"]
    assert isinstance(model, RandomForestClassifier)
    assert model.class_weight == "balanced_subsample"


def test_model_version(bundle, metrics):
    assert bundle["metadata"]["model_version"] == "3.0.0"
    assert metrics["model_version"] == "3.0.0"


def test_threshold_consistency(bundle, metrics):
    th = bundle["threshold"]
    assert th == bundle["thresholds"]["deployment_f2_safety"]
    assert th == bundle["metadata"]["threshold"]
    assert th == metrics["threshold"]
    assert th == metrics["thresholds"]["deployment_f2_safety"]
    assert th == metrics["thresholds"]["f1_optimal"]


def test_feature_columns_match_selected_set(bundle, metrics):
    fs = bundle["feature_set"]
    assert bundle["feature_columns"] == FEATURE_SETS[fs]
    assert metrics["feature_columns"] == FEATURE_SETS[fs]
    assert metrics["feature_set"] == fs


def test_risk_level_boundaries(bundle, metrics):
    b = bundle["risk_level_boundaries"]
    assert b == metrics["risk_level_boundaries"] == {"low": 0.25, "moderate": 0.5, "high": 0.75}
    assert _risk_level(0.10, b) == "low"
    assert _risk_level(0.25, b) == "moderate"
    assert _risk_level(0.49, b) == "moderate"
    assert _risk_level(0.50, b) == "high"
    assert _risk_level(0.74, b) == "high"
    assert _risk_level(0.75, b) == "extreme"


def test_predict_event_contract(bundle):
    result = predict_event(
        {
            "magnitude": 5.8,
            "depth_km": 12.9,
            "latitude": 30.0,
            "longitude": 67.0,
            "province": "Balochistan",
            "city": "Harnai",
            "date": "2025-03-03",
        }
    )
    assert result["success"] is True
    assert result["model"]["version"] == "3.0.0"
    assert result["model"]["threshold"] == bundle["threshold"]
    p = result["prediction"]
    assert 0.0 <= p["damage_probability"] <= 1.0
    assert p["threshold_used"] == bundle["threshold"]
    assert p["damage_predicted"] == (p["damage_probability"] >= bundle["threshold"])
    assert p["risk_level"] == _risk_level(p["damage_probability"], bundle["risk_level_boundaries"])


def test_unknown_city_province_handled(bundle):
    result = predict_event(
        {
            "magnitude": 4.0,
            "depth_km": 15.0,
            "latitude": 33.0,
            "longitude": 73.0,
            "province": "UnknownProvince",
            "city": "UnknownCity",
            "date": "2025-03-03",
        }
    )
    assert result["success"] is True
    assert 0.0 <= result["prediction"]["damage_probability"] <= 1.0


import asyncio


def test_api_predict_and_model_info():
    import httpx
    from fastapi import FastAPI
    from routes.earthquake import router

    app = FastAPI()
    app.include_router(router)

    async def run():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/earthquake/predict",
                json={
                    "magnitude": 5.8,
                    "depth_km": 12.9,
                    "latitude": 30.0,
                    "longitude": 67.0,
                    "province": "Balochistan",
                    "city": "Harnai",
                    "date": "2025-03-03",
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["model"]["version"] == "3.0.0"
            assert data["prediction"]["threshold_used"] == data["model"]["threshold"]

            bad = await client.post(
                "/api/earthquake/predict",
                json={
                    "magnitude": 50.0,
                    "depth_km": 12.9,
                    "latitude": 30.0,
                    "longitude": 67.0,
                },
            )
            assert bad.status_code == 422

            info = await client.get("/api/earthquake/model-info")
            assert info.status_code == 200
            info = info.json()
            bundle = _load_bundle()
            assert info["model"]["threshold"] == bundle["threshold"]
            assert info["model"]["version"] == "3.0.0"

    asyncio.run(run())


def test_holdout_confusion_matrix(metrics):
    cm = metrics["evaluation"]["holdout_deployment_threshold"]["confusion_matrix"]
    total = sum(sum(row) for row in cm)
    assert total == 129
    tp = cm[1][1]
    fn = cm[1][0]
    assert tp + fn == 6


def test_training_fit_count(metrics):
    tr = metrics["training_runs"]
    recomputed = (
        tr["feature_set_comparison_fits"]
        + tr["hyperparameter_fits"]
        + tr["oof_threshold_fits"]
        + tr["repeated_cv_fits"]
        + tr["temporal_cv_fits"]
        + tr["holdout_fits"]
    )
    assert recomputed == tr["total_fits"]


def test_model_info_fields(metrics):
    info = model_info()
    assert info["success"] is True
    assert info["model"]["name"] == "random_forest"
    m = info["metrics_summary"]["holdout"]
    assert m["accuracy"] == metrics["evaluation"]["holdout_deployment_threshold"]["accuracy"]
    assert m["f1"] == metrics["evaluation"]["holdout_deployment_threshold"]["f1"]
    assert info["training_runs"]["total_fits"] == metrics["training_runs"]["total_fits"]


def test_health_and_ready():
    import asyncio
    import httpx
    from fastapi import FastAPI

    # Rebuild a minimal app with the health/ready endpoints by importing main's functions
    from main import health, ready

    assert health()["status"] == "ok"
    r = ready()
    assert r["status"] == "ready"
    assert r["earthquake_model"] == "3.0.0"


def test_live_city_risk_uses_live_usgs(monkeypatch):
    import services.earthquake_service as svc

    fake_events = [
        {
            "magnitude": 5.2,
            "latitude": 24.9,
            "longitude": 67.0,
            "depth_km": 15.0,
            "time": 1700000000000,
            "place": "Karachi",
        }
    ]
    monkeypatch.setattr(svc, "_load_live_usgs_events", lambda *args, **kwargs: fake_events)
    svc.clear_live_city_cache()
    result = svc.city_risk_live("Karachi")
    assert result["data_source"] == "live_usgs"
    assert result["live_source"]["available"] is True
    assert 0.0 <= result["prediction"]["damage_probability"] <= 1.0


def test_live_city_risk_falls_back_without_usgs(monkeypatch):
    import services.earthquake_service as svc

    monkeypatch.setattr(svc, "_load_live_usgs_events", lambda *args, **kwargs: [])
    svc.clear_live_city_cache()
    result = svc.city_risk_live("Karachi")
    assert result["data_source"] == "historical_dataset_fallback"
    assert result["live_source"]["available"] is False


def test_live_city_risk_ignores_old_or_distant_event(monkeypatch):
    import services.earthquake_service as svc
    from datetime import datetime, timezone

    old_event = {
        "magnitude": 4.8,
        "latitude": 25.4,
        "longitude": 66.7,
        "depth_km": 10.0,
        "time": int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp() * 1000),
        "place": "Old distant event",
    }
    monkeypatch.setattr(svc, "_load_live_usgs_events", lambda *args, **kwargs: [old_event])
    svc.clear_live_city_cache()
    result = svc.city_risk_live("Karachi")

    assert result["data_source"] == "live_usgs"
    assert result["location"]["events_in_scope"] == 0
    assert result["prediction"]["risk_level"] == "low"
    assert result["live_source"]["nearest_event"]["distance_km"] > 0
    assert "no USGS events" in result["location"]["basis"]


def test_live_city_risk_uses_recent_local_event(monkeypatch):
    import services.earthquake_service as svc
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    recent_event = {
        "magnitude": 5.6,
        "latitude": 24.9,
        "longitude": 67.0,
        "depth_km": 10.0,
        "time": int((now - timedelta(days=2)).timestamp() * 1000),
        "place": "Near Karachi",
    }
    monkeypatch.setattr(svc, "_load_live_usgs_events", lambda *args, **kwargs: [recent_event])
    svc.clear_live_city_cache()
    result = svc.city_risk_live("Karachi")

    assert result["data_source"] == "live_usgs"
    assert result["location"]["events_in_scope"] == 1
    assert result["location"]["scenario"]["magnitude"] == 5.6
    assert result["prediction"]["damage_probability"] >= 0.5
