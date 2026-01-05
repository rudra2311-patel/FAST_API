"""
Translation Engine using Sarvam AI Official SDK
Supports 22 Indian languages with high accuracy
Docs: https://docs.sarvam.ai/api-reference-docs/getting-started/quickstart
"""
from sarvamai import SarvamAI
from src.config import Config

class SarvamTranslator:
    """
    Sarvam AI Translation Engine for Indian Languages
    Using official Python SDK
    """
    def __init__(self):
        print("🔵 Initializing Sarvam AI Translation SDK...")
        self.api_key = Config.SARVAM_API_KEY
        
        if not self.api_key:
            print("⚠️  WARNING: SARVAM_API_KEY not found in .env file!")
            print("   Add it to .env file: SARVAM_API_KEY=your_api_key_here")
            self.client = None
        else:
            self.client = SarvamAI(api_subscription_key=self.api_key)
            print(f"🟢 Sarvam AI Translation SDK ready! (Key: {self.api_key[:8]}...)")

    def translate(self, text: str, lang_code: str) -> str:
        """
        Translate English text to Indian languages using Sarvam AI
        
        Supported languages (22):
        - Hindi (hi-IN), Gujarati (gu-IN), Marathi (mr-IN)
        - Tamil (ta-IN), Telugu (te-IN), Kannada (kn-IN)
        - Malayalam (ml-IN), Bengali (bn-IN), Punjabi (pa-IN)
        - Odia (or-IN), Assamese (as-IN), Urdu (ur-IN)
        - And 10 more Indian languages
        
        Args:
            text: English text to translate
            lang_code: Target language code (e.g., 'hi', 'gu', 'mr')
                      Will be converted to Sarvam format (e.g., 'hi-IN')
        
        Returns:
            Translated text in target language
        """
        if not self.client:
            print("❌ No API key - returning original text")
            return text
        
        try:
            # Convert Flutter lang code to Sarvam format
            # e.g., 'hi' -> 'hi-IN', 'gu' -> 'gu-IN'
            target_lang = f"{lang_code}-IN" if "-" not in lang_code else lang_code
            
            print(f"🔍 DEBUG: Translating '{text}' to {target_lang}")
            
            # Use official SDK
            response = self.client.text.translate(
                input=text,
                source_language_code="en-IN",
                target_language_code=target_lang,
                speaker_gender="Male",
                mode="formal",
                enable_preprocessing=True
            )
            
            print(f"📥 API Response: {response}")
            
            translated_text = response.translated_text
            print(f"✅ Translated to {target_lang}: {text[:50]}... -> {translated_text[:50]}...")
            return translated_text
                    
        except Exception as e:
            print(f"❌ Translation error: {e}")
            # Fallback: return original text
            return text


# Shared singleton instance
translator = SarvamTranslator()
