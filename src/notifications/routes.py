"""
Notification routes for fetching user notifications created by weather/risk system
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
from typing import List
from datetime import datetime, timedelta

from src.db.main import get_session
from src.auth.dependencies import AccessTokenBearer
from ..weather.models import NotificationLog

router = APIRouter()


@router.get("/my")
async def get_my_notifications(
    token_data: dict = Depends(AccessTokenBearer()),
    session: Session = Depends(get_session),
    limit: int = Query(default=50, le=100),  # Max 100 notifications
    hours: int = Query(default=168, description="Get notifications from last N hours (default: 7 days)")
):
    """
    Get recent notifications for the authenticated user.
    Returns notifications created by weather/risk system.
    
    Query params:
    - limit: Maximum number of notifications (default: 50, max: 100)
    - hours: Get notifications from last N hours (default: 168 = 7 days)
    """
    try:
        user_id = token_data["user"]["user_id"]
        
        # Calculate cutoff time
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Query notification_logs from database (only recent ones)
        statement = select(NotificationLog).where(
            NotificationLog.user_id == user_id,
            NotificationLog.created_at >= cutoff_time
        ).order_by(NotificationLog.created_at.desc()).limit(limit)
        
        results = (await session.exec(statement)).all()
        
        # Convert to response format
        notifications = []
        for notif in results:
            notifications.append({
                "id": str(notif.id),
                "type": "weather",  # For now all are weather-related
                "severity": notif.severity,
                "message": notif.message,
                "created_at": notif.created_at.isoformat() if notif.created_at else None,
                "is_read": notif.is_read,
                "sent": notif.sent == 1,
            })
        
        return {
            "total": len(notifications),
            "notifications": notifications,
            "cutoff_hours": hours
        }
    
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
    Mark a notification as read
    """
    try:
        user_id = token_data["user"]["user_id"]
        
        # Find notification
        statement = select(NotificationLog).where(
            NotificationLog.id == notification_id,
            NotificationLog.user_id == user_id
        )
        result = (await session.exec(statement)).first()
        
        if not result:
            raise HTTPException(status_code=404, detail="Notification not found")
        
        # Mark as read
        result.is_read = True
        session.add(result)
        await session.commit()
        
        return {
            "status": "ok", 
            "message": "Notification marked as read",
            "notification_id": str(result.id)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    token_data: dict = Depends(AccessTokenBearer()),
    session: Session = Depends(get_session)
):
    """
    Mark all notifications as read for current user
    """
    try:
        user_id = token_data["user"]["user_id"]
        
        # Get all unread notifications
        statement = select(NotificationLog).where(
            NotificationLog.user_id == user_id,
            NotificationLog.is_read == False
        )
        results = (await session.exec(statement)).all()
        
        # Mark all as read
        count = 0
        for notif in results:
            notif.is_read = True
            session.add(notif)
            count += 1
        
        await session.commit()
        
        return {
            "status": "ok",
            "message": f"Marked {count} notifications as read"
        }
    
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/clear-old")
async def clear_old_notifications(
    token_data: dict = Depends(AccessTokenBearer()),
    session: Session = Depends(get_session),
    days: int = Query(default=7, description="Delete notifications older than N days")
):
    """
    Delete old notifications (older than specified days)
    """
    try:
        user_id = token_data["user"]["user_id"]
        
        cutoff_time = datetime.utcnow() - timedelta(days=days)
        
        # Find old notifications
        statement = select(NotificationLog).where(
            NotificationLog.user_id == user_id,
            NotificationLog.created_at < cutoff_time
        )
        results = (await session.exec(statement)).all()
        
        # Delete them
        count = 0
        for notif in results:
            session.delete(notif)
            count += 1
        
        await session.commit()
        
        return {
            "status": "ok",
            "message": f"Deleted {count} old notifications",
            "cutoff_days": days
        }
    
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(e))
