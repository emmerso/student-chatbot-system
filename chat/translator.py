from googletrans import Translator, LANGUAGES
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class MultilingualTranslator:
    def __init__(self):
        self.translator = Translator()
        self.supported_languages = {
            'en': 'english',
            'sn': 'shona'
        }
    
    def detect_language(self, text):
        """
        Detect the language of input text
        Returns 'en' for English, 'sn' for Shona, 'en' as default
        """
        try:
            # Clean text for better detection
            cleaned_text = text.strip()
            if not cleaned_text:
                return 'en'
            
            detection = self.translator.detect(cleaned_text)
            detected_lang = detection.lang
            
            # Map detected language to our supported languages
            if detected_lang == 'en':
                return 'en'
            elif detected_lang == 'sn':
                return 'sn'
            else:
                # Check if text contains common Shona words/patterns
                if self._is_likely_shona(cleaned_text):
                    return 'sn'
                return 'en'  # Default to English
                
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            return 'en'  # Default fallback
    
    def _is_likely_shona(self, text):
        """
        Check for common Shona words/patterns as fallback
        """
        shona_indicators = [
            'mhoro', 'mangwanani', 'masikati', 'manheru', 'ndeipi', 'zvakanaka',
            'tinotenda', 'pamusoroi', 'hongu', 'kwete', 'sei', 'rinhi', 'ripi',
            'makadii', 'zita', 'renyu', 'ndiani', 'ndiri', 'ndinoda', 'handina',
            'mukoma', 'hanzvadzi', 'amai', 'baba', 'mwana', 'mukomana', 'musikana'
        ]
        
        text_lower = text.lower()
        return any(indicator in text_lower for indicator in shona_indicators)
    
    def translate_text(self, text, target_language):
        """
        Translate text to target language
        """
        try:
            if not text.strip():
                return text
            
            # Don't translate if already in target language
            detected_lang = self.detect_language(text)
            if detected_lang == target_language:
                return text
            
            result = self.translator.translate(
                text, 
                src=detected_lang, 
                dest=target_language
            )
            return result.text
            
        except Exception as e:
            logger.error(f"Translation error: {e}")
            return text  # Return original text if translation fails
    
    def translate_to_user_language(self, text, user_input):
        """
        Translate response text to match user's input language
        """
        user_language = self.detect_language(user_input)
        return self.translate_text(text, user_language)

# Global translator instance
translator = MultilingualTranslator()