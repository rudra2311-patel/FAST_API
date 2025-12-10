"""
Notification routes for fetching user notifications created by weather/risk system
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

from src.db.main import get_session
from src.auth.dependencies import AccessTokenBearer
from ..weather.models import NotificationLog

router = APIRouter()


@router.get("/my")
async def get_my_notifications(
    token_data: dict = Depends(AccessTokenBearer()),
    session: Session = Depends(get_session)
):
    """
    Get all notifications for the authenticated user.
    Returns notifications created by weather/risk system.
    """
    try:
        user_id = token_data["user"]["user_id"]
        
        # Query notification_logs from database
        statement = select(NotificationLog).where(
            NotificationLog.user_id == user_id
        ).order_by(NotificationLog.created_at.desc())
        
        results = session.exec(statement).all()
        
        # Convert to response format
        notifications = []
        for notif in results:
            notifications.append({
                "id": str(notif.id),
                "type": "weather",  # For now all are weather-related
                "severity": notif.severity,
                "message": notif.message,
                "created_at": notif.created_at.isoformat() if notif.created_at else None,
                "is_read": False,  # TODO: Add is_read field to model
            })
        
        return notifications
    
    except KeyError:
        raise HTTPException(status_code=401, detail="Invalid token structure")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    token_data: dict = Depends(AccessTokenBearer()),
    session: Session = Depends(get_session)
):
    """
    Mark a notification as read (placeholder for future implementation)
    """
    # TODO: Add is_read field to NotificationLog model
    return {"status": "ok", "message": "Feature coming soon"}
