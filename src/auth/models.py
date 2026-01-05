from sqlmodel import Column, Field, SQLModel
from datetime import datetime
from typing import Optional
import uuid
import sqlalchemy.dialects.postgresql as pg

class User(SQLModel, table=True):
    __tablename__ = "users"
    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, nullable=False),
    )
    username: str
    email: str
    first_name: str
    last_name: str
    is_verified: bool = Field(default=False)
    password_hash: str = Field(exclude=True)
    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(pg.TIMESTAMP, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(pg.TIMESTAMP, nullable=False)
    )
    
    # FCM (Firebase Cloud Messaging) fields
    fcm_token: Optional[str] = Field(default=None, max_length=500)
    fcm_token_updated_at: Optional[datetime] = Field(
        default=None,
        sa_column=Column(pg.TIMESTAMP, nullable=True)
    )

    def __repr__(self) -> str:
        return f"<User{self.username}>"
    