"""
Translation API using Sarvam AI
Supports 22 Indian languages with high accuracy
Features: Smart caching, batch processing, cost optimization
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from src.translation.engine import translator
from src.translation.utils import map_lang_code
from src.translation.cache import (
    get_cached_translation, 
    cache_translation,
    get_cached_batch,
    cache_batch,
    get_cache_stats,
    clear_cache
)

router = APIRouter(prefix="/api/v1/translate", tags=["translation"])


class TranslateRequest(BaseModel):
    text: str
    lang: str  # Language code: hi, gu, mr, ta, te, kn, ml, bn, pa, etc.


class TranslateResponse(BaseModel):
    original: str
    translated: str
    target_language: str
    cached: bool = False  # Indicates if result came from cache


class BatchTranslateRequest(BaseModel):
    texts: List[str]  # Multiple texts for batch translation
    lang: str  # Target language code


class BatchTranslateResponse(BaseModel):
    translations: List[str]
    target_language: str
    cached_count: int  # Number of translations from cache
    api_calls: int  # Number of API calls made
    cache_hit_rate: float  # Percentage of cache hits


class CacheStatsResponse(BaseModel):
    total_cached_translations: int
    memory_used: str
    cache_ttl_hours: float
    estimated_cost_saved: str


@router.post("/", response_model=TranslateResponse)
async def translate_text(payload: TranslateRequest):
    """
    Translate English text to Indian languages using Sarvam AI
    
    **Features:**
    - ✅ Smart caching (Redis) - 75% cost reduction
    - ✅ 24-hour cache TTL
    - ✅ Graceful degradation if Redis is down
    
    **Supported languages (22):**
    - Hindi (hi), Gujarati (gu), Marathi (mr)
    - Tamil (ta), Telugu (te), Kannada (kn)
    - Malayalam (ml), Bengali (bn), Punjabi (pa)
    - Odia (or), Assamese (as), Urdu (ur)
    - And 10 more Indian languages
    
    **Example Request:**
    ```json
    {
      "text": "Late Blight disease detected on your potato farm",
      "lang": "hi"
    }
    ```
    
    **Example Response:**
    ```json
    {
      "original": "Late Blight disease detected...",
      "translated": "आपके आलू के खेत पर लेट ब्लाइट रोग का पता चला",
      "target_language": "hi-IN",
      "cached": false
    }
    ```
    
    **Performance:**
    - Cache hit: ~5ms, ₹0 cost
    - Cache miss: ~250ms, ₹0.125 cost
    """
    try:
        # STEP 1: Check Redis cache first
        print(f"\n🔍 Translation request: '{payload.text[:50]}...' → {payload.lang}")
        cached_translation = await get_cached_translation(payload.text, payload.lang)
        
        if cached_translation:
            # Cache hit - return immediately (fast + free!)
            print(f"⚡ Cache HIT! Returning cached translation")
            return TranslateResponse(
                original=payload.text,
                translated=cached_translation,
                target_language=map_lang_code(payload.lang),
                cached=True
            )
        
        # STEP 2: Cache miss - call Sarvam AI API
        print(f"🌐 Cache MISS! Calling Sarvam AI API...")
        translated = translator.translate(payload.text, payload.lang)
        
        # STEP 3: Store in cache for future requests
        await cache_translation(payload.text, payload.lang, translated)
        
        return TranslateResponse(
            original=payload.text,
            translated=translated,
            target_language=map_lang_code(payload.lang),
            cached=False
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Translation failed: {str(e)}"
        )


@router.post("/batch", response_model=BatchTranslateResponse)
async def translate_batch(payload: BatchTranslateRequest):
    """
    Batch translate multiple texts (optimized for disease results)
    
    **Use Case:** 
    Translate 4 fields at once: disease name, symptoms, treatment, prevention
    
    **Optimization Strategy:**
    1. Check cache for all 4 texts (Redis MGET - single round-trip)
    2. Only call API for cache misses
    3. Merge cached + API results
    4. Store new translations in cache
    
    **Example Request:**
    ```json
    {
      "texts": [
        "Tomato Late Blight",
        "Brown spots on leaves with white mold",
        "Apply copper-based fungicide every 7 days",
        "Improve drainage and avoid overhead watering"
      ],
      "lang": "hi"
    }
    ```
    
    **Example Response:**
    ```json
    {
      "translations": [
        "टमाटर लेट ब्लाइट",
        "पत्ती पर भूरे धब्बे...",
        "कवकनाशी का प्रयोग...",
        "जल निकासी में सुधार..."
      ],
      "target_language": "hi-IN",
      "cached_count": 2,
      "api_calls": 2,
      "cache_hit_rate": 50.0
    }
    ```
    
    **Performance:**
    - All cached (4/4): ~10ms, ₹0
    - Mixed (2/4 cached): ~250ms, ₹0.25
    - All miss (0/4): ~500ms, ₹0.50
    """
    try:
        print(f"\n🔍 Batch translation: {len(payload.texts)} texts → {payload.lang}")
        
        # STEP 1: Batch cache check using MGET
        cached_results = await get_cached_batch(payload.texts, payload.lang)
        
        # STEP 2: Identify which texts need API calls
        texts_to_translate = []
        texts_indices = []  # Track original positions
        
        for i, cached in enumerate(cached_results):
            if cached is None:
                texts_to_translate.append(payload.texts[i])
                texts_indices.append(i)
        
        # STEP 3: Call API only for cache misses
        api_results = []
        if texts_to_translate:
            print(f"🌐 Calling API for {len(texts_to_translate)} uncached texts...")
            for text in texts_to_translate:
                translated = translator.translate(text, payload.lang)
                api_results.append(translated)
        
        # STEP 4: Merge cached + API results (preserve order!)
        final_translations = []
        api_index = 0
        
        for i, cached in enumerate(cached_results):
            if cached is not None:
                # Use cached value
                final_translations.append(cached)
            else:
                # Use API result
                final_translations.append(api_results[api_index])
                api_index += 1
        
        # STEP 5: Cache new translations
        if texts_to_translate and api_results:
            await cache_batch(texts_to_translate, payload.lang, api_results)
        
        # Calculate metrics
        cached_count = sum(1 for c in cached_results if c is not None)
        api_calls = len(texts_to_translate)
        cache_hit_rate = (cached_count / len(payload.texts) * 100) if payload.texts else 0
        
        print(f"✅ Batch complete: {cached_count} cached, {api_calls} API calls ({cache_hit_rate:.1f}% hit rate)")
        
        return BatchTranslateResponse(
            translations=final_translations,
            target_language=map_lang_code(payload.lang),
            cached_count=cached_count,
            api_calls=api_calls,
            cache_hit_rate=cache_hit_rate
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Batch translation failed: {str(e)}"
        )


@router.get("/cache/stats", response_model=CacheStatsResponse)
async def get_translation_cache_stats():
    """
    Get cache statistics (admin/monitoring endpoint)
    
    **Returns:**
    ```json
    {
      "total_cached_translations": 1247,
      "memory_used": "2.5MB",
      "cache_ttl_hours": 24,
      "estimated_cost_saved": "₹155.88"
    }
    ```
    
    **Use Cases:**
    - Monitor cache performance
    - Calculate cost savings
    - Capacity planning
    """
    try:
        stats = await get_cache_stats()
        return CacheStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get cache stats: {str(e)}"
        )


@router.delete("/cache/clear")
async def clear_translation_cache(lang: str = None):
    """
    Clear translation cache (admin endpoint)
    
    **Query Parameters:**
    - `lang` (optional): Clear only specific language (e.g., ?lang=hi)
    - If not provided: Clear all translations
    
    **Use Cases:**
    - Content updates (disease info changed)
    - Testing new translation models
    - Memory management
    
    **Example:**
    - Clear all: DELETE /api/v1/translate/cache/clear
    - Clear Hindi: DELETE /api/v1/translate/cache/clear?lang=hi
    """
    try:
        deleted = await clear_cache(lang)
        return {
            "message": f"Cache cleared successfully",
            "deleted_keys": deleted,
            "language": lang or "all"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear cache: {str(e)}"
        )

