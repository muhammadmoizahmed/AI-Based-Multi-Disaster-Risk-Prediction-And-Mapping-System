"""
Weather service for fetching real-time and forecast data from OpenWeatherMap
"""
import os
import requests
import time
from dotenv import load_dotenv
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from utils.helpers import PAKISTAN_CITIES, find_pakistan_city, search_pakistan_cities

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

OPENWEATHERMAP_API_KEY = os.getenv('openweathermap_api_key', '')

# Caching mechanism (in-memory)
_cache = {}
CACHE_TTL = 300  # 5 minutes

def _get_cache_key(key: str) -> str:
    """Generate cache key"""
    return f"weather:{key}"

def _get_from_cache(key: str) -> Optional[Any]:
    """Get value from cache"""
    cache_key = _get_cache_key(key)
    if cache_key in _cache:
        cached_data, timestamp = _cache[cache_key]
        if time.time() - timestamp < CACHE_TTL:
            return cached_data
        del _cache[cache_key]
    return None

def _set_to_cache(key: str, data: Any):
    """Store value in cache"""
    _cache[_get_cache_key(key)] = (data, time.time())

def get_location_from_ip(ip_address: Optional[str] = None) -> Dict[str, Any]:
    """
    Get location (city, country, coordinates) from IP address using ipapi.co
    """
    try:
        url = "https://ipapi.co/json/"
        if ip_address and ip_address not in ["127.0.0.1", "localhost", "::1"]:
            url = f"https://ipapi.co/{ip_address}/json/"
        
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return {
                "city": data.get("city", "Unknown"),
                "country": data.get("country_name", "Unknown"),
                "country_code": data.get("country_code", ""),
                "lat": data.get("latitude", 0.0),
                "lon": data.get("longitude", 0.0),
                "ip": data.get("ip", ip_address or "Unknown")
            }
        return {"error": "Failed to get location"}
    except Exception as e:
        return {"error": str(e)}


def get_current_weather(lat: float, lon: float):
    """Fetch current weather data for given coordinates with caching"""
    if not OPENWEATHERMAP_API_KEY:
        return {"error": "API key not configured"}
    
    cache_key = f"current:{lat}:{lon}"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached
    
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
        response = requests.get(url, timeout=10)
        data = response.json()
        _set_to_cache(cache_key, data)
        return data
    except Exception as e:
        return {"error": str(e)}


def get_weather_forecast(lat: float, lon: float):
    """Fetch weather forecast data for given coordinates with caching"""
    if not OPENWEATHERMAP_API_KEY:
        return {"error": "API key not configured"}
    
    cache_key = f"forecast:{lat}:{lon}"
    cached = _get_from_cache(cache_key)
    if cached:
        return cached
    
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={OPENWEATHERMAP_API_KEY}&units=metric"
        response = requests.get(url, timeout=10)
        data = response.json()
        _set_to_cache(cache_key, data)
        return data
    except Exception as e:
        return {"error": str(e)}


def get_pakistan_cities_weather():
    """Fetch live weather data for major Pakistan cities"""
    results = []
    for city in PAKISTAN_CITIES:
        weather_data = get_current_weather(city["lat"], city["lng"])
        if "error" not in weather_data and "main" in weather_data:
            results.append({
                "name": weather_data.get("name", city["name"]),
                "province": city["province"],
                "lat": city["lat"],
                "lon": city["lng"],
                "temperature": weather_data["main"].get("temp", 0),
                "condition": weather_data["weather"][0].get("main", "Unknown") if weather_data.get("weather") else "Unknown",
                "humidity": weather_data["main"].get("humidity", 0),
                "wind_speed": round(weather_data["wind"].get("speed", 0) * 3.6, 1)  # m/s to km/h
            })
        if len(results) >= 30:  # Limit to top 30 cities to avoid too many API calls
            break
    return results


def search_city_weather(city_name: str):
    """Search weather and forecast for a Pakistan city"""
    city = find_pakistan_city(city_name)
    if not city:
        return {"error": "City not found in Pakistan"}
    
    current_weather = get_current_weather(city["lat"], city["lng"])
    forecast = get_weather_forecast(city["lat"], city["lng"])
    
    return {
        "city": city,
        "current": current_weather,
        "forecast": forecast
    }


def autocomplete_cities(query: str):
    """Autocomplete cities search"""
    return search_pakistan_cities(query, limit=15)


def get_my_location_weather(ip_address: Optional[str] = None):
    """Get weather for user's detected location"""
    location = get_location_from_ip(ip_address)
    if "error" in location:
        # Fallback to Karachi if location detection fails
        location = {
            "city": "Karachi",
            "country": "Pakistan",
            "lat": 24.8607,
            "lon": 67.0011
        }
    
    current = get_current_weather(location["lat"], location["lon"])
    forecast = get_weather_forecast(location["lat"], location["lon"])
    
    return {
        "location": location,
        "current": current,
        "forecast": forecast
    }


def get_api_key() -> dict:
    """Get OpenWeatherMap API key (for legacy purposes)"""
    return {"api_key": OPENWEATHERMAP_API_KEY}
