"""
WebSocket Connection Manager for Real-Time Weather Alerts
Handles client connections, subscriptions, and broadcasting
"""

from fastapi import WebSocket
from typing import Dict, List, Set, Optional
import json
import asyncio
from datetime import datetime


class ConnectionManager:
    """
    Manages WebSocket connections and subscriptions.
    Clients can subscribe to specific locations and crops.
    """

    def __init__(self):
        # Active connections: {websocket: client_info}
        self.active_connections: Dict[WebSocket, dict] = {}
        
        # Subscriptions by location: {location_key: [websocket1, websocket2, ...]}
        self.location_subscriptions: Dict[str, Set[WebSocket]] = {}
        
        # Subscriptions by crop: {crop: [websocket1, websocket2, ...]}
        self.crop_subscriptions: Dict[str, Set[WebSocket]] = {}
        
        # Lock for thread-safe operations
        self._lock = asyncio.Lock()

    def _get_location_key(self, lat: float, lon: float, radius: float = 0.1) -> str:
        """
        Generate location key for grouping nearby locations.
        Radius determines how close locations need to be (in degrees).
        """
        # Round to create location buckets
        lat_rounded = round(lat / radius) * radius
        lon_rounded = round(lon / radius) * radius
        return f"{lat_rounded:.2f},{lon_rounded:.2f}"

    async def connect(
        self, 
        websocket: WebSocket, 
        user_id: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        crop: Optional[str] = None
    ) -> Optional[str]:
        """
        Accept WebSocket connection and store client info with subscription.
        Returns connection_id or None if connection failed.
        """
        try:
            await websocket.accept()
        except Exception as e:
            print(f"❌ Failed to accept WebSocket: {e}")
            return None
        
        connection_id = f"conn_{id(websocket)}"
        
        async with self._lock:
            self.active_connections[websocket] = {
                "connection_id": connection_id,
                "user_id": user_id,
                "connected_at": datetime.utcnow(),
                "locations": set(),
                "crops": set(),
                "lat": lat,
                "lon": lon,
                "crop": crop
            }
            
            # Auto-subscribe if location provided
            if lat is not None and lon is not None:
                location_key = self._get_location_key(lat, lon)
                self.active_connections[websocket]["locations"].add(location_key)
                if location_key not in self.location_subscriptions:
                    self.location_subscriptions[location_key] = set()
                self.location_subscriptions[location_key].add(websocket)
            
            # Auto-subscribe if crop provided
            if crop:
                crop_lower = crop.lower()
                self.active_connections[websocket]["crops"].add(crop_lower)
                if crop_lower not in self.crop_subscriptions:
                    self.crop_subscriptions[crop_lower] = set()
                self.crop_subscriptions[crop_lower].add(websocket)
        
        # Save subscription to Redis for background monitor
        if lat is not None and lon is not None and crop:
            from src.db.redis import redis_client
            subscription_data = {
                "connection_id": connection_id,
                "user_id": user_id,
                "lat": lat,
                "lon": lon,
                "crop": crop,
                "timestamp": datetime.utcnow().isoformat()
            }
            await redis_client.set(
                f"weather:subscription:{connection_id}",
                json.dumps(subscription_data),
                ex=86400  # Expire after 24 hours
            )
        
        print(f"✅ WebSocket connected: user={user_id}, location=({lat},{lon}), crop={crop}, total={len(self.active_connections)}")
        return connection_id

    async def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection and clean up subscriptions"""
        async with self._lock:
            if websocket in self.active_connections:
                client_info = self.active_connections[websocket]
                connection_id = client_info.get("connection_id")
                
                # Remove from location subscriptions
                for location in client_info["locations"]:
                    if location in self.location_subscriptions:
                        self.location_subscriptions[location].discard(websocket)
                        if not self.location_subscriptions[location]:
                            del self.location_subscriptions[location]
                
                # Remove from crop subscriptions
                for crop in client_info["crops"]:
                    if crop in self.crop_subscriptions:
                        self.crop_subscriptions[crop].discard(websocket)
                        if not self.crop_subscriptions[crop]:
                            del self.crop_subscriptions[crop]
                
                # Remove from Redis
                if connection_id:
                    from src.db.redis import redis_client
                    try:
                        await redis_client.delete(f"weather:subscription:{connection_id}")
                    except Exception as e:
                        print(f"⚠️ Failed to remove Redis subscription: {e}")
                
                del self.active_connections[websocket]
        
        print(f"❌ WebSocket disconnected: total={len(self.active_connections)}")

    async def subscribe_location(self, websocket: WebSocket, lat: float, lon: float):
        """Subscribe client to weather alerts for a specific location"""
        location_key = self._get_location_key(lat, lon)
        
        async with self._lock:
            if websocket in self.active_connections:
                # Add to client's location set
                self.active_connections[websocket]["locations"].add(location_key)
                
                # Add to location subscriptions
                if location_key not in self.location_subscriptions:
                    self.location_subscriptions[location_key] = set()
                self.location_subscriptions[location_key].add(websocket)
        
        print(f"📍 Subscribed to location: {location_key}")

    async def subscribe_crop(self, websocket: WebSocket, crop: str):
        """Subscribe client to weather alerts for a specific crop"""
        crop_lower = crop.lower()
        
        async with self._lock:
            if websocket in self.active_connections:
                # Add to client's crop set
                self.active_connections[websocket]["crops"].add(crop_lower)
                
                # Add to crop subscriptions
                if crop_lower not in self.crop_subscriptions:
                    self.crop_subscriptions[crop_lower] = set()
                self.crop_subscriptions[crop_lower].add(websocket)
        
        print(f"🌾 Subscribed to crop: {crop_lower}")

    async def unsubscribe_location(self, websocket: WebSocket, lat: float, lon: float):
        """Unsubscribe client from location alerts"""
        location_key = self._get_location_key(lat, lon)
        
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections[websocket]["locations"].discard(location_key)
                
                if location_key in self.location_subscriptions:
                    self.location_subscriptions[location_key].discard(websocket)
                    if not self.location_subscriptions[location_key]:
                        del self.location_subscriptions[location_key]

    async def unsubscribe_crop(self, websocket: WebSocket, crop: str):
        """Unsubscribe client from crop alerts"""
        crop_lower = crop.lower()
        
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections[websocket]["crops"].discard(crop_lower)
                
                if crop_lower in self.crop_subscriptions:
                    self.crop_subscriptions[crop_lower].discard(websocket)
                    if not self.crop_subscriptions[crop_lower]:
                        del self.crop_subscriptions[crop_lower]

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific client"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            print(f"❌ Error sending message: {e}")
            await self.disconnect(websocket)

    async def broadcast_to_location(self, lat: float, lon: float, message: dict):
        """Broadcast alert to all clients subscribed to a location"""
        location_key = self._get_location_key(lat, lon)
        
        async with self._lock:
            subscribers = self.location_subscriptions.get(location_key, set()).copy()
        
        if subscribers:
            print(f"📢 Broadcasting to {len(subscribers)} clients at {location_key}")
            
            # Send to all subscribers
            disconnected = []
            for websocket in subscribers:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    print(f"❌ Error broadcasting: {e}")
                    disconnected.append(websocket)
            
            # Clean up disconnected clients
            for ws in disconnected:
                await self.disconnect(ws)

    async def broadcast_to_crop(self, crop: str, message: dict):
        """Broadcast alert to all clients subscribed to a crop"""
        crop_lower = crop.lower()
        
        async with self._lock:
            subscribers = self.crop_subscriptions.get(crop_lower, set()).copy()
        
        if subscribers:
            print(f"📢 Broadcasting to {len(subscribers)} clients for crop: {crop}")
            
            disconnected = []
            for websocket in subscribers:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    print(f"❌ Error broadcasting: {e}")
                    disconnected.append(websocket)
            
            for ws in disconnected:
                await self.disconnect(ws)

    async def broadcast_to_all(self, message: dict):
        """Broadcast message to all connected clients"""
        async with self._lock:
            connections = list(self.active_connections.keys())
        
        print(f"📢 Broadcasting to all {len(connections)} clients")
        
        disconnected = []
        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"❌ Error broadcasting: {e}")
                disconnected.append(websocket)
        
        for ws in disconnected:
            await self.disconnect(ws)

    async def broadcast_to_matching_clients(self, alert_data: dict):
        """
        Broadcast alert to clients whose subscriptions match the alert.
        Called by Redis pub/sub when an alert is received.
        """
        lat = alert_data.get("lat")
        lon = alert_data.get("lon")
        crop = alert_data.get("crop", "").lower()
        
        if lat is None or lon is None:
            return
        
        location_key = self._get_location_key(lat, lon)
        
        # Find matching subscribers
        matching_clients = set()
        
        async with self._lock:
            # Match by location
            if location_key in self.location_subscriptions:
                matching_clients.update(self.location_subscriptions[location_key])
            
            # Match by crop
            if crop and crop in self.crop_subscriptions:
                matching_clients.update(self.crop_subscriptions[crop])
        
        if not matching_clients:
            return
        
        print(f"📤 Broadcasting alert to {len(matching_clients)} matching client(s)")
        
        # Send alert to matching clients
        message = alert_data.get("data", alert_data)
        disconnected = []
        
        for websocket in matching_clients:
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"❌ Error sending alert: {e}")
                disconnected.append(websocket)
        
        # Clean up disconnected clients
        for ws in disconnected:
            await self.disconnect(ws)

    async def disconnect_by_user_and_location(self, user_id: str, lat: float, lon: float, crop: str = None):
        """
        Disconnect WebSocket connections for a specific user at a specific farm location.
        Called when a farm is deleted.
        """
        location_key = self._get_location_key(lat, lon)
        disconnected_count = 0
        
        async with self._lock:
            # Find matching connections
            to_disconnect = []
            for websocket, client_info in self.active_connections.items():
                if (client_info.get("user_id") == user_id and 
                    client_info.get("lat") == lat and 
                    client_info.get("lon") == lon):
                    # If crop specified, match it too
                    if crop is None or client_info.get("crop") == crop:
                        to_disconnect.append(websocket)
        
        # Disconnect matching WebSockets
        for websocket in to_disconnect:
            try:
                await websocket.close(code=1000, reason="Farm deleted")
                await self.disconnect(websocket)
                disconnected_count += 1
            except Exception as e:
                print(f"⚠️ Error closing WebSocket: {e}")
        
        if disconnected_count > 0:
            print(f"🔌 Disconnected {disconnected_count} WebSocket(s) for deleted farm at ({lat}, {lon})")
        
        return disconnected_count

    def get_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "location_subscriptions": len(self.location_subscriptions),
            "crop_subscriptions": len(self.crop_subscriptions),
            "locations": list(self.location_subscriptions.keys()),
            "crops": list(self.crop_subscriptions.keys())
        }


# Global connection manager instance
manager = ConnectionManager()
