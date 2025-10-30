from fastapi import APIRouter
from fastapi import status, HTTPException
from typing import List
from src.books.books_data import books
from src.books.schemas import Book, BookUpdateModel
book_router = APIRouter()
@book_router.get("/", response_model=List[Book])
async def get_all_books():
    return books


@book_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_a_book(book_data: Book) -> dict:
    new_book = book_data.model_dump()

    books.append(new_book)

    return new_book


@book_router.get("/{book_id}")
async def get_book(book_id: int) -> dict:
    for book in books:
        if book["id"] == book_id:
            return book

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")


@book_router.patch("/{book_id}")
async def update_book(book_id: int,book_update_data:BookUpdateModel) -> dict:
    for book in books:
        if book['id'] == book_id:
            book['title'] = book_update_data.title
            book['publisher'] = book_update_data.publisher
            book['page_count'] = book_update_data.page_count
            book['language'] = book_update_data.language
            return book
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
@book_router.delete("/{book_id}",status_code=status.HTTP_204_NO_CONTENT)

@book_router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book(book_id: int):
    for book in books:
        if book["id"] == book_id:
            books.remove(book)
            return {}
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
