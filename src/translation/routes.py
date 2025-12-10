"""
Translation API using Sarvam AI
Supports 22 Indian languages with high accuracy
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.translation.engine import translator
from src.translation.utils import map_lang_code

router = APIRouter(prefix="/api/v1/translate", tags=["translation"])


class TranslateRequest(BaseModel):
    text: str
    lang: str  # Language code: hi, gu, mr, ta, te, kn, ml, bn, pa, etc.


class TranslateResponse(BaseModel):
    original: str
    translated: str
    target_language: str


@router.post("/", response_model=TranslateResponse)
async def translate_text(payload: TranslateRequest):
    """
    Translate English text to Indian languages using Sarvam AI
    
    Supported languages (22):
    - Hindi (hi), Gujarati (gu), Marathi (mr)
    - Tamil (ta), Telugu (te), Kannada (kn)
    - Malayalam (ml), Bengali (bn), Punjabi (pa)
    - Odia (or), Assamese (as), Urdu (ur)
    - And 10 more Indian languages
    
    Example:
    ```json
    {
      "text": "Late Blight disease detected on your potato farm",
      "lang": "hi"
    }
    ```
    
    Returns:
    ```json
    {
      "original": "Late Blight disease detected...",
      "translated": "आपके आलू के खेत पर लेट ब्लाइट रोग का पता चला",
      "target_language": "hi-IN"
    }
    ```
    """
    try:
        # Convert to Sarvam format (e.g., hi -> hi-IN)
        target_lang = map_lang_code(payload.lang)
        
        # Translate using Sarvam AI
        translated = translator.translate(payload.text, payload.lang)
        
        return TranslateResponse(
            original=payload.text,
            translated=translated,
            target_language=target_lang
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {str(e)}"
        )
