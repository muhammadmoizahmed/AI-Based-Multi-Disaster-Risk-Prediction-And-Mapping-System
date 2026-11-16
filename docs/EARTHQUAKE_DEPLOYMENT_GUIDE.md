# Earthquake Deployment Guide

## Environment
- Python 3.11
- Install: `pip install -r backend/requirements.txt`
- Set environment variables (see `.env.example`): DB credentials, API keys, `ALLOWED_ORIGINS`.

## Artifacts
Ensure `backend/ml/artifacts/earthquake_model.joblib` and `earthquake_metrics.json` exist.

## Start
```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 5000
```

## Health
- `GET /health` -> `{"status":"ok"}`
- `GET /ready` -> model version and threshold

## Rollback
Keep previous `earthquake_model.joblib` and `earthquake_metrics.json` as `.bak`. Restore files and restart.

## Notes
- Do not commit secrets.
- Model is a prototype; not a validated early-warning system.