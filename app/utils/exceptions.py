"""Custom exception classes"""

class WhatsAppSaaSException(Exception):
    """Base exception for WhatsApp SaaS application"""
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)

class ValidationError(WhatsAppSaaSException):
    """Raised when input validation fails"""
    pass

class AuthenticationError(WhatsAppSaaSException):
    """Raised when authentication fails"""
    pass

class AuthorizationError(WhatsAppSaaSException):
    """Raised when user lacks permission"""
    pass

class BusinessNotFoundError(WhatsAppSaaSException):
    """Raised when business is not found"""
    pass

class DocumentProcessingError(WhatsAppSaaSException):
    """Raised when document processing fails"""
    pass

class VectorSearchError(WhatsAppSaaSException):
    """Raised when vector search fails"""
    pass

class AIProcessingError(WhatsAppSaaSException):
    """Raised when AI processing fails"""
    pass

class WhatsAppAPIError(WhatsAppSaaSException):
    """Raised when WhatsApp API calls fail"""
    pass
