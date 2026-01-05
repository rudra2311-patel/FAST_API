from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from src.db.main import get_session  # your existing DB session function
from src.auth.dependencies import AccessTokenBearer  # ADDED: JWT auth
from .services import get_weather_data, get_weather_and_risk
from .schemas import WeatherData, WeatherRiskResponse
from .models import WeatherLog, NotificationLog


router = APIRouter()

@router.get("/current", response_model=WeatherData)
async def current_weather(lat: float, lon: float):
    """
    Returns simplified weather data ONLY.
    """
    try:
        data = await get_weather_data(lat, lon)

        return {
            "temperature": data["temperature"],
            "humidity": data["humidity"],
            "rainfall_mm": data["rainfall_mm"],
            "rain_probability": data["rain_probability"],
            "wind_speed": data["wind_speed"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast")
async def forecast_weather(lat: float, lon: float):
    """
    Returns full weather data including hourly forecast for 3 days.
    Used by frontend to generate 3-day forecast cards.
    """
    try:
        data = await get_weather_data(lat, lon)
        return data  # Includes hourly data

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/risk", response_model=WeatherRiskResponse)
async def weather_risk(
    lat: float,
    lon: float,
    crop: str = "generic",
    session: Session = Depends(get_session),
    token_data: dict = Depends(AccessTokenBearer())  # ADDED: Require auth
):
    """
    Returns weather + disease/condition risk AND saves log to DB.
    Now requires authentication to ensure logs are tied to correct user.
    """
    try:
        # Extract user_id from JWT token
        user_id = token_data["user"]["user_id"]
        
        result = await get_weather_and_risk(lat, lon, crop)
        weather = result["weather"]
        risk = result["risk"]

        # Save WeatherLog into DB with authenticated user_id
        log = WeatherLog(
            user_id=user_id,  # FIXED: Use JWT user_id
            lat=lat,
            lon=lon,
            weather=weather,
            risk=risk["risk"],
            severity=risk["severity"],
            message=risk["message"],
            advice=risk["advice"]
        )
        session.add(log)
        await session.commit()
        await session.refresh(log)

        # High severity → create notification entry
        if risk["severity"] in ["high", "critical"]:
            notif = NotificationLog(
                user_id=user_id,  # FIXED: Use JWT user_id
                weather_log_id=log.id,
                severity=risk["severity"],
                message=risk["message"]
            )
            session.add(notif)
            await session.commit()

        return {"weather": weather, "risk": risk}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@router.post("/test", response_model=WeatherRiskResponse)
async def test_weather_risk(payload: dict, session: Session = Depends(get_session)):
    """
    Test weather risk with manual/dummy weather JSON.
    Does NOT call Open-Meteo.
    Does NOT save to DB unless told.
    """
    try:
        weather = payload.get("weather")
        crop = payload.get("crop", "generic")
        user_id = payload.get("user_id", None)

        if not weather:
            raise HTTPException(status_code=400, detail="weather object missing")

        # apply rule engine
        from .rules import apply_rules
        risk = apply_rules(weather, crop)

        # optional: save logs for testing
        if payload.get("save", False):
            log = WeatherLog(
                user_id=user_id,
                lat=0.0,
                lon=0.0,
                weather=weather,
                risk=risk["risk"],
                severity=risk["severity"],
                message=risk["message"],
                advice=risk["advice"]
            )
            session.add(log)
            await session.commit()
            await session.refresh(log)

        return {"weather": weather, "risk": risk}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
