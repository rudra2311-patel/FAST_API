
from sqlmodel import SQLModel, Field, Column
from datetime import datetime
import uuid
import sqlalchemy.dialects.postgresql as pg
from sqlalchemy import ForeignKey


class Scan(SQLModel, table=True):
    __tablename__ = "scans"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, nullable=False),
    )

    user_id: uuid.UUID = Field(
        sa_column=Column(
            pg.UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),  # ✅ foreign key here
            nullable=False,
            index=True
        )
    )

    disease_name: str
    confidence: float
    image_url: str
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, nullable=False),
    )
