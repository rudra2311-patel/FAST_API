from fastapi import APIRouter,Depends
from fastapi import status, HTTPException
from typing import List
from src.books.books_data import books
from src.books.schemas import Book, BookUpdateModel,BookCreateModel
from src.db.main import get_session
from sqlmodel.ext.asyncio.session import AsyncSession
from src.books.services import BookService

book_router = APIRouter()
book_service = BookService()
@book_router.get("/", response_model=List[Book])
async def get_all_books(session: AsyncSession = Depends(get_session)):
    books = await book_service.get_all_books(session)
    return books


@book_router.post("/", status_code=status.HTTP_201_CREATED, response_model=Book)
async def create_a_book(book_data: BookCreateModel, session: AsyncSession = Depends(get_session)) -> dict:
    new_book = await book_service.create_book(book_data, session)
    return new_book


@book_router.get("/{book_uid}", response_model=Book)
async def get_book(book_uid: str, session: AsyncSession = Depends(get_session)) -> dict:
    book = await book_service.get_book(book_uid, session)
    if book:
        return book
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")


@book_router.patch("/{book_uid}", response_model=Book)
async def update_book(book_uid: str, book_update_data: BookUpdateModel, session: AsyncSession = Depends(get_session)) -> dict:
   update_book = await book_service.update_book(book_uid, book_update_data, session)
   if update_book: 
         return update_book
   else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    

@book_router.delete("/{book_uid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_uid: str, session: AsyncSession = Depends(get_session)) -> None:
    deleted_book = await book_service.delete_book(book_uid, session)
    if deleted_book:
        return None
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")










































# from  fastapi import FastAPI, HTTPException
# from   pydantic import BaseModel ,Field
# from uuid import UUID


# app = FastAPI()
# class Book(BaseModel):
#     id: UUID
#     title: str = Field(min_length=1)
#     author: str = Field(min_length=1, max_length=100)
#     description: str | None = Field(default=None, min_length=1, max_length=100)
#     rating: int = Field(gt=-1, lt=101)


# Books = []
# @app.get("/greet/{name}")
# def read_root(name: str, age: int):
#     return {"Diya": f"{name}", "age": f"{age}"}

# @app.get("/")
# def read_api():
#     return {"Books": Books}

# @app.post("/")
# def create_book(book: Book):
#     Books.append(book)
#     return book


# @app.put("/{book_id}")
# def update_book(book_id: UUID, book: Book):
#     counter = 0
#     for b in Books:
#         if b.id == book_id:
#             Books[counter-1] = book
#             return Books[counter-1]
#         raise HTTPException(status_code=404, detail="Book not found")
#         counter += 1
#     raise HTTPException(status_code=404, detail="Book not found")


# @app.delete("/{book_id}")
# def delete_book(book_id: UUID):
#     for index, b in enumerate(Books):
#         if b.id == book_id:
#             del Books[index]
#             return {"Message": "Book deleted successfully"}
#     raise HTTPException(status_code=404, detail="Book not found")
