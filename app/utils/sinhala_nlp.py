import re
from typing import Optional, List
import httpx  # ✅ Replace requests with httpx
import asyncio
import structlog

logger = structlog.get_logger(__name__)

class SinhalaNLP:
    def __init__(self):
        self.sinhala_unicode_range = (0x0D80, 0x0DFF)
        self.translate_api_url = "https://api.mymemory.translated.net/get"
    
    def detect_language(self, text: str) -> str:
        """Detect if text is primarily Sinhala or English"""
        if not text:
            return 'en'
        
        sinhala_chars = 0
        total_chars = 0
        
        for char in text:
            if char.isalpha():
                total_chars += 1
                if self._is_sinhala_char(char):
                    sinhala_chars += 1
        
        if total_chars == 0:
            return 'en'
        
        sinhala_ratio = sinhala_chars / total_chars
        
        # If more than 30% Sinhala characters, consider it Sinhala
        return 'si' if sinhala_ratio > 0.3 else 'en'
    
    def is_sinhala_text(self, text: str) -> bool:
        """Check if text contains Sinhala characters"""
        return any(self._is_sinhala_char(char) for char in text)
    
    def _is_sinhala_char(self, char: str) -> bool:
        """Check if character is in Sinhala Unicode range"""
        return self.sinhala_unicode_range[0] <= ord(char) <= self.sinhala_unicode_range[1]
    
    async def translate_to_sinhala(self, text: str) -> str:
        """Translate text to Sinhala using translation API (async version)"""
        try:
            params = {
                'q': text,
                'langpair': 'en|si',
                'de': 'your-email@domain.com'  # Replace with actual email
            }
            
            # Use httpx for async HTTP requests
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.translate_api_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                translated = data.get('responseData', {}).get('translatedText', text)
                logger.info("Text translated to Sinhala", 
                           original_length=len(text), 
                           translated_length=len(translated))
                return translated
            else:
                logger.error("Translation failed", status_code=response.status_code)
                return text
                
        except Exception as e:
            logger.error("Error translating to Sinhala", error=str(e))
            return text
    
    async def translate_to_english(self, text: str) -> str:
        """Translate Sinhala text to English (async version)"""
        try:
            params = {
                'q': text,
                'langpair': 'si|en',
                'de': 'your-email@domain.com'  # Replace with actual email
            }
            
            # Use httpx for async HTTP requests
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.translate_api_url, params=params)
            
            if response.status_code == 200:
                data = response.json()
                translated = data.get('responseData', {}).get('translatedText', text)
                return translated
            else:
                return text
                
        except Exception as e:
            logger.error("Error translating to English", error=str(e))
            return text
    
    def normalize_sinhala_text(self, text: str) -> str:
        """Normalize Sinhala text for better processing"""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Normalize common Sinhala punctuation
        text = text.replace('à¥¤', '.')
        text = text.replace('ØŸ', '?')
        
        return text
    
    def extract_sinhala_keywords(self, text: str) -> List[str]:
        """Extract key Sinhala words (basic implementation)"""
        # This is a simplified implementation
        # In production, you'd use a proper Sinhala NLP library
        
        if not self.is_sinhala_text(text):
            return []
        
        # Split by common separators
        words = re.split(r'[\s\u0020\u00A0\u1680\u2000-\u200A\u202F\u205F\u3000]+', text)
        
        # Filter out short words and punctuation
        keywords = [
            word.strip('.,!?;:()[]{}""''') 
            for word in words 
            if len(word) > 2 and self.is_sinhala_text(word)
        ]
        
        return list(set(keywords))  # Remove duplicates