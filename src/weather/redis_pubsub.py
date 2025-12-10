"""
Redis Pub/Sub service for broadcasting weather alerts across multiple server instances.
Enables horizontal scaling while maintaining real-time alert delivery.
"""

import json
import asyncio
from typing import Callable, Optional
import redis.asyncio as aioredis
from src.config import Config


class RedisPubSub:
    """
    Redis publisher/subscriber for distributed weather alerts.
    Allows multiple FastAPI instances to share real-time alerts.
    """

    def __init__(self):
        self.redis_client: Optional[aioredis.Redis] = None
        self.pubsub: Optional[aioredis.client.PubSub] = None
        self.listener_task: Optional[asyncio.Task] = None
        
        # Channel names
        self.WEATHER_ALERTS_CHANNEL = "weather:alerts"
        self.WEATHER_LOCATION_PREFIX = "weather:location:"
        self.WEATHER_CROP_PREFIX = "weather:crop:"

    async def connect(self):
        """Initialize Redis connection and pub/sub"""
        if not self.redis_client:
            self.redis_client = aioredis.StrictRedis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=1,  # Use different DB than token blocklist
                decode_responses=True
            )
            self.pubsub = self.redis_client.pubsub()
            print("✅ Redis Pub/Sub connected")

    async def disconnect(self):
        """Close Redis connections"""
        if self.listener_task:
            self.listener_task.cancel()
            try:
                await self.listener_task
            except asyncio.CancelledError:
                pass

        if self.pubsub:
            await self.pubsub.close()
        
        if self.redis_client:
            await self.redis_client.close()
        
        print("❌ Redis Pub/Sub disconnected")

    async def start(self):
        """
        Start the Redis pub/sub listener.
        Called on application startup to begin receiving alerts.
        """
        from .websocket_manager import manager
        
        await self.connect()
        
        # Subscribe to alerts and set callback to broadcast to WebSocket clients
        async def broadcast_callback(alert_data: dict):
            """Callback when alert received from Redis"""
            await manager.broadcast_to_matching_clients(alert_data)
        
        await self.subscribe_to_alerts(broadcast_callback)
        print("🔔 Redis pub/sub listener started")

    async def stop(self):
        """
        Stop the Redis pub/sub listener.
        Called on application shutdown.
        """
        await self.disconnect()

    async def publish_alert(
        self, 
        lat: float, 
        lon: float, 
        crop: str, 
        alert_data: dict
    ):
        """
        Publish weather alert to Redis channels.
        Other server instances will receive and broadcast to their connected clients.
        """
        if not self.redis_client:
            await self.connect()

        # Create alert message
        message = {
            "type": "weather_alert",
            "lat": lat,
            "lon": lon,
            "crop": crop,
            "data": alert_data,
            "timestamp": alert_data.get("timestamp")
        }

        message_json = json.dumps(message)

        # Publish to multiple channels for flexibility
        await self.redis_client.publish(self.WEATHER_ALERTS_CHANNEL, message_json)
        await self.redis_client.publish(
            f"{self.WEATHER_LOCATION_PREFIX}{lat:.2f},{lon:.2f}", 
            message_json
        )
        await self.redis_client.publish(
            f"{self.WEATHER_CROP_PREFIX}{crop.lower()}", 
            message_json
        )

        print(f"📤 Published alert to Redis: {crop} at ({lat}, {lon})")

    async def subscribe_to_alerts(self, callback: Callable):
        """
        Subscribe to weather alerts channel and call callback when message received.
        Callback should be: async def callback(message_data: dict)
        """
        if not self.redis_client:
            await self.connect()

        # Subscribe to the main alerts channel
        await self.pubsub.subscribe(self.WEATHER_ALERTS_CHANNEL)
        print(f"📥 Subscribed to Redis channel: {self.WEATHER_ALERTS_CHANNEL}")

        # Start listening in background
        self.listener_task = asyncio.create_task(
            self._listen_for_messages(callback)
        )

    async def _listen_for_messages(self, callback: Callable):
        """Background task that listens for Redis pub/sub messages"""
        try:
            async for message in self.pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await callback(data)
                    except json.JSONDecodeError as e:
                        print(f"❌ Error decoding Redis message: {e}")
                    except Exception as e:
                        print(f"❌ Error processing Redis message: {e}")
        except asyncio.CancelledError:
            print("🛑 Redis listener stopped")
            raise
        except Exception as e:
            print(f"❌ Redis listener error: {e}")

    async def get_active_channels(self) -> list:
        """Get list of active pub/sub channels (for monitoring)"""
        if not self.redis_client:
            await self.connect()
        
        channels = await self.redis_client.pubsub_channels()
        return channels


# Global Redis pub/sub instance
redis_pubsub = RedisPubSub()
