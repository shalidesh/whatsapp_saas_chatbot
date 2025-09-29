# middleware/tenant.py - Complete FastAPI Version

from fastapi import HTTPException, Depends, status, Query, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Optional, List, Dict, Any, Callable
import structlog
import time
import json

from ..models.business import Business
from ..models.user import User
from ..config.database import db_session
from .auth import get_current_user

logger = structlog.get_logger(__name__)

# Core FastAPI Dependencies
async def get_current_business(
    business_id: int,
    current_user: User = Depends(get_current_user)
) -> Business:
    """Get current business and verify user ownership (FastAPI dependency)"""
    try:
        # Verify business access
        business = db_session.query(Business).filter(
            Business.id == business_id,
            Business.user_id == current_user.id,
            Business.is_active == True
        ).first()
        
        if not business:
            logger.warning("Unauthorized business access attempt", 
                         user_id=current_user.id, 
                         business_id=business_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Business not found or access denied"
            )
        
        return business
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in business access verification", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Access verification failed"
        )

# Business Validation Functions
async def validate_business_ownership(business_id: int, user_id: int) -> bool:
    """Validate that a user owns a specific business"""
    try:
        business = db_session.query(Business).filter(
            Business.id == business_id,
            Business.user_id == user_id,
            Business.is_active == True
        ).first()
        
        return business is not None
        
    except Exception as e:
        logger.error("Error validating business ownership", 
                    business_id=business_id, user_id=user_id, error=str(e))
        return False

async def get_user_businesses(user_id: int) -> List[Dict[str, Any]]:
    """Get all businesses owned by a user"""
    try:
        businesses = db_session.query(Business).filter(
            Business.user_id == user_id,
            Business.is_active == True
        ).all()
        
        return [business.to_dict() for business in businesses]
        
    except Exception as e:
        logger.error("Error getting user businesses", user_id=user_id, error=str(e))
        return []

# Business Settings and Configuration
async def get_business_settings(business_id: int) -> Dict[str, Any]:
    """Get business-specific settings and configuration"""
    try:
        business = db_session.query(Business).filter(
            Business.id == business_id,
            Business.is_active == True
        ).first()
        
        if not business:
            return {}
        
        return {
            'business_id': business.id,
            'name': business.name,
            'ai_persona': business.ai_persona,
            'supported_languages': business.supported_languages,
            'default_language': business.default_language,
            'whatsapp_phone_number': business.whatsapp_phone_number,
            'business_category': business.business_category,
            'website_url': business.website_url,
            'description': business.description,
            'created_at': business.created_at.isoformat() if business.created_at else None,
            'updated_at': business.updated_at.isoformat() if business.updated_at else None
        }
        
    except Exception as e:
        logger.error("Error getting business settings", 
                    business_id=business_id, error=str(e))
        return {}

# Query Helper Functions
def filter_by_business(query, model_class, business_id: int):
    """Helper function to filter queries by business_id"""
    if hasattr(model_class, 'business_id'):
        return query.filter(model_class.business_id == business_id)
    return query

def create_tenant_aware_query(model_class, business_id: int):
    """Create a query that's automatically filtered by business_id"""
    query = db_session.query(model_class)
    
    if business_id and hasattr(model_class, 'business_id'):
        query = query.filter(model_class.business_id == business_id)
    
    return query

def isolate_data_by_tenant(query, model_class, business_id: int):
    """Apply tenant isolation to database queries"""
    try:
        if not business_id:
            logger.warning("No business_id available for data isolation")
            return query
        
        # Apply business_id filter if the model has it
        if hasattr(model_class, 'business_id'):
            query = query.filter(model_class.business_id == business_id)
            logger.debug("Applied tenant isolation", 
                        business_id=business_id, 
                        model=model_class.__name__)
        
        return query
        
    except Exception as e:
        logger.error("Error applying tenant isolation", error=str(e))
        return query

