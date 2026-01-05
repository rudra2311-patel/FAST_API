"""
Background task that monitors weather conditions and publishes alerts.
Runs periodically to check subscribed locations for critical weather.
"""
import asyncio
import json
import hashlib
from typing import Dict, Any, Set
from datetime import datetime, timedelta

from src.db.redis import redis_client
from src.db.main import get_session
from src.auth.models import User
from .models import NotificationLog
from .services import get_weather_data
from .rules import apply_rules
from sqlalchemy import select

# Import FCM service and notification manager
try:
    from src.fcm import FCMService
    from src.fcm.notification_manager import notification_manager
    FCM_AVAILABLE = True
except ImportError:
    FCM_AVAILABLE = False
    notification_manager = None
    print("⚠️ FCM not available - notifications will use Redis pub/sub only")


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
        Publish a weather alert to Redis pub/sub channel and send FCM notification.
        
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
        
        # Publish to Redis pub/sub (for WebSocket clients)
        channel = f"weather:alerts:{user_id}"
        
        try:
            await redis_client.publish(
                channel,
                json.dumps(alert)
            )
            print(f"🔔 Alert published for user {user_id}: {risk['severity']} - {risk['risk']}")
        except Exception as e:
            print(f"❌ Failed to publish alert: {e}")
            
        # 🔥 Send FCM push notification with smart deduplication
        if FCM_AVAILABLE and notification_manager:
            await self._send_fcm_notification(user_id, crop, weather, risk, farm_name="Your Farm")
    
    async def _send_fcm_notification(
        self,
        user_id: str,
        crop: str,
        weather: Dict[str, Any],
        risk: Dict[str, Any],
        farm_name: str = "Your Farm"
    ):
        """
        Send FCM push notification with smart deduplication and rate limiting.
        Follows industry best practices to avoid notification spam.
        
        Args:
            user_id: User ID
            crop: Crop type
            weather: Weather data
            risk: Risk assessment
            farm_name: Farm name for personalization
        """
        try:
            # Get user's FCM token from database
            async with get_session() as session:
                from sqlalchemy import select
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user or not user.fcm_token:
                    print(f"⚠️ No FCM token for user {user_id}")
                    return
                
                # Create content summary for deduplication
                content_summary = f"{crop}:{risk['severity']}:{risk['risk'][:50]}"
                
                # Check if notification should be sent (deduplication + rate limiting)
                check_result = await notification_manager.should_send_notification(
                    user_id=str(user_id),
                    notification_type="weather",
                    severity=risk["severity"],
                    content_summary=content_summary,
                    force=(risk["severity"] == "critical")
                )
                
                if not check_result["should_send"]:
                    print(f"⏭️ Skipping notification for user {user_id}: {check_result['reason']}")
                    if check_result.get("message"):
                        print(f"   Reason: {check_result['message']}")
                    return
                
                # Determine if should batch or send immediately
                should_batch = notification_manager.should_batch_notification(
                    severity=risk["severity"],
                    notification_type="weather"
                )
                
                if should_batch and risk["severity"] not in ["critical", "high"]:
                    # Add to batch queue
                    await notification_manager.add_to_batch(
                        user_id=str(user_id),
                        notification_data={
                            "type": "weather",
                            "severity": risk["severity"],
                            "crop": crop,
                            "farm_name": farm_name,
                            "risk": risk["risk"],
                            "weather": weather
                        }
                    )
                    print(f"📦 Notification batched for user {user_id} (will send in batch)")
                    return
                
                # Create personalized message
                message = notification_manager.create_personalized_message(
                    user_name=user.username or "Farmer",
                    farm_name=farm_name,
                    crop=crop,
                    severity=risk["severity"],
                    risk_type=risk["risk"],
                    weather_data=weather
                )
                
                # Send notification
                result = await FCMService.send_notification(
                    token=user.fcm_token,
                    title=message["title"],
                    body=message["body"],
                    data={
                        "type": "weather",
                        "severity": risk["severity"],
                        "crop": crop,
                        "farm_name": farm_name,
                        "risk": risk["risk"],
                        "temperature": str(weather.get("temperature", "")),
                        "humidity": str(weather.get("humidity", "")),
                        "rainfall": str(weather.get("rainfall_mm", "")),
                        "timestamp": datetime.utcnow().isoformat()
                    },
                    severity=risk["severity"]
                )
                
                if result.get("success"):
                    print(f"✅ FCM notification sent to user {user_id}: {message['title']}")
                    
                    # Save to notification_logs for alert screen
                    notification_hash = hashlib.sha256(
                        f"{user_id}:{content_summary}".encode()
                    ).hexdigest()
                    
                    # Check if notification already exists in last 24 hours (prevent duplicates in alert screen)
                    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
                    existing = await session.execute(
                        select(NotificationLog).where(
                            NotificationLog.user_id == user_id,
                            NotificationLog.notification_hash == notification_hash,
                            NotificationLog.created_at >= twenty_four_hours_ago
                        )
                    )
                    existing_notif = existing.scalar_one_or_none()
                    
                    if not existing_notif:
                        # Create new notification log entry
                        notification_log = NotificationLog(
                            user_id=user_id,
                            severity=risk["severity"],
                            message=f"{message['title']}\n{message['body']}",
                            sent=1,  # Mark as sent
                            is_read=False,
                            fcm_message_id=result.get("message_id"),
                            notification_hash=notification_hash,
                            created_at=datetime.utcnow()
                        )
                        session.add(notification_log)
                        await session.commit()
                        print(f"💾 Notification saved to database for alert screen")
                    else:
                        print(f"⏭️ Notification already exists in alert screen (last 24h)")
                    
                    # Mark as sent for deduplication/rate limiting
                    await notification_manager.mark_notification_sent(
                        user_id=str(user_id),
                        notification_type="weather",
                        severity=risk["severity"],
                        content_summary=content_summary
                    )
                else:
                    print(f"❌ FCM notification failed: {result.get('error')}")
                    
        except Exception as e:
            print(f"❌ Failed to send FCM notification: {e}")


# Global instance
alert_monitor = AlertMonitor(check_interval=300)  # Check every 5 minutes
