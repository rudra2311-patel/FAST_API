"""
FCM (Firebase Cloud Messaging) API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

from src.db.main import get_session
from src.auth.models import User
from src.auth.dependencies import AccessTokenBearer
from src.fcm import FCMService


router = APIRouter()


class FCMTokenRequest(BaseModel):
    """Request model for updating FCM token."""
    token: str


class PushNotificationRequest(BaseModel):
    """Request model for sending push notification."""
    fcm_token: str
    title: str
    body: str
    data: Optional[Dict[str, str]] = None
    severity: str = "medium"


@router.post("/token")
async def update_fcm_token(
    request: FCMTokenRequest,
    token_data: dict = Depends(AccessTokenBearer()),
    db: Session = Depends(get_session)
):
    """
    Update user's FCM token for push notifications.
    
    - **token**: FCM device token from Flutter app
    """
    try:
        # Get user from token
        user_id = token_data["user"]["user_id"]
        
        # Fetch user from database
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        current_user = result.scalar_one_or_none()
        
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update user's FCM token
        current_user.fcm_token = request.token
        current_user.fcm_token_updated_at = datetime.utcnow()
        await db.commit()
        
        print(f"✅ FCM token updated for user {current_user.username}")
        
        return {
            "message": "FCM token updated successfully",
            "user_id": str(current_user.id),
            "token_updated_at": current_user.fcm_token_updated_at
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"❌ Error updating FCM token: {e}")
        raise HTTPException(status_code=500, detail="Failed to update FCM token")


@router.get("/token")
async def get_fcm_token(
    token_data: dict = Depends(AccessTokenBearer()),
    db: Session = Depends(get_session)
):
    """
    Get current user's FCM token.
    """
    try:
        user_id = token_data["user"]["user_id"]
        
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        current_user = result.scalar_one_or_none()
        
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "fcm_token": current_user.fcm_token,
            "fcm_token_updated_at": current_user.fcm_token_updated_at
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get FCM token: {str(e)}")


@router.post("/send")
async def send_push_notification(
    request: PushNotificationRequest,
    token_data: dict = Depends(AccessTokenBearer())
):
    """
    Send push notification to a device.
    
    - **fcm_token**: Target device token
    - **title**: Notification title
    - **body**: Notification body
    - **data**: Additional data payload
    - **severity**: Alert severity (critical, high, medium, low)
    """
    try:
        result = await FCMService.send_notification(
            token=request.fcm_token,
            title=request.title,
            body=request.body,
            data=request.data,
            severity=request.severity
        )
        
        if result.get("success"):
            return {
                "success": True,
                "message": "Notification sent successfully",
                "message_id": result.get("message_id")
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Failed to send notification")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send notification: {str(e)}")


@router.delete("/token")
async def delete_fcm_token(
    token_data: dict = Depends(AccessTokenBearer()),
    db: Session = Depends(get_session)
):
    """
    Delete user's FCM token (e.g., on logout).
    """
    try:
        user_id = token_data["user"]["user_id"]
        
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        current_user = result.scalar_one_or_none()
        
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        current_user.fcm_token = None
        current_user.fcm_token_updated_at = None
        await db.commit()
        
        return {"message": "FCM token deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to delete FCM token: {str(e)}")


@router.post("/test-notification")
async def send_test_notification_to_self(
    token_data: dict = Depends(AccessTokenBearer()),
    db: Session = Depends(get_session)
):
    """
    Send a test notification to yourself (logged-in user).
    Use this to verify FCM is working.
    """
    try:
        user_id = token_data["user"]["user_id"]
        
        # Get current user
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        current_user = result.scalar_one_or_none()
        
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")
        
        if not current_user.fcm_token:
            raise HTTPException(
                status_code=400, 
                detail="No FCM token registered. Please update your FCM token first using POST /api/v1/fcm/token"
            )
        
        # Send test notification
        result = await FCMService.send_notification(
            token=current_user.fcm_token,
            title="🎉 Test Notification",
            body=f"Hello {current_user.username}! Your FCM notifications are working perfectly!",
            data={
                "type": "test",
                "user_id": str(current_user.id),
                "timestamp": datetime.utcnow().isoformat()
            },
            severity="medium"
        )
        
        if result.get("success"):
            return {
                "success": True,
                "message": "Test notification sent! Check your device.",
                "message_id": result.get("message_id"),
                "sent_to": current_user.username
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send notification: {result.get('error')}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
