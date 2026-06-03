"""
Weather routes for fetching real-time and forecast data
"""
from fastapi import APIRouter, Request

from services.weather_service import (
    get_current_weather,
    get_weather_forecast,
    get_api_key,
    get_pakistan_cities_weather,
    search_city_weather,
    autocomplete_cities,
    get_my_location_weather
)


router = APIRouter(prefix="/api/weather", tags=["Weather"])


@router.get("/api-key")
async def get_weather_api_key():
    return get_api_key()


@router.get("/current")
async def current_weather(lat: float, lon: float):
    return get_current_weather(lat, lon)


@router.get("/forecast")
async def weather_forecast(lat: float, lon: float):
    return get_weather_forecast(lat, lon)


@router.get("/my-location")
async def my_location_weather(request: Request):
    """Get weather for user's detected location based on IP"""
    ip_address = request.client.host if request.client else None
    return get_my_location_weather(ip_address)


@router.get("/pakistan-cities")
async def pakistan_cities_weather():
    """Get weather data for major Pakistan cities"""
    return {"cities": get_pakistan_cities_weather()}


@router.get("/search")
async def search_weather(city: str):
    """Search weather and forecast for a Pakistan city"""
    return search_city_weather(city)


@router.get("/autocomplete")
async def autocomplete_city_search(query: str):
    """Autocomplete search for Pakistan cities"""
    return {"suggestions": autocomplete_cities(query)}
