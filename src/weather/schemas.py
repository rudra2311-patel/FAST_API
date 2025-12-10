from typing import Dict, Any
from pydantic import BaseModel


class WeatherData(BaseModel):
    temperature: float
    humidity: float
    rainfall_mm: float
    rain_probability: float
    wind_speed: float


class RiskData(BaseModel):
    risk: str
    severity: str
    message: str
    advice: str


class WeatherRiskResponse(BaseModel):
    weather: Dict[str, Any]
    risk: Dict[str, Any]
