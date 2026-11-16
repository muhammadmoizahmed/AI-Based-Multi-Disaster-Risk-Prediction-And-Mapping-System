import json
from pathlib import Path

import numpy as np
import pytest
import asyncio
from httpx import ASGITransport, AsyncClient

from services.flood_lstm_service import (
    _load_bundle,
    _load_history,
    _risk_level,
    list_cities,
    model_info,
    predict_by_city,
    predict_sequence,
)
from main import app

ARTIFACT_DIR = Path(__file__).resolve().parents[1] / "ml" / "artifacts" / "flood_lstm"
SUPPORTED_CITIES = ["Karachi", "Lahore", "Peshawar"]


@pytest.fixture(scope="session")
def bundle():
    return _load_bundle()


def test_artifacts_exist():
    for name in [
        "flood_lstm.keras",
        "scaler.joblib",
        "feature_schema.json",
        "model_metadata.json",
        "evaluation_metrics.json",
        "training_history.json",
    ]:
        assert (ARTIFACT_DIR / name).exists(), name


def test_bundle_metadata(bundle):
    meta = bundle["metadata"]
    assert meta["model_name"] == "flood_lstm"
    assert meta["lookback"] == 14
    assert meta["framework"] == "tensorflow"
    assert len(bundle["features"]) == 7


def test_feature_schema(bundle):
    schema = json.loads((ARTIFACT_DIR / "feature_schema.json").read_text())
    assert schema == bundle["features"]
    assert schema == [
        "rainfall_mm",
        "river_level_m",
        "latitude",
        "longitude",
        "days_since_previous",
        "month_sin",
        "month_cos",
    ]


def test_model_input_shape(bundle):
    assert bundle["model"].input_shape == (None, 14, 7)


def test_scaler_transform(bundle):
    x = np.zeros((14, 7), dtype=float)
    y = bundle["scaler"].transform(x)
    assert y.shape == (14, 7)


def test_risk_levels():
    assert _risk_level(0.0) == "low"
    assert _risk_level(0.24) == "low"
    assert _risk_level(0.25) == "moderate"
    assert _risk_level(0.49) == "moderate"
    assert _risk_level(0.5) == "high"
    assert _risk_level(0.74) == "high"
    assert _risk_level(0.75) == "extreme"


def test_invalid_sequence_shape():
    with pytest.raises(ValueError):
        predict_sequence([[1.0] * 7] * 13)
    with pytest.raises(ValueError):
        predict_sequence([[1.0] * 6] * 14)
    with pytest.raises(ValueError):
        predict_sequence([[1.0] * 7] * 14 + [[np.nan] * 7])


def test_valid_sequence_prediction():
    seq = [[0.0, 1.0, 24.8, 67.0, 1.0, 0.5, 0.5] for _ in range(14)]
    result = predict_sequence(seq)
    assert result["success"] is True
    assert 0.0 <= result["prediction"]["flood_probability"] <= 1.0
    assert result["prediction"]["risk_level"] in {"low", "moderate", "high", "extreme"}


def test_city_prediction():
    for city in SUPPORTED_CITIES:
        result = predict_by_city(city)
        assert result["success"] is True
        assert result["city"] == city
        assert result["location"]["city"] == city
        assert len(result["observation"]) == 6
        assert 0.0 <= result["prediction"]["flood_probability"] <= 1.0


def test_insufficient_history():
    # Any city with fewer than 14 records should raise; use a tiny city if present.
    history = _load_history()
    counts = history.groupby("city").size()
    small = [city for city, count in counts.items() if count < 14]
    if small:
        with pytest.raises(ValueError):
            predict_by_city(small[0])


def test_model_info():
    info = model_info()
    assert info["success"] is True
    assert info["model"]["type"] == "LSTM"
    assert info["model"]["lookback"] == 14
    assert info["model"]["feature_count"] == 7
    assert info["metrics"]["accuracy"] > 0


def test_list_cities():
    data = list_cities()
    assert data["success"] is True
    assert len(data["cities"]) > 0
    assert all(item["required_records"] == 14 for item in data["cities"])


async def _request(method, path, **kwargs):
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        return await client.request(method, path, **kwargs)


def test_api_model_info():
    response = asyncio.run(_request("GET", "/api/flood-lstm/model-info"))
    assert response.status_code == 200
    assert response.json()["model"]["version"] == "1.0.0"


def test_api_predict():
    payload = {"sequence": [[0.0, 1.0, 24.8, 67.0, 1.0, 0.5, 0.5] for _ in range(14)]}
    response = asyncio.run(_request("POST", "/api/flood-lstm/predict", json=payload))
    assert response.status_code == 200
    assert "prediction" in response.json()


def test_api_invalid_predict():
    payload = {"sequence": [[1.0]]}
    response = asyncio.run(_request("POST", "/api/flood-lstm/predict", json=payload))
    assert response.status_code in {400, 422}


def test_api_predict_by_city():
    response = asyncio.run(_request("GET", "/api/flood-lstm/predict-by-city", params={"city": "Karachi"}))
    assert response.status_code == 200
    assert response.json()["city"] == "Karachi"


def test_api_cities():
    response = asyncio.run(_request("GET", "/api/flood-lstm/cities"))
    assert response.status_code == 200
    assert response.json()["lookback"] == 14


def test_api_ready_includes_flood():
    response = asyncio.run(_request("GET", "/ready"))
    assert response.status_code == 200
    assert "flood_lstm_model" in response.json()

def test_live_prediction_uses_live_weather(monkeypatch):
    import services.flood_lstm_service as svc

    monkeypatch.setattr(
        svc,
        "_live_weather_for",
        lambda lat, lon: {"available": True, "rainfall_mm": 75.0, "source": "test"},
    )
    result = svc.predict_by_city_live("Karachi")
    assert result["data_source"] == "live_weather"
    assert result["observation"]["rainfall_mm"] == 75.0
    assert 0.0 <= result["prediction"]["flood_probability"] <= 1.0


def test_live_prediction_falls_back_when_weather_unavailable(monkeypatch):
    import services.flood_lstm_service as svc

    monkeypatch.setattr(
        svc,
        "_live_weather_for",
        lambda lat, lon: {"available": False, "reason": "offline"},
    )
    result = svc.predict_by_city_live("Karachi")
    assert result["data_source"] == "historical_dataset_fallback"
    assert result["live_weather"]["available"] is False


def test_auto_dispatch_selects_live(monkeypatch):
    import services.flood_lstm_service as svc

    monkeypatch.setattr(
        svc,
        "_live_weather_for",
        lambda lat, lon: {"available": True, "rainfall_mm": 10.0, "source": "test"},
    )
    assert svc.predict_by_city_auto("Karachi", live=True)["data_source"] == "live_weather"
    assert svc.predict_by_city_auto("Karachi", live=False)["data_source"] == "historical_dataset"
