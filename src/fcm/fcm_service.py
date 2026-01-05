"""
Firebase Cloud Messaging Service for sending push notifications.
"""
import json
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    FCM_AVAILABLE = True
except ImportError:
    FCM_AVAILABLE = False
    print("⚠️ firebase-admin not installed. Run: pip install firebase-admin")


class FCMService:
    """
    Service for sending push notifications via Firebase Cloud Messaging.
    """
    
    _initialized = False
    
    @classmethod
    def initialize(cls, service_account_path: str = "firebase-service-account.json"):
        """
        Initialize Firebase Admin SDK.
        
        Args:
            service_account_path: Path to Firebase service account JSON file
        """
        if not FCM_AVAILABLE:
            print("⚠️ FCM not available - firebase-admin not installed")
            return False
            
        if cls._initialized:
            return True
            
        try:
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred)
            cls._initialized = True
            print("✅ Firebase Admin SDK initialized")
            return True
        except Exception as e:
            print(f"❌ Failed to initialize Firebase Admin SDK: {e}")
            return False
    
    @classmethod
    async def send_notification(
        cls,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        severity: str = "medium"
    ) -> Dict[str, Any]:
        """
        Send push notification to a single device.
        
        Args:
            token: FCM device token
            title: Notification title
            body: Notification body
            data: Additional data payload
            severity: Alert severity (critical, high, medium, low)
            
        Returns:
            Dict with success status and message_id or error
        """
        if not FCM_AVAILABLE or not cls._initialized:
            return {"success": False, "error": "FCM not available"}
        
        try:
            # Convert data values to strings (FCM requirement)
            data = data or {}
            data_payload = {k: str(v) for k, v in data.items()}
            data_payload["severity"] = severity
            data_payload["timestamp"] = datetime.utcnow().isoformat()
            
            # Determine notification priority
            priority = "high" if severity in ["critical", "high"] else "normal"
            
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data_payload,
                token=token,
                android=messaging.AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        channel_id='critical_alerts_channel',
                        priority='high' if severity in ["critical", "high"] else 'default',
                        sound='default',
                        color='#4CAF50',
                        icon='ic_launcher'
                    )
                ),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(
                            alert=messaging.ApsAlert(
                                title=title,
                                body=body
                            ),
                            badge=1,
                            sound='default'
                        )
                    )
                )
            )
            
            response = messaging.send(message)
            print(f"✅ FCM sent to {token[:20]}... - {title}")
            return {"success": True, "message_id": response}
            
        except messaging.UnregisteredError:
            print(f"⚠️ FCM token unregistered: {token[:20]}...")
            return {"success": False, "error": "token_unregistered"}
        except Exception as e:
            print(f"❌ FCM send error: {e}")
            return {"success": False, "error": str(e)}
    
    @classmethod
    async def send_multicast(
        cls,
        tokens: List[str],
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        severity: str = "medium"
    ) -> Dict[str, Any]:
        """
        Send push notification to multiple devices.
        
        Args:
            tokens: List of FCM device tokens
            title: Notification title
            body: Notification body
            data: Additional data payload
            severity: Alert severity
            
        Returns:
            Dict with success_count, failure_count, and failed_tokens
        """
        if not FCM_AVAILABLE or not cls._initialized:
            return {"success": False, "error": "FCM not available"}
        
        if not tokens:
            return {"success": True, "success_count": 0, "failure_count": 0}
        
        try:
            # Convert data values to strings
            data = data or {}
            data_payload = {k: str(v) for k, v in data.items()}
            data_payload["severity"] = severity
            data_payload["timestamp"] = datetime.utcnow().isoformat()
            
            priority = "high" if severity in ["critical", "high"] else "normal"
            
            message = messaging.MulticastMessage(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data_payload,
                tokens=tokens,
                android=messaging.AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        channel_id='critical_alerts_channel',
                        priority='high' if severity in ["critical", "high"] else 'default'
                    )
                )
            )
            
            response = messaging.send_multicast(message)
            
            print(f"✅ FCM multicast: {response.success_count}/{len(tokens)} sent - {title}")
            
            # Collect failed tokens
            failed_tokens = []
            if response.failure_count > 0:
                for idx, resp in enumerate(response.responses):
                    if not resp.success:
                        failed_tokens.append(tokens[idx])
            
            return {
                "success": True,
                "success_count": response.success_count,
                "failure_count": response.failure_count,
                "failed_tokens": failed_tokens
            }
            
        except Exception as e:
            print(f"❌ FCM multicast error: {e}")
            return {"success": False, "error": str(e)}
    
    @classmethod
    async def send_to_topic(
        cls,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, str]] = None,
        severity: str = "medium"
    ) -> Dict[str, Any]:
        """
        Send push notification to all devices subscribed to a topic.
        
        Args:
            topic: Topic name (e.g., 'critical_alerts', 'weather_updates')
            title: Notification title
            body: Notification body
            data: Additional data payload
            severity: Alert severity
            
        Returns:
            Dict with success status and message_id or error
        """
        if not FCM_AVAILABLE or not cls._initialized:
            return {"success": False, "error": "FCM not available"}
        
        try:
            data = data or {}
            data_payload = {k: str(v) for k, v in data.items()}
            data_payload["severity"] = severity
            data_payload["timestamp"] = datetime.utcnow().isoformat()
            
            priority = "high" if severity in ["critical", "high"] else "normal"
            
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body
                ),
                data=data_payload,
                topic=topic,
                android=messaging.AndroidConfig(
                    priority=priority,
                    notification=messaging.AndroidNotification(
                        channel_id='critical_alerts_channel',
                        priority='high' if severity in ["critical", "high"] else 'default'
                    )
                )
            )
            
            response = messaging.send(message)
            print(f"✅ FCM sent to topic '{topic}' - {title}")
            return {"success": True, "message_id": response}
            
        except Exception as e:
            print(f"❌ FCM topic send error: {e}")
            return {"success": False, "error": str(e)}