# Business Limits and Analytics
async def check_business_limits(business_id: int, limit_type: str) -> Dict[str, Any]:
    """Check if business has reached certain limits (messages, documents, etc.)"""
    try:
        from ..models.message import Message
        from ..models.document import Document
        from datetime import datetime, timedelta
        
        # Define limits (can be moved to configuration)
        limits = {
            'messages_per_day': 1000,
            'documents_total': 50,
            'api_calls_per_hour': 100,
            'messages_per_hour': 50,
            'storage_mb': 1000
        }
        
        current_time = datetime.utcnow()
        
        if limit_type == 'messages_per_day':
            start_of_day = current_time.replace(hour=0, minute=0, second=0, microsecond=0)
            count = db_session.query(Message).filter(
                Message.business_id == business_id,
                Message.created_at >= start_of_day
            ).count()
            
            return {
                'limit_type': limit_type,
                'current_count': count,
                'limit': limits[limit_type],
                'exceeded': count >= limits[limit_type],
                'percentage_used': round((count / limits[limit_type]) * 100, 2)
            }
        
        elif limit_type == 'messages_per_hour':
            start_of_hour = current_time.replace(minute=0, second=0, microsecond=0)
            count = db_session.query(Message).filter(
                Message.business_id == business_id,
                Message.created_at >= start_of_hour
            ).count()
            
            return {
                'limit_type': limit_type,
                'current_count': count,
                'limit': limits[limit_type],
                'exceeded': count >= limits[limit_type],
                'percentage_used': round((count / limits[limit_type]) * 100, 2)
            }
        
        elif limit_type == 'documents_total':
            count = db_session.query(Document).filter(
                Document.business_id == business_id,
                Document.is_active == True
            ).count()
            
            return {
                'limit_type': limit_type,
                'current_count': count,
                'limit': limits[limit_type],
                'exceeded': count >= limits[limit_type],
                'percentage_used': round((count / limits[limit_type]) * 100, 2)
            }
        
        return {
            'limit_type': limit_type, 
            'exceeded': False,
            'current_count': 0,
            'limit': limits.get(limit_type, 0),
            'percentage_used': 0
        }
        
    except Exception as e:
        logger.error("Error checking business limits", 
                    business_id=business_id, limit_type=limit_type, error=str(e))
        return {
            'limit_type': limit_type, 
            'exceeded': False, 
            'error': str(e),
            'current_count': 0,
            'limit': 0,
            'percentage_used': 0
        }

async def get_business_analytics_context(business_id: int) -> Dict[str, Any]:
    """Get analytics context for a business (for multi-tenant analytics)"""
    try:
        business = db_session.query(Business).filter(
            Business.id == business_id,
            Business.is_active == True
        ).first()
        
        if not business:
            return {}
        
        # Get basic business metrics
        from ..models.message import Message
        from ..models.document import Document
        from datetime import datetime, timedelta
        
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        
        # Message counts
        message_count_30d = db_session.query(Message).filter(
            Message.business_id == business_id,
            Message.created_at >= thirty_days_ago
        ).count()
        
        message_count_7d = db_session.query(Message).filter(
            Message.business_id == business_id,
            Message.created_at >= seven_days_ago
        ).count()
        
        # Document count
        document_count = db_session.query(Document).filter(
            Document.business_id == business_id,
            Document.is_active == True
        ).count()
        
        return {
            'business_id': business_id,
            'business_name': business.name,
            'business_category': business.business_category,
            'message_count_30d': message_count_30d,
            'message_count_7d': message_count_7d,
            'document_count': document_count,
            'created_at': business.created_at.isoformat() if business.created_at else None,
            'user_id': business.user_id,
            'supported_languages': business.supported_languages,
            'default_language': business.default_language
        }
        
    except Exception as e:
        logger.error("Error getting business analytics context", 
                    business_id=business_id, error=str(e))
        return {}

