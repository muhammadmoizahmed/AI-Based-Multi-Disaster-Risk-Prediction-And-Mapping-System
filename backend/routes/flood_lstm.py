"""Flood LSTM API routes."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from typing import List

from services.flood_lstm_service import (
    get_city_history,
    list_cities,
    model_info,
    overview,
    predict_by_city_auto,
    predict_sequence,
)

router = APIRouter(prefix="/api/flood-lstm", tags=["Flood LSTM"])


class SequenceRequest(BaseModel):
    sequence: List[List[float]] = Field(
        ...,
        description="14 chronological observations, each with 7 numeric features in the trained order.",
    )


@router.get("/model-info")
async def get_info():
    try:
        return model_info()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/cities")
async def get_cities():
    try:
        return list_cities()
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/history")
async def get_history(city: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=100)):
    try:
        return get_city_history(city, limit=limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/overview")
async def get_overview(limit: int = Query(50, ge=1, le=200)):
    try:
        return overview(limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/predict")
async def predict(req: SequenceRequest):
    try:
        return await run_in_threadpool(predict_sequence, req.sequence)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/predict-by-city")
async def predict_by_city_endpoint(city: str = Query(..., min_length=1), live: bool = Query(False)):
    try:
        return await run_in_threadpool(predict_by_city_auto, city, live)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
