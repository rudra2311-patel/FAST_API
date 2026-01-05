"""
Pydantic schemas for WebSocket messages and weather alerts
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime


class SubscriptionRequest(BaseModel):
    """Client request to subscribe to location/crop alerts"""
    action: Literal["subscribe", "unsubscribe"]
    type: Literal["location", "crop"]
    lat: Optional[float] = None
    lon: Optional[float] = None
    crop: Optional[str] = None

    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "action": "subscribe",
                    "type": "location",
                    "lat": 37.4219983,
                    "lon": -122.084
                },
                {
                    "action": "subscribe",
                    "type": "crop",
                    "crop": "Potato"
                }
            ]
        }


class WeatherAlertMessage(BaseModel):
    """Weather alert message sent to clients via WebSocket"""
    type: Literal["weather_alert", "connection", "error", "info"]
    severity: Optional[str] = None
    risk: Optional[str] = None
    message: str
    advice: Optional[str] = None
    location: Optional[dict] = None
    crop: Optional[str] = None
    weather: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "type": "weather_alert",
                "severity": "high",
                "risk": "late_blight",
                "message": "High risk of Late Blight disease detected",
                "advice": "Apply fungicide immediately. Monitor plants daily.",
                "location": {"lat": 37.42, "lon": -122.08},
                "crop": "Potato",
                "weather": {
                    "temperature": 18.5,
                    "humidity": 87,
                    "rainfall_mm": 5.2
                },
                "timestamp": "2025-11-18T12:00:00Z"
            }
        }


class ConnectionMessage(BaseModel):
    """Connection status message"""
    type: Literal["connection"]
    status: Literal["connected", "disconnected"]
    message: str
    client_id: Optional[str] = None


class SubscriptionResponse(BaseModel):
    """Response to subscription request"""
    type: Literal["subscription"]
    status: Literal["success", "error"]
    action: str
    message: str
    subscriptions: Optional[dict] = None


class ErrorMessage(BaseModel):
    """Error message"""
    type: Literal["error"]
    message: str
    details: Optional[str] = None


class StatsMessage(BaseModel):
    """WebSocket connection statistics"""
    type: Literal["stats"]
    total_connections: int
    location_subscriptions: int
    crop_subscriptions: int
    locations: list
    crops: list
