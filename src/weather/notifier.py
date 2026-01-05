from sqlmodel import Session, select
from src.weather.models import NotificationLog
from src.db.main import get_session


def send_notification_to_user(user_id: str, title: str, message: str):
    """
    BASIC notifier (console log). Replace with FCM later.
    """
    print(f"[NOTIFY] User {user_id} | {title} | {message}")


def process_pending_notifications():
    """
    Fetch all unsent notifications and send them.
    """
    with next(get_session()) as session:
        stmt = select(NotificationLog).where(NotificationLog.sent == 0)
        pending = session.exec(stmt).all()

        for notif in pending:
            send_notification_to_user(
                user_id=str(notif.user_id),
                title=f"Weather Alert [{notif.severity.upper()}]",
                message=notif.message
            )

            notif.sent = 1
            session.add(notif)

        session.commit()

        return len(pending)
