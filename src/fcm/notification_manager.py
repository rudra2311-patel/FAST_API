"""
Notification Management System - Industry Best Practices
Handles deduplication, rate limiting, batching, and personalization
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from sqlalchemy import Column, String, DateTime, Integer, Boolean, Text
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, desc
from src.db.redis import redis_client
import hashlib
import json


class NotificationPreference:
    """User notification preferences"""
    
    FREQUENCY_IMMEDIATE = "immediate"
    FREQUENCY_HOURLY = "hourly"
    FREQUENCY_DAILY = "daily"
    
    SEVERITY_ALL = ["critical", "high", "medium", "low"]
    SEVERITY_CRITICAL_HIGH = ["critical", "high"]
    SEVERITY_CRITICAL_ONLY = ["critical"]


class NotificationManager:
    """
    Manages notification deduplication, rate limiting, and batching
    following industry best practices.
    """
    
    # Rate limiting: Max notifications per user per time period
    MAX_NOTIFICATIONS_PER_HOUR = 5
    MAX_NOTIFICATIONS_PER_DAY = 20
    
    # Deduplication: Don't send same notification within this time
    DEDUP_WINDOW_MINUTES = 60
    
    # Batching: Group similar notifications
    BATCH_WINDOW_MINUTES = 15
    
    def __init__(self):
        pass
        
    async def _get_redis(self):
        """Get Redis client for caching"""
        return redis_client
    
    def _generate_notification_hash(
        self,
        user_id: str,
        notification_type: str,
        severity: str,
        content_summary: str
    ) -> str:
        """
        Generate unique hash for notification deduplication.
        
        Args:
            user_id: User ID
            notification_type: Type of notification (weather, disease, etc.)
            severity: Severity level
            content_summary: Brief content summary
            
        Returns:
            SHA256 hash of notification
        """
        content = f"{user_id}:{notification_type}:{severity}:{content_summary}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    async def should_send_notification(
        self,
        user_id: str,
        notification_type: str,
        severity: str,
        content_summary: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Determines if notification should be sent based on:
        - Deduplication (already sent recently?)
        - Rate limiting (too many notifications?)
        - User preferences
        - Severity importance
        
        Args:
            user_id: User ID
            notification_type: weather, disease, action
            severity: critical, high, medium, low
            content_summary: Brief summary for deduplication
            force: Force send regardless of limits (for critical alerts)
            
        Returns:
            Dict with 'should_send' boolean and 'reason' string
        """
        redis = await self._get_redis()
        
        # Critical alerts always go through
        if force or severity == "critical":
            return {"should_send": True, "reason": "critical_priority"}
        
        # Check deduplication
        notif_hash = self._generate_notification_hash(
            user_id, notification_type, severity, content_summary
        )
        dedup_key = f"notif:dedup:{notif_hash}"
        
        if await redis.get(dedup_key):
            return {
                "should_send": False,
                "reason": "duplicate_recent",
                "message": f"Same notification sent within {self.DEDUP_WINDOW_MINUTES} minutes"
            }
        
        # Check hourly rate limit
        hourly_key = f"notif:rate:hour:{user_id}"
        hourly_count = await redis.get(hourly_key)
        
        if hourly_count and int(hourly_count) >= self.MAX_NOTIFICATIONS_PER_HOUR:
            # Allow high severity to exceed limits slightly
            if severity != "high":
                return {
                    "should_send": False,
                    "reason": "rate_limit_hourly",
                    "message": f"Exceeded {self.MAX_NOTIFICATIONS_PER_HOUR} notifications per hour"
                }
        
        # Check daily rate limit
        daily_key = f"notif:rate:day:{user_id}"
        daily_count = await redis.get(daily_key)
        
        if daily_count and int(daily_count) >= self.MAX_NOTIFICATIONS_PER_DAY:
            return {
                "should_send": False,
                "reason": "rate_limit_daily",
                "message": f"Exceeded {self.MAX_NOTIFICATIONS_PER_DAY} notifications per day"
            }
        
        # Check user preferences (would need to fetch from DB)
        # For now, allow all high and critical
        
        return {"should_send": True, "reason": "approved"}
    
    async def mark_notification_sent(
        self,
        user_id: str,
        notification_type: str,
        severity: str,
        content_summary: str
    ):
        """
        Mark notification as sent for deduplication and rate limiting.
        
        Args:
            user_id: User ID
            notification_type: Type of notification
            severity: Severity level
            content_summary: Content summary
        """
        redis = await self._get_redis()
        
        # Set deduplication key
        notif_hash = self._generate_notification_hash(
            user_id, notification_type, severity, content_summary
        )
        dedup_key = f"notif:dedup:{notif_hash}"
        await redis.setex(
            dedup_key,
            self.DEDUP_WINDOW_MINUTES * 60,
            "1"
        )
        
        # Increment hourly counter
        hourly_key = f"notif:rate:hour:{user_id}"
        if not await redis.get(hourly_key):
            await redis.setex(hourly_key, 3600, "1")
        else:
            await redis.incr(hourly_key)
        
        # Increment daily counter
        daily_key = f"notif:rate:day:{user_id}"
        if not await redis.get(daily_key):
            await redis.setex(daily_key, 86400, "1")
        else:
            await redis.incr(daily_key)
    
    async def get_pending_batch_notifications(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get pending notifications that can be batched together.
        
        Args:
            user_id: User ID
            
        Returns:
            List of pending notifications
        """
        redis = await self._get_redis()
        batch_key = f"notif:batch:{user_id}"
        
        notifications = await redis.lrange(batch_key, 0, -1)
        return [json.loads(n) for n in notifications] if notifications else []
    
    async def add_to_batch(
        self,
        user_id: str,
        notification_data: Dict[str, Any]
    ):
        """
        Add notification to batch queue.
        
        Args:
            user_id: User ID
            notification_data: Notification data
        """
        redis = await self._get_redis()
        batch_key = f"notif:batch:{user_id}"
        
        notification_data["queued_at"] = datetime.utcnow().isoformat()
        await redis.rpush(batch_key, json.dumps(notification_data))
        await redis.expire(batch_key, self.BATCH_WINDOW_MINUTES * 60)
    
    async def clear_batch(self, user_id: str):
        """Clear batch queue for user"""
        redis = await self._get_redis()
        batch_key = f"notif:batch:{user_id}"
        await redis.delete(batch_key)
    
    def should_batch_notification(
        self,
        severity: str,
        notification_type: str
    ) -> bool:
        """
        Determine if notification should be batched.
        
        Args:
            severity: Notification severity
            notification_type: Type of notification
            
        Returns:
            True if should be batched, False if should send immediately
        """
        # Never batch critical alerts
        if severity == "critical":
            return False
        
        # Never batch action-required notifications
        if notification_type == "action":
            return False
        
        # Batch low and medium severity weather alerts
        if severity in ["low", "medium"] and notification_type == "weather":
            return True
        
        return False
    
    def create_personalized_message(
        self,
        user_name: str,
        farm_name: str,
        crop: str,
        severity: str,
        risk_type: str,
        weather_data: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Create personalized notification message.
        
        Args:
            user_name: User's name
            farm_name: Farm name
            crop: Crop type
            severity: Alert severity
            risk_type: Type of risk
            weather_data: Weather conditions
            
        Returns:
            Dict with 'title' and 'body'
        """
        # Severity-based emojis and tone
        severity_config = {
            "critical": {
                "emoji": "🔴",
                "urgency": "URGENT",
                "action": "Take immediate action"
            },
            "high": {
                "emoji": "🟠",
                "urgency": "Important",
                "action": "Action recommended"
            },
            "medium": {
                "emoji": "🟡",
                "urgency": "Notice",
                "action": "Monitor situation"
            },
            "low": {
                "emoji": "🟢",
                "urgency": "Update",
                "action": "No action needed"
            }
        }
        
        config = severity_config.get(severity, severity_config["medium"])
        
        # Personalized title
        if severity in ["critical", "high"]:
            title = f"{config['emoji']} {config['urgency']}: {farm_name} Alert"
        else:
            title = f"{config['emoji']} {farm_name} Weather Update"
        
        # Personalized body with actionable info
        temp = weather_data.get("temperature", "N/A")
        humidity = weather_data.get("humidity", "N/A")
        rainfall = weather_data.get("rainfall_mm", 0)
        
        if severity == "critical":
            body = (
                f"Critical conditions detected for your {crop.title()} crop! "
                f"{risk_type}. {config['action']} to protect your harvest."
            )
        elif severity == "high":
            body = (
                f"High risk alert for {crop.title()} at {farm_name}. "
                f"{risk_type}. Current: {temp}°C, {humidity}% humidity"
            )
        elif severity == "medium":
            body = (
                f"Weather conditions may affect your {crop.title()}. "
                f"{risk_type}. Recommended to {config['action'].lower()}."
            )
        else:
            body = (
                f"Favorable conditions for {crop.title()}. "
                f"Temp: {temp}°C, Humidity: {humidity}%. "
                f"No immediate concerns."
            )
        
        return {"title": title, "body": body}
    
    def create_batched_message(
        self,
        user_name: str,
        notifications: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        Create single notification from batch of alerts.
        
        Args:
            user_name: User's name
            notifications: List of notification data
            
        Returns:
            Dict with 'title' and 'body'
        """
        count = len(notifications)
        
        # Get highest severity
        severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
        highest_severity = max(
            notifications,
            key=lambda n: severity_order.get(n.get("severity", "low"), 0)
        )
        
        severity_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢"
        }
        
        emoji = severity_emoji.get(highest_severity.get("severity", "low"), "📊")
        
        title = f"{emoji} {count} Weather Updates for Your Farms"
        
        # Summarize alerts
        farms = set(n.get("farm_name", "Unknown") for n in notifications)
        farms_text = ", ".join(list(farms)[:3])
        if len(farms) > 3:
            farms_text += f" and {len(farms) - 3} more"
        
        body = (
            f"You have {count} weather alerts across {len(farms)} farm(s): {farms_text}. "
            f"Tap to view details."
        )
        
        return {"title": title, "body": body}


# Global instance
notification_manager = NotificationManager()
