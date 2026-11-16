"""Earthquake risk prediction endpoints backed by the trained ML model."""

from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.concurrency import run_in_threadpool

from models.disaster_models import EarthquakePredictRequest
from services.earthquake_service import city_risk_auto, list_cities, model_info, overview, predict_event, recent_events
from services.usgs_earthquake_service import fetch_usgs_events


router = APIRouter(prefix="/api/earthquake", tags=["Earthquake"])


@router.get("/model-info")
async def get_model_info():
    try:
        return model_info()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.post("/predict")
async def predict_earthquake_risk(request: EarthquakePredictRequest):
    try:
        return predict_event(request.model_dump())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/risk-by-city")
async def earthquake_risk_by_city(city: str, live: bool = False):
    if not city or not city.strip():
        raise HTTPException(status_code=400, detail="city is required")
    try:
        return await run_in_threadpool(city_risk_auto, city, live)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/events")
async def earthquake_events(city: Optional[str] = None, limit: int = 10):
    try:
        return recent_events(city, limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/cities")
async def earthquake_cities():
    try:
        return list_cities()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/overview")
async def earthquake_overview(limit: int = 60):
    try:
        return overview(limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/usgs-events")
async def usgs_events(
    starttime: str = None,
    endtime: str = None,
    minmagnitude: float = 2.5,
    maxmagnitude: float = None,
    latitude: float = None,
    longitude: float = None,
    maxradiuskm: float = None,
    limit: int = 50,
):
    try:
        return fetch_usgs_events(
            starttime=starttime,
            endtime=endtime,
            minmagnitude=minmagnitude,
            maxmagnitude=maxmagnitude,
            latitude=latitude,
            longitude=longitude,
            maxradiuskm=maxradiuskm,
            limit=limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
