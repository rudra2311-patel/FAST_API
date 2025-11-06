from datetime import datetime
import uuid
from pydantic import BaseModel, EmailStr, Field



class UserCreateModel(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    username: str = Field(min_length=3, max_length=50)
    email : EmailStr 
    password: str = Field(min_length=6)


class UserModel(BaseModel):
    id: uuid.UUID 
    username: str
    email: str
    first_name: str
    last_name: str
    is_verified: bool 
    password_hash: str = Field(exclude=True)
    created_at: datetime 
    updated_at: datetime 

class UserLoggingModel(BaseModel):
    email: str = Field(max_length=40)
    password: str = Field(min_length=6)
