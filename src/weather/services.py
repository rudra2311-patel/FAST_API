import httpx
from datetime import datetime
from typing import Dict, Any

from .rules import apply_rules


# ---------------------------------------------------------
# Fetch raw weather data from Open-Meteo and simplify it
# ---------------------------------------------------------

async def get_weather_data(lat: float, lon: float) -> Dict[str, Any]:
    """
    Fetch real-time & forecast weather data from Open-Meteo
    and return a simplified dict suitable for the rule engine.
    """

    url = "https://api.open-meteo.com/v1/forecast"

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relativehumidity_2m,rain,precipitation,wind_speed_10m",
        "hourly": "temperature_2m,relativehumidity_2m,rain,precipitation_probability,wind_speed_10m",
        "forecast_days": 3,
        "timezone": "auto",
    }

    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()

    current = data.get("current", {})
    hourly = data.get("hourly", {})

    # ---------------------------------------------------------
    # Extract simple fields
    # ---------------------------------------------------------
    temp = current.get("temperature_2m", 0.0)
    humidity = current.get("relativehumidity_2m", 0.0)
    rainfall = current.get("rain", 0.0)
    wind_speed = current.get("wind_speed_10m", 0.0)

    # rain probability from hourly forecast (first value)
    rain_prob = 0.0
    if "precipitation_probability" in hourly and len(hourly["precipitation_probability"]) > 0:
        rain_prob = hourly["precipitation_probability"][0]

    # ---------------------------------------------------------
    # Determine consecutive rain days
    # ---------------------------------------------------------
    consecutive_rain_days = compute_consecutive_rain_days(hourly)

    simplified = {
        "temperature": temp,
        "humidity": humidity,
        "rainfall_mm": rainfall,
        "rain_probability": rain_prob,
        "wind_speed": wind_speed,
        "consecutive_rain_days": consecutive_rain_days,
        "hourly": hourly,  # keep for debugging or future features
    }

    return simplified


# ---------------------------------------------------------
# Helper: Compute consecutive rainy days from hourly data
# ---------------------------------------------------------

def compute_consecutive_rain_days(hourly: Dict[str, Any]) -> int:
    """
    Counts how many consecutive days have any rain (rain > 0).
    This is a simple heuristic but works reliably.
    """

    try:
        times = hourly.get("time", [])
        rain_arr = hourly.get("rain", [])

        day_has_rain = {}

        for t, rain in zip(times, rain_arr):
            day = t.split("T")[0]  # extract YYYY-MM-DD
            if rain is not None and rain > 0:
                day_has_rain[day] = True

        # consecutive day count = number of unique rain-days in forecast window
        return len(day_has_rain)

    except:
        return 0


# ---------------------------------------------------------
# Combined weather + risk computation (used in routes)
# ---------------------------------------------------------

async def get_weather_and_risk(lat: float, lon: float, crop: str = "generic") -> Dict[str, Any]:
    """
    Fetch simplified weather and apply rule engine to compute risk.
    Returns dict: { weather: {...}, risk: {...} }
    """

    weather = await get_weather_data(lat, lon)
    risk = apply_rules(weather, crop)

    return {
        "weather": weather,
        "risk": risk
    }
