"""
WebSocket routes for real-time weather alerts
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

from .websocket_manager import manager


ws_router = APIRouter()


@ws_router.websocket("/weather-alerts")
async def weather_alerts(
    websocket: WebSocket,
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    crop: str = Query(..., description="Crop type"),
    user_id: Optional[str] = Query(None, description="User ID")
):
    """
    WebSocket endpoint for real-time weather alerts.
    
    Connect with: ws://localhost:8000/ws/weather-alerts?lat=37.42&lon=-122.08&crop=Potato&user_id=user123
    
    Receives real-time alerts when critical weather conditions are detected.
    """
    
    # Connect the WebSocket and store subscription
    connection_id = await manager.connect(websocket, user_id, lat, lon, crop)
    
    if connection_id is None:
        # Connection failed (already closed by manager)
        return
    
    # Send connection confirmation
    await websocket.send_json({
        "type": "connection",
        "message": "Connected to weather alerts",
        "connection_id": connection_id,
        "subscription": {
            "lat": lat,
            "lon": lon,
            "crop": crop,
            "user_id": user_id
        }
    })
    
    try:
        # Keep connection alive and listen for messages
        while True:
            # Receive messages from client (for heartbeat/ping)
            try:
                data = await websocket.receive_text()
                # Echo back to confirm connection is alive
                await websocket.send_json({"type": "pong", "message": "Connection alive"})
            except WebSocketDisconnect:
                break
                
    except WebSocketDisconnect:
        pass
    finally:
        # Clean up connection
        await manager.disconnect(websocket)
