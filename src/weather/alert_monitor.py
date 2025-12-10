"""
Background task that monitors weather conditions and publishes alerts.
Runs periodically to check subscribed locations for critical weather.
"""
import asyncio
import json
from typing import Dict, Any, Set
from datetime import datetime

from src.db.redis import redis_client
from .services import get_weather_data
from .rules import apply_rules


class AlertMonitor:
    """
    Background service that monitors weather conditions for subscribed locations
    and publishes alerts via Redis pub/sub when critical conditions are detected.
    """
    
    def __init__(self, check_interval: int = 300):
        """
        Args:
            check_interval: Seconds between weather checks (default: 5 minutes)
        """
        self.check_interval = check_interval
        self.running = False
        self._task = None
        
    async def start(self):
        """Start the background monitoring task."""
        if self.running:
            return
            
        self.running = True
        self._task = asyncio.create_task(self._monitor_loop())
        print(f"🔔 Alert monitor started (checking every {self.check_interval}s)")
        
    async def stop(self):
        """Stop the background monitoring task."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        print("🔔 Alert monitor stopped")
        
    async def _monitor_loop(self):
        """Main monitoring loop that runs continuously."""
        while self.running:
            try:
                await self._check_all_subscriptions()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"❌ Alert monitor error: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying
                
    async def _check_all_subscriptions(self):
        """
        Check weather for all active subscriptions and send alerts if needed.
        """
        try:
            # Get all active subscriptions from Redis
            subscriptions = await self._get_active_subscriptions()
            
            if not subscriptions:
                return
                
            print(f"🔍 Checking weather for {len(subscriptions)} subscription(s)")
            
            # Check each subscription
            for sub_key, sub_data in subscriptions.items():
                try:
                    await self._check_subscription(sub_data)
                except Exception as e:
                    print(f"❌ Error checking subscription {sub_key}: {e}")
                    
        except Exception as e:
            print(f"❌ Error fetching subscriptions: {e}")
            
    async def _get_active_subscriptions(self) -> Dict[str, Dict[str, Any]]:
        """
        Retrieve all active weather alert subscriptions from Redis.
        
        Returns:
            Dict mapping subscription keys to subscription data
        """
        subscriptions = {}
        
        try:
            # Get all subscription keys
            keys = await redis_client.keys("weather:subscription:*")
            
            if not keys:
                return subscriptions
                
            # Fetch all subscription data
            for key in keys:
                data = await redis_client.get(key)
                if data:
                    try:
                        sub_data = json.loads(data)
                        subscriptions[key] = sub_data
                    except json.JSONDecodeError:
                        print(f"⚠️ Invalid JSON in subscription key: {key}")
                        
        except Exception as e:
            print(f"❌ Error reading subscriptions from Redis: {e}")
            
        return subscriptions
        
    async def _check_subscription(self, sub_data: Dict[str, Any]):
        """
        Check weather for a single subscription and publish alert if needed.
        
        Args:
            sub_data: Subscription data containing lat, lon, crop, user_id, etc.
        """
        lat = sub_data.get("lat")
        lon = sub_data.get("lon")
        crop = sub_data.get("crop", "generic")
        user_id = sub_data.get("user_id")
        
        if lat is None or lon is None:
            return
            
        # Fetch current weather data
        weather = await get_weather_data(lat, lon)
        
        # Apply risk rules
        risk = apply_rules(weather, crop)
        
        # Only send alerts for high or critical severity
        if risk["severity"] in ["high", "critical"]:
            await self._publish_alert(
                user_id=user_id,
                lat=lat,
                lon=lon,
                crop=crop,
                weather=weather,
                risk=risk
            )
            
    async def _publish_alert(
        self,
        user_id: str,
        lat: float,
        lon: float,
        crop: str,
        weather: Dict[str, Any],
        risk: Dict[str, Any]
    ):
        """
        Publish a weather alert to Redis pub/sub channel.
        
        Args:
            user_id: User ID to send alert to
            lat: Latitude
            lon: Longitude
            crop: Crop type
            weather: Weather data
            risk: Risk assessment
        """
        alert = {
            "type": "weather_alert",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "location": {"lat": lat, "lon": lon},
            "crop": crop,
            "weather": {
                "temperature": weather.get("temperature"),
                "humidity": weather.get("humidity"),
                "rainfall_mm": weather.get("rainfall_mm"),
                "wind_speed": weather.get("wind_speed")
            },
            "risk": risk
        }
        
        # Publish to Redis pub/sub
        channel = f"weather:alerts:{user_id}"
        
        try:
            await redis_client.publish(
                channel,
                json.dumps(alert)
            )
            print(f"🔔 Alert published for user {user_id}: {risk['severity']} - {risk['risk']}")
        except Exception as e:
            print(f"❌ Failed to publish alert: {e}")


# Global instance
alert_monitor = AlertMonitor(check_interval=300)  # Check every 5 minutes
