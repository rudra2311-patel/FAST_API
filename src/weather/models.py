from sqlmodel import SQLModel, Field, Column
from sqlalchemy import ForeignKey
from datetime import datetime
import uuid
import sqlalchemy.dialects.postgresql as pg

class WeatherLog(SQLModel, table=True):
    __tablename__ = "weather_logs"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, nullable=False),
    )

    user_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True
        )
    )

    lat: float
    lon: float

    weather: dict = Field(
        sa_column=Column(pg.JSON, nullable=False)
    )

    risk: str = Field(nullable=False)
    severity: str = Field(nullable=False)
    message: str | None = None
    advice: str | None = None

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, nullable=False)
    )


class NotificationLog(SQLModel, table=True):
    __tablename__ = "notification_logs"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, nullable=False),
    )

    user_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True
        )
    )

    weather_log_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("weather_logs.id", ondelete="SET NULL"),
            nullable=True,
        )
    )

    severity: str
    message: str
    sent: int = 0  # 0 = pending, 1 = sent

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, nullable=False)
    )
