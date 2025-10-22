from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from .config.settings import config
from .config.database import init_db, close_db, db_session
from .utils.logging import configure_logging, FastAPILoggingMiddleware

# Import routers (converted from blueprints)
from .api.auth.routes import auth_router
from .api.dashboard.routes import dashboard_router  
from .api.whatsapp.webhook import whatsapp_router
from .api.ai.agent import ai_router

from .middleware.tenant import TenantLoggingMiddleware

from .utils.error_handlers import register_exception_handlers
from .utils.logging import FastAPILoggingMiddleware  
from .utils.metrics import MetricsMiddleware

logger = structlog.get_logger(__name__)

def create_app():
    """Application factory for FastAPI"""
    
    # Configure logging first
    configure_logging()
    
    # Create FastAPI app
    app = FastAPI(
        title="WhatsApp AI SaaS",
        description="AI-powered WhatsApp business automation",
        version="1.0.0",
        debug=config.DEBUG
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://192.168.8.194:3000", "https://yourdomain.com"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    

    # Add request logging middleware
    app.add_middleware(FastAPILoggingMiddleware)
    app.add_middleware(MetricsMiddleware)
    app.add_middleware(TenantLoggingMiddleware)


    register_exception_handlers(app)
    
    # Initialize database on startup
    @app.on_event("startup")
    async def startup_event():
        init_db()
        logger.info("Database initialized")
    
    # Cleanup on shutdown
    @app.on_event("shutdown")
    async def shutdown_event():
        close_db()
        logger.info("Database connections closed")
    
    # Register routers (equivalent to Flask blueprints)
    app.include_router(auth_router, prefix="/api/auth", tags=["Authentication"])
    app.include_router(dashboard_router, prefix="/api/dashboard", tags=["Dashboard"])
    app.include_router(whatsapp_router, prefix="/api/whatsapp", tags=["WhatsApp"])
    app.include_router(ai_router, prefix="/api/ai", tags=["AI Agent"])
    
    # Health check endpoint
    @app.get("/health", tags=["Health"])
    async def health_check():
        return {"status": "healthy", "service": "whatsapp-ai-saas"}
    
    # Global exception handlers
    @app.exception_handler(404)
    async def not_found_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=404,
            content={"error": "Not found"}
        )
    
    @app.exception_handler(500)
    async def internal_error_handler(request: Request, exc: Exception):
        db_session.rollback()
        logger.error("Internal server error", error=str(exc))
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )
    
    # General exception handler
    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        db_session.rollback()
        logger.error("Unhandled exception", error=str(exc), path=str(request.url))
        return JSONResponse(
            status_code=500,
            content={"error": "An unexpected error occurred"}
        )
    
    logger.info("FastAPI application created successfully")
    return app