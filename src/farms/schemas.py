from pydantic import BaseModel
from typing import Optional
import uuid


class FarmCreate(BaseModel):
    lat: float
    lon: float
    crop: str
    name: str | None = None  # ADDED: Optional farm name


class FarmResponse(BaseModel):
    id: uuid.UUID
    lat: float
    lon: float
    crop: str
    name: str | None = None  # ADDED: Return farm name to frontend

    class Config:
        orm_mode = True
