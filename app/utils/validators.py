import re
from typing import Optional
import validators as external_validators

def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email or len(email) > 255:
        return False
    return external_validators.email(email)

def validate_password(password: str) -> bool:
    """Validate password strength"""
    if not password or len(password) < 8:
        return False
    
    # Check for at least one letter and one number
    has_letter = bool(re.search(r'[a-zA-Z]', password))
    has_number = bool(re.search(r'\d', password))
    
    return has_letter and has_number

def validate_phone(phone: str) -> bool:
    """Validate phone number format"""
    if not phone:
        return True  # Phone is optional
    
    # Remove all non-digits
    digits_only = re.sub(r'\D', '', phone)
    
    # Check if it's between 7 and 15 digits (international standard)
    return 7 <= len(digits_only) <= 15

def validate_url(url: str) -> bool:
    """Validate URL format"""
    if not url:
        return False
    
    # Add protocol if missing
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url
    
    return external_validators.url(url)

def validate_whatsapp_phone(phone: str) -> bool:
    """Validate WhatsApp phone number format"""
    if not phone:
        return False
    
    # WhatsApp phone numbers should be in international format
    # Remove all non-digits
    digits_only = re.sub(r'\D', '', phone)
    
    # Should start with country code and be 10-15 digits
    return 10 <= len(digits_only) <= 15 and not digits_only.startswith('0')

def sanitize_input(text: str, max_length: int = 1000) -> str:
    """Sanitize user input"""
    if not text:
        return ""
    
    # Remove dangerous characters
    sanitized = re.sub(r'[<>"\']', '', text)
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()