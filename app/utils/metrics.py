from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import structlog
import time
from functools import wraps

logger = structlog.get_logger(__name__)

# Metrics
REQUEST_COUNT = Counter(
    'whatsapp_saas_requests_total',
    'Total number of HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_DURATION = Histogram(
    'whatsapp_saas_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

MESSAGE_PROCESSING_DURATION = Histogram(
    'whatsapp_saas_message_processing_duration_seconds',
    'Message processing duration in seconds',
    ['business_id']
)

ACTIVE_USERS = Gauge(
    'whatsapp_saas_active_users',
    'Number of active users'
)

VECTOR_SEARCH_DURATION = Histogram(
    'whatsapp_saas_vector_search_duration_seconds',
    'Vector search duration in seconds',
    ['business_id']
)

AI_CONFIDENCE_SCORE = Histogram(
    'whatsapp_saas_ai_confidence_score',
    'AI response confidence scores',
    ['business_id'],
    buckets=[0, 20, 40, 60, 80, 100]
)

class MetricsMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware to track request metrics"""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        method = request.method
        path = request.url.path
        
        # Get route pattern instead of actual path for better grouping
        endpoint = path
        if hasattr(request, 'route') and request.route:
            endpoint = request.route.path
        
        try:
            response = await call_next(request)
            
            # Track successful requests
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=response.status_code
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(time.time() - start_time)
            
            return response
            
        except Exception as e:
            # Track failed requests
            REQUEST_COUNT.labels(
                method=method,
                endpoint=endpoint,
                status=500
            ).inc()
            
            REQUEST_DURATION.labels(
                method=method,
                endpoint=endpoint
            ).observe(time.time() - start_time)
            
            raise

def track_request_metrics(f):
    """Decorator to track request metrics for individual functions"""
    @wraps(f)
    async def decorated_function(*args, **kwargs):
        start_time = time.time()
        function_name = f.__name__
        
        try:
            response = await f(*args, **kwargs)
            
            # Track timing for function execution
            REQUEST_DURATION.labels(
                method="FUNCTION",
                endpoint=function_name
            ).observe(time.time() - start_time)
            
            return response
            
        except Exception as e:
            logger.error("Function execution failed", 
                        function=function_name, 
                        error=str(e))
            raise
    
    return decorated_function

def track_message_processing(business_id: str, duration: float):
    """Track message processing duration"""
    MESSAGE_PROCESSING_DURATION.labels(business_id=business_id).observe(duration)

def track_vector_search(business_id: str, duration: float):
    """Track vector search duration"""
    VECTOR_SEARCH_DURATION.labels(business_id=business_id).observe(duration)

def track_ai_confidence(business_id: str, confidence: float):
    """Track AI confidence scores"""
    AI_CONFIDENCE_SCORE.labels(business_id=business_id).observe(confidence)

async def get_metrics():
    """Get Prometheus metrics endpoint"""
    return Response(
        content=generate_latest(),
        media_type='text/plain'
    )