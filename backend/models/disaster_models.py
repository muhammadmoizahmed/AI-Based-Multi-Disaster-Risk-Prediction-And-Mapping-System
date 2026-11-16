"""Request models for disaster risk prediction endpoints."""

from typing import Optional

from pydantic import BaseModel, Field


class EarthquakePredictRequest(BaseModel):
    magnitude: float = Field(..., ge=0.0, le=10.0, description="Richter/local magnitude")
    depth_km: float = Field(..., ge=0.0, le=700.0, description="Hypocentre depth in kilometres")
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    province: str = Field(default="Unknown")
    city: str = Field(default="Unknown")
    date: Optional[str] = Field(default=None, description="Event date (YYYY-MM-DD); defaults to today")

