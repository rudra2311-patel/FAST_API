from  fastapi import FastAPI, HTTPException
from   pydantic import BaseModel ,Field
from uuid import UUID


app = FastAPI()
class Book(BaseModel):
    id: UUID
    title: str = Field(min_length=1)
    author: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, min_length=1, max_length=100)
    rating: int = Field(gt=-1, lt=101)


Books = []
@app.get("/greet/{name}")
def read_root(name: str, age: int):
    return {"Diya": f"{name}", "age": f"{age}"}

@app.get("/")
def read_api():
    return {"Books": Books}

@app.post("/")
def create_book(book: Book):
    Books.append(book)
    return book


@app.put("/{book_id}")
def update_book(book_id: UUID, book: Book):
    counter = 0
    for b in Books:
        if b.id == book_id:
            Books[counter-1] = book
            return Books[counter-1]
        raise HTTPException(status_code=404, detail="Book not found")
        counter += 1
    raise HTTPException(status_code=404, detail="Book not found")


@app.delete("/{book_id}")
def delete_book(book_id: UUID):
    for index, b in enumerate(Books):
        if b.id == book_id:
            del Books[index]
            return {"Message": "Book deleted successfully"}
    raise HTTPException(status_code=404, detail="Book not found")