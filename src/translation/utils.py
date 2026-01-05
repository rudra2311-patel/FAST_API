"""
Language code mapping for Sarvam AI Translation API
Maps Flutter/app language codes to Sarvam AI format
"""

def map_lang_code(code: str) -> str:
    """
    Convert app language codes to Sarvam AI format (lang-IN)
    
    Sarvam AI supports 22 Indian languages:
    Hindi, Gujarati, Marathi, Tamil, Telugu, Kannada, Malayalam,
    Bengali, Punjabi, Odia, Assamese, Urdu, and 10 more
    
    Args:
        code: 2-letter language code (e.g., 'hi', 'gu', 'mr')
    
    Returns:
        Sarvam format language code (e.g., 'hi-IN', 'gu-IN')
    """
    # Sarvam uses lang-IN format (e.g., hi-IN, gu-IN)
    # If code already has region (e.g., hi-IN), return as is
    if "-" in code:
        return code
    
    # Otherwise, append -IN for Indian languages
    return f"{code}-IN"
