import asyncio
from sqlmodel import Session, select
from apscheduler.schedulers.background import BackgroundScheduler

from src.db.main import get_session
from src.weather.services import get_weather_and_risk
from src.weather.models import WeatherLog, NotificationLog
from src.weather.notifier import process_pending_notifications
from src.farms.models import Farm


scheduler = BackgroundScheduler()


def run_weather_job():
    """
    Main auto weather monitoring loop.
    Runs every X hours.
    """

    print("⏳ Running scheduled weather monitoring...")

    with next(get_session()) as session:

        farms = session.exec(select(Farm)).all()
        print(f"🌾 Found {len(farms)} farms to process.")

        for farm in farms:
            try:
                process_single_farm(session, farm)
            except Exception as e:
                print(f"❌ Error processing farm {farm.id}: {e}")

    # After processing all farms → send pending notifications
    sent_count = process_pending_notifications()
    print(f"📨 {sent_count} notifications sent.")


def process_single_farm(session: Session, farm: Farm):
    """
    Fetches weather, evaluates risk, stores logs.
    """
    print(f"➡ Checking farm {farm.id} (crop={farm.crop})...")

    # Weather + risk from services
    result = asyncio.run(get_weather_and_risk(farm.lat, farm.lon, farm.crop))

    weather = result["weather"]
    risk = result["risk"]

    print(f"   ✔ Risk found: {risk['risk']} ({risk['severity']})")

    # Save weather log
    log = WeatherLog(
        user_id=farm.user_id,
        lat=farm.lat,
        lon=farm.lon,
        weather=weather,
        risk=risk["risk"],
        severity=risk["severity"],
        message=risk["message"],
        advice=risk["advice"]
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    # Create notification entry for HIGH/CRITICAL risks
    if risk["severity"] in ["high", "critical"]:
        notif = NotificationLog(
            user_id=farm.user_id,
            weather_log_id=log.id,
            severity=risk["severity"],
            message=risk["message"],
        )
        session.add(notif)
        session.commit()

    return result


def init_scheduler():
    """
    Start the scheduler on FastAPI startup.
    """
    scheduler.add_job(run_weather_job, "interval", hours=3)
    scheduler.start()
    print("⏱ Background scheduler started.")
