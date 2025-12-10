from sqlmodel import SQLModel, Field, Column
from sqlalchemy import ForeignKey
from datetime import datetime
import uuid
import sqlalchemy.dialects.postgresql as pg

class Farm(SQLModel, table=True):
    __tablename__ = "farms"

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

    # ADDED: Farm name
    name: str | None = Field(default=None, nullable=True)

    # location
    lat: float = Field(nullable=False)
    lon: float = Field(nullable=False)

    # associated crop
    crop: str = Field(nullable=False)

    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(pg.TIMESTAMP, nullable=False)
    )
