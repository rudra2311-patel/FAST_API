from sqlmodel import SQLModel, Field, Column
from datetime import datetime, date
import sqlalchemy.dialects.postgresql as pg
import uuid


class Book(SQLModel, table=True):
    __tablename__ = "books"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(pg.UUID(as_uuid=True), primary_key=True, nullable=False),
    )

    title: str
    author: str
    publisher: str
    published_date: date
    page_count: int
    language: str

    created_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(pg.TIMESTAMP, nullable=False)
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column=Column(pg.TIMESTAMP, nullable=False)
    )
    
    def __repr__(self) -> str:
        return f"Book(id={self.id}, title={self.title}, author={self.author})"
