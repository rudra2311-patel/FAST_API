from fastapi import FastAPI
from contextlib import asynccontextmanager

from src.db.main import init_db
from src.books.routes import book_router
from src.auth.routes import auth_router
from src.scans.routes import router as scans_router
from src.weather.routes import router as weather_router
from src.farms.routes import router as farm_router
from src.notifications.routes import router as notifications_router
from src.translation.routes import router as translation_router

# ⏱ Import Scheduler Initializer
from src.weather.tasks import init_scheduler

# 🔔 Import WebSocket and Alert Monitor
from src.weather.websocket_routes import ws_router
from src.weather.alert_monitor import alert_monitor
from src.weather.redis_pubsub import redis_pubsub as redis_pubsub_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Starting up...")

    # Initialize DB
    await init_db()

    # Start background weather scheduler
    init_scheduler()

    # 🔔 Start Redis pub/sub listener
    await redis_pubsub_handler.start()

    # 🔔 Start background alert monitor
    await alert_monitor.start()

    yield

    print("🛑 Shutting down...")

    # 🔔 Stop alert monitor
    await alert_monitor.stop()

    # 🔔 Stop Redis pub/sub listener
    await redis_pubsub_handler.stop()


version1 = "v1"

app = FastAPI(
    title="AgriScan API",
    description="AI-powered crop disease detection API",
    version=version1,
    lifespan=lifespan,
)

# Routers
app.include_router(book_router,   prefix=f"/api/{version1}/books",  tags=["books"])
app.include_router(auth_router,   prefix=f"/api/{version1}/auth",   tags=["auth"])
app.include_router(scans_router,  prefix=f"/api/{version1}/scans",  tags=["scans"])
app.include_router(weather_router,prefix=f"/api/{version1}/weather",tags=["weather"])
app.include_router(farm_router,   prefix=f"/api/{version1}/farms",  tags=["farms"])
app.include_router(notifications_router, prefix=f"/api/{version1}/notifications", tags=["notifications"])
app.include_router(translation_router, tags=["translation"])  # Already has /api/v1/translate prefix

# 🔔 WebSocket Router (no /api/v1 prefix for WebSocket)
app.include_router(ws_router, prefix="/ws", tags=["websockets"])
