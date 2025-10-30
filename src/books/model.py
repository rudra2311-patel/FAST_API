
from sqlmodel import SQLModel,Field,Column
from datetime import datetime
import sqlalchemy.dialects.postgresql as pg
import uuid


class Book(SQLModel, table=True):
    __tablename__ = "books"
    id: uuid.UUID = Field(
        sa_column= Column(
            pg.UUID(as_uuid=True),  
            nullable=False,
            primary_key=True,
            default=uuid.uuid4
        )

    )
    title: str
    author: str
    publisher: str
    published_date: str
    page_count: int
    language: str
    created_at: datetime = Field(sa_column=Column(pg.TIMESTAMP,default=datetime.now()))
    updated_at: datetime = Field(sa_column=Column(pg.TIMESTAMP,default=datetime.now()))

def __repr__(self) -> str:
        return f"Book(id={self.id}, title={self.title}, author={self.author})"