# Dependency Factories for Business Limits
def require_business_limit_check(limit_type: str):
    """Dependency factory for checking business limits"""
    async def check_limits(
        business_id: int,
        current_user: User = Depends(get_current_user)
    ) -> Business:
        # Verify business ownership first
        business = await get_current_business(business_id, current_user)
        
        # Check limits
        limit_check = await check_business_limits(business.id, limit_type)
        if limit_check.get('exceeded'):
            logger.warning("Business limit exceeded", 
                         business_id=business.id, 
                         limit_type=limit_type,
                         current_count=limit_check.get('current_count'),
                         limit=limit_check.get('limit'))
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    'error': f'Business limit exceeded for {limit_type}',
                    'limit_info': limit_check
                },
                headers={'Retry-After': '3600'}  # 1 hour
            )
        
        return business
    
    return check_limits

# Advanced Business Access Dependencies
def require_business_access_with_permissions(required_permissions: List[str] = None):
    """Dependency factory for business access with specific permissions"""
    async def check_access_and_permissions(
        business_id: int,
        current_user: User = Depends(get_current_user)
    ) -> Business:
        # Get business and verify ownership
        business = await get_current_business(business_id, current_user)
        
        # Check permissions if specified
        if required_permissions:
            # This would integrate with a role-based access control system
            user_permissions = getattr(current_user, 'permissions', [])
            
            for permission in required_permissions:
                if permission not in user_permissions:
                    logger.warning("Insufficient permissions", 
                                 user_id=current_user.id,
                                 business_id=business_id,
                                 required_permission=permission)
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Insufficient permissions: {permission} required"
                    )
        
        return business
    
    return check_access_and_permissions

