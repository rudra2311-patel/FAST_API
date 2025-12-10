from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class ScanCreate(BaseModel):
    disease_name: str
    confidence: float
    image_base64: Optional[str] = None  # sent from mobile app


class ScanRead(BaseModel):
    id: UUID             # ✅ keep UUID here, safer type
    disease_name: str
    confidence: float
    image_url: str
    created_at: datetime

    class Config:
        orm_mode = True
        json_encoders = {
            UUID: lambda v: str(v)     # ✅ convert UUID to string automatically
        }
