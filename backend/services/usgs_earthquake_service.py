"""Live USGS earthquake event service."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import requests

USGS_QUERY_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_LAST_GOOD: dict[str, tuple[float, dict[str, Any]]] = {}
CACHE_TTL_SECONDS = 300
REGION_CACHE_TTL_SECONDS = 300

# Box covering Pakistan and the surrounding seismic belts (Hindu Kush, Pamir,
# Makran, Sulaiman range, Himalaya foothills). One query serves every city.
PAKISTAN_BOUNDS = {
    "minlatitude": 23.0,
    "maxlatitude": 38.5,
    "minlongitude": 59.0,
    "maxlongitude": 78.5,
}
_BOUND_KEYS = ("minlatitude", "maxlatitude", "minlongitude", "maxlongitude")


def _round_endtime(endtime: str, bucket_seconds: int = CACHE_TTL_SECONDS) -> str:
    """Snap the end time to the cache window so repeated calls share a key."""
    try:
        parsed = datetime.fromisoformat(endtime.replace("Z", "+00:00"))
    except ValueError:
        return endtime
    bucket = int(parsed.timestamp()) // bucket_seconds * bucket_seconds
    return datetime.fromtimestamp(bucket, tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _cache_key(params: dict[str, Any]) -> str:
    return "&".join(f"{key}={params[key]}" for key in sorted(params))


def _family_key(params: dict[str, Any]) -> str:
    """Key that ignores the time window, used to serve stale data on failure."""
    keys = ("minmagnitude", "maxmagnitude", "latitude", "longitude", "maxradiuskm", "limit") + _BOUND_KEYS
    return "&".join(f"{key}={params[key]}" for key in sorted(keys) if key in params)


def fetch_usgs_events(
    starttime: Optional[str] = None,
    endtime: Optional[str] = None,
    minmagnitude: float = 2.5,
    maxmagnitude: Optional[float] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    maxradiuskm: Optional[float] = None,
    minlatitude: Optional[float] = None,
    maxlatitude: Optional[float] = None,
    minlongitude: Optional[float] = None,
    maxlongitude: Optional[float] = None,
    limit: int = 50,
    cache_ttl: int = CACHE_TTL_SECONDS,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    if not starttime:
        starttime = (now - timedelta(days=7)).date().isoformat()
    if not endtime:
        endtime = now.isoformat(timespec="seconds").replace("+00:00", "Z")

    params: dict[str, Any] = {
        "format": "geojson",
        "starttime": starttime,
        "endtime": _round_endtime(endtime, cache_ttl),
        "minmagnitude": minmagnitude,
        "limit": min(max(1, limit), 20000),
        "orderby": "time",
    }
    if maxmagnitude is not None:
        params["maxmagnitude"] = maxmagnitude
    if latitude is not None and longitude is not None and maxradiuskm is not None:
        params["latitude"] = round(float(latitude), 2)
        params["longitude"] = round(float(longitude), 2)
        params["maxradiuskm"] = maxradiuskm
    if all(v is not None for v in (minlatitude, maxlatitude, minlongitude, maxlongitude)):
        params["minlatitude"] = minlatitude
        params["maxlatitude"] = maxlatitude
        params["minlongitude"] = minlongitude
        params["maxlongitude"] = maxlongitude

    key = _cache_key(params)
    family = _family_key(params)
    cached = _CACHE.get(key)
    if cached and time.time() - cached[0] < cache_ttl:
        return cached[1]

    last_error: Optional[Exception] = None
    for attempt in range(2):
        try:
            response = requests.get(USGS_QUERY_URL, params=params, timeout=12)
            response.raise_for_status()
            raw = response.json()
            break
        except Exception as exc:  # network error or USGS rate limit
            last_error = exc
            time.sleep(1.5 * (attempt + 1))
    else:
        stale = _LAST_GOOD.get(family)
        if stale:
            result = dict(stale[1])
            result["stale"] = True
            result["stale_age_seconds"] = int(time.time() - stale[0])
            return result
        raise last_error  # type: ignore[misc]

    events = []
    for feature in raw.get("features", []):
        properties = feature.get("properties", {})
        coordinates = (feature.get("geometry") or {}).get("coordinates") or [None, None, None]
        events.append(
            {
                "id": feature.get("id"),
                "magnitude": properties.get("mag"),
                "place": properties.get("place"),
                "time": properties.get("time"),
                "updated": properties.get("updated"),
                "status": properties.get("status"),
                "tsunami": properties.get("tsunami"),
                "sig": properties.get("sig"),
                "type": properties.get("type"),
                "latitude": coordinates[1],
                "longitude": coordinates[0],
                "depth_km": coordinates[2],
                "url": properties.get("url"),
            }
        )

    result = {
        "success": True,
        "source": "USGS FDSN Event Web Service",
        "count": len(events),
        "metadata": raw.get("metadata", {}),
        "events": events,
    }
    _CACHE[key] = (time.time(), result)
    _LAST_GOOD[family] = (time.time(), result)
    return result


def fetch_pakistan_events(days: int = 365, minmagnitude: float = 2.5) -> dict[str, Any]:
    """Fetch every regional event once; all cities then filter this cache locally."""
    now = datetime.now(timezone.utc)
    return fetch_usgs_events(
        starttime=(now - timedelta(days=days)).date().isoformat(),
        endtime=now.isoformat(timespec="seconds").replace("+00:00", "Z"),
        minmagnitude=minmagnitude,
        minlatitude=PAKISTAN_BOUNDS["minlatitude"],
        maxlatitude=PAKISTAN_BOUNDS["maxlatitude"],
        minlongitude=PAKISTAN_BOUNDS["minlongitude"],
        maxlongitude=PAKISTAN_BOUNDS["maxlongitude"],
        limit=20000,
        cache_ttl=REGION_CACHE_TTL_SECONDS,
    )
