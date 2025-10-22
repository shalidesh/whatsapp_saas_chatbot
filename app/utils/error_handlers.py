from fastapi import HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

logger = structlog.get_logger(__name__)

class APIError(Exception):
    """Custom API Error for FastAPI"""
    def __init__(self, message: str, status_code: int = 400, details=None):
        super().__init__()
        self.message = message
        self.status_code = status_code
        self.details = details

    def to_dict(self):
        result = {'error': self.message}
        if self.details:
            result.update({'details': self.details})
        return result

class ValidationError(APIError):
    """Validation Error"""
    def __init__(self, message: str, field: str = None):
        super().__init__(message, 400)
        self.field = field

class AuthenticationError(APIError):
    """Authentication Error"""
    def __init__(self, message: str = "Authentication required"):
        super().__init__(message, 401)

class AuthorizationError(APIError):
    """Authorization Error"""
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, 403)

class NotFoundError(APIError):
    """Not Found Error"""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, 404)

class RateLimitError(APIError):
    """Rate Limit Error"""
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, 429)

def register_exception_handlers(app):
    """Register exception handlers with FastAPI app"""
    
    @app.exception_handler(APIError)
    async def handle_api_error(request: Request, exc: APIError):
        logger.error("API Error", 
                    message=exc.message, 
                    status_code=exc.status_code,
                    path=str(request.url))
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )
    
    @app.exception_handler(ValidationError)
    async def handle_validation_error(request: Request, exc: ValidationError):
        logger.warning("Validation Error", 
                      message=exc.message, 
                      field=exc.field,
                      path=str(request.url))
        return JSONResponse(
            status_code=exc.status_code,
            content={
                'error': exc.message,
                'field': exc.field,
                'type': 'validation_error'
            }
        )
    
    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(request: Request, exc: RequestValidationError):
        # Convert validation errors to JSON-serializable format
        errors = exc.errors()
        serializable_errors = []

        for error in errors:
            serializable_error = {}
            for key, value in error.items():
                # Convert bytes to string for JSON serialization
                if isinstance(value, bytes):
                    serializable_error[key] = value.decode('utf-8', errors='replace')
                elif key == 'input' and value is not None:
                    # Handle input field specially - it might contain non-serializable objects
                    try:
                        import json
                        json.dumps(value)
                        serializable_error[key] = value
                    except (TypeError, ValueError):
                        serializable_error[key] = str(value)
                else:
                    serializable_error[key] = value
            serializable_errors.append(serializable_error)

        logger.warning("Request Validation Error",
                      errors=serializable_errors,
                      path=str(request.url))
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                'error': 'Request validation failed',
                'details': serializable_errors,
                'type': 'request_validation_error'
            }
        )
    
    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(request: Request, exc: StarletteHTTPException):
        logger.warning("HTTP Exception", 
                      status_code=exc.status_code, 
                      detail=exc.detail,
                      path=str(request.url))
        return JSONResponse(
            status_code=exc.status_code,
            content={'error': exc.detail}
        )
    
    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        logger.error("Unexpected Error", 
                    error=str(exc), 
                    path=str(request.url),
                    method=request.method)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={'error': 'Internal server error'}
        )
