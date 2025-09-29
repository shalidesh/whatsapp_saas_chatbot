# Updated api/__init__.py for FastAPI

from .auth.routes import auth_router
from .dashboard.routes import dashboard_router
from .whatsapp.webhook import whatsapp_router
from .ai.agent import ai_router

__all__ = ['auth_router', 'dashboard_router', 'whatsapp_router', 'ai_router']