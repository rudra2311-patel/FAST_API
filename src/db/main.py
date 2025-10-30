from sqlmodel  import  create_engine,text
from sqlalchemy.ext.asyncio import AsyncEngine
from src.config import Config
from src.books.model import Book
from sqlmodel import SQLModel


engine =  AsyncEngine(
    create_engine(
    url=Config.DATABASE_URL,
    echo=True,
))
async def init_db():
    async with engine.begin() as conn:
       from src.books.model import Book
       await conn.run_sync(SQLModel.metadata.create_all)
      