# FastAPI Middleware for Tenant Context
class TenantLoggingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for tenant-aware request logging"""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = structlog.get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Extract business_id and user info from request
        business_id = None
        user_id = None
        
        try:
            # Try to get business_id from query params
            if request.method == "GET":
                business_id = request.query_params.get("business_id")
            
            # Try to get from request body for POST/PUT requests
            elif request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    try:
                        data = json.loads(body)
                        business_id = data.get("business_id")
                    except json.JSONDecodeError:
                        pass
                    
                    # Re-create request with body for downstream handlers
                    async def receive():
                        return {"type": "http.request", "body": body}
                    request._receive = receive
            
            # Try to extract user_id from JWT token
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                try:
                    import jwt
                    from ..config.settings import config
                    token = auth_header.split(" ")[1]
                    payload = jwt.decode(token, config.JWT_SECRET_KEY, algorithms=['HS256'])
                    user_id = payload.get('user_id')
                except:
                    pass
        
        except Exception as e:
            self.logger.debug("Error extracting request context", error=str(e))
        
        # Process request
        try:
            response = await call_next(request)
        except Exception as e:
            # Log errors with context
            process_time = time.time() - start_time
            self.logger.error("Request failed", 
                            method=request.method,
                            path=str(request.url.path),
                            business_id=business_id,
                            user_id=user_id,
                            process_time=round(process_time, 4),
                            error=str(e))
            raise
        
        # Log successful request completion
        process_time = time.time() - start_time
        
        log_data = {
            "method": request.method,
            "path": str(request.url.path),
            "status_code": response.status_code,
            "process_time": round(process_time, 4),
            "business_id": business_id,
            "user_id": user_id,
            "user_agent": request.headers.get("user-agent", "")[:100]
        }
        
        if response.status_code >= 400:
            self.logger.warning("Request completed with error", **log_data)
        else:
            self.logger.info("Request completed", **log_data)
        
        return response

class TenantContextMiddleware(BaseHTTPMiddleware):
    """Middleware to set tenant context for the request"""
    
    def __init__(self, app):
        super().__init__(app)
        self.logger = structlog.get_logger(__name__)
    
    async def dispatch(self, request: Request, call_next):
        # Set tenant context in request state
        business_id = None
        
        try:
            if request.method == "GET":
                business_id = request.query_params.get("business_id")
            elif request.method in ["POST", "PUT", "PATCH"]:
                body = await request.body()
                if body:
                    try:
                        data = json.loads(body)
                        business_id = data.get("business_id")
                    except json.JSONDecodeError:
                        pass
                    
                    # Re-create request for downstream
                    async def receive():
                        return {"type": "http.request", "body": body}
                    request._receive = receive
            
            if business_id:
                request.state.business_id = int(business_id)
                self.logger.debug("Tenant context set", business_id=business_id)
        
        except Exception as e:
            self.logger.debug("Error setting tenant context", error=str(e))
        
        response = await call_next(request)
        return response

# Utility Functions for Activity Logging
async def log_tenant_activity(
    activity_type: str, 
    business_id: int,
    user_id: int,
    details: Dict[str, Any] = None,
    request_path: str = None,
    ip_address: str = None
):
    """Log tenant-specific activity for audit purposes"""
    try:
        log_data = {
            'activity_type': activity_type,
            'business_id': business_id,
            'user_id': user_id,
            'details': details or {},
            'request_path': request_path,
            'ip_address': ip_address,
            'timestamp': time.time()
        }
        
        logger.info("Tenant activity logged", **log_data)
        
        # Here you could also store audit logs in database
        # await store_audit_log(log_data)
        
    except Exception as e:
        logger.error("Error logging tenant activity", 
                    activity_type=activity_type, 
                    business_id=business_id,
                    error=str(e))

# Business Metrics and Health Check
async def get_business_health_metrics(business_id: int) -> Dict[str, Any]:
    """Get business health and usage metrics"""
    try:
        from datetime import datetime, timedelta
        
        # Check multiple limits
        limits_to_check = ['messages_per_day', 'messages_per_hour', 'documents_total']
        limit_results = {}
        
        for limit_type in limits_to_check:
            limit_results[limit_type] = await check_business_limits(business_id, limit_type)
        
        # Calculate overall health score
        health_score = 100
        warnings = []
        
        for limit_type, result in limit_results.items():
            percentage = result.get('percentage_used', 0)
            if percentage >= 90:
                health_score -= 30
                warnings.append(f"{limit_type} at {percentage}% capacity")
            elif percentage >= 75:
                health_score -= 15
                warnings.append(f"{limit_type} at {percentage}% capacity")
        
        # Get business settings
        settings = await get_business_settings(business_id)
        
        return {
            'business_id': business_id,
            'health_score': max(0, health_score),
            'status': 'healthy' if health_score >= 80 else 'warning' if health_score >= 50 else 'critical',
            'warnings': warnings,
            'limits': limit_results,
            'last_checked': datetime.utcnow().isoformat(),
            'business_active': bool(settings)
        }
        
    except Exception as e:
        logger.error("Error getting business health metrics", 
                    business_id=business_id, error=str(e))
        return {
            'business_id': business_id,
            'health_score': 0,
            'status': 'error',
            'error': str(e)
        }

# Context Managers for Tenant Operations
class TenantContext:
    """Context manager for tenant-aware operations"""
    
    def __init__(self, business_id: int):
        self.business_id = business_id
        self.business = None
        
    async def __aenter__(self):
        try:
            self.business = db_session.query(Business).filter(
                Business.id == self.business_id,
                Business.is_active == True
            ).first()
            
            if not self.business:
                raise ValueError(f"Business {self.business_id} not found")
            
            return self
        
        except Exception as e:
            logger.error("Error entering tenant context", 
                        business_id=self.business_id, error=str(e))
            raise
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Cleanup operations if needed
        pass
    
    def get_business(self) -> Business:
        return self.business
    
    def filter_query(self, query, model_class):
        """Filter query by tenant"""
        return filter_by_business(query, model_class, self.business_id)

# Export all functions for use in other modules
__all__ = [
    'get_current_business',
    'validate_business_ownership',
    'get_user_businesses',
    'get_business_settings',
    'filter_by_business',
    'create_tenant_aware_query',
    'isolate_data_by_tenant',
    'check_business_limits',
    'get_business_analytics_context',
    'require_business_limit_check',
    'require_business_access_with_permissions',
    'TenantLoggingMiddleware',
    'TenantContextMiddleware',
    'log_tenant_activity',
    'get_business_health_metrics',
    'TenantContext'
]