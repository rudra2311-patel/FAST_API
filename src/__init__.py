from fastapi import FastAPI, HTTPException
from src.books.routes import book_router
from contextlib import asynccontextmanager
from src.db.main import init_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting up...")
    await init_db()
    yield
    print(f"Shutting down...")


version1 = "v1"
app = FastAPI(

    title="Books API",
    description="A simple Books API built with FastAPI",
    version=version1,
    lifespan=lifespan,
)

app.include_router(book_router, prefix=f"/api{version1}/books", tags=["books"])