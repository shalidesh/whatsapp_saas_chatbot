import structlog
import logging
import sys
from datetime import datetime
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response
import time

def configure_logging():
    """Configure structured logging"""
    
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

class FastAPILoggingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to log HTTP requests"""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = structlog.get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract request info
        method = request.method
        path = str(request.url.path)
        query_string = str(request.url.query) if request.url.query else ""
        user_agent = request.headers.get("user-agent", "")
        remote_addr = request.client.host if request.client else "unknown"
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log successful request
            self.logger.info(
                "HTTP request completed",
                method=method,
                path=path,
                query_string=query_string,
                status=response.status_code,
                duration_ms=duration_ms,
                user_agent=user_agent[:100],  # Truncate long user agents
                remote_addr=remote_addr
            )
            
            return response
            
        except Exception as e:
            # Calculate duration for failed requests
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log failed request
            self.logger.error(
                "HTTP request failed",
                method=method,
                path=path,
                query_string=query_string,
                duration_ms=duration_ms,
                error=str(e),
                user_agent=user_agent[:100],
                remote_addr=remote_addr
            )
            
            raise

# Alternative simple logging function for route decorators
def log_request(func):
    """Decorator to log individual route requests"""
    import functools
    
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = structlog.get_logger(__name__)
        start_time = time.time()
        
        try:
            result = await func(*args, **kwargs)
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.info("Route executed successfully",
                       function=func.__name__,
                       duration_ms=duration_ms)
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error("Route execution failed",
                        function=func.__name__,
                        duration_ms=duration_ms,
                        error=str(e))
            raise
    
    return wrapper