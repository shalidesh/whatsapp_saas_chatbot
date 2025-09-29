#!/usr/bin/env python3
"""
WhatsApp AI SaaS Application Entry Point - FastAPI Version
"""

import uvicorn
from app import create_app
from app.config.settings import config

app = create_app()

if __name__ == '__main__':
    uvicorn.run(
        "run:app",  # module:app_instance
        host='0.0.0.0',
        port=5000,
        reload=config.DEBUG,  # Use reload instead of debug for FastAPI
        log_level="info" if not config.DEBUG else "debug"
    )