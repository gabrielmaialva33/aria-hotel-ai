"""Main FastAPI application for ARIA Hotel AI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from prometheus_client import make_asgi_app

from aria.api.webhooks import whatsapp
from aria.core.config import settings
from aria.core.logging import get_logger
from aria.core.sessions import SessionManager

logger = get_logger(__name__)

# Global session manager
session_manager = SessionManager()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting ARIA Hotel AI", version="0.1.0")
    
    # Connect to Redis
    await session_manager.connect()
    
    # TODO: Initialize other services
    # - Database connections
    # - Background tasks
    # - Agent warmup
    
    yield
    
    # Shutdown
    logger.info("Shutting down ARIA Hotel AI")
    
    # Cleanup
    await session_manager.disconnect()
    
    # TODO: Cleanup other services


# Create FastAPI app
app = FastAPI(
    title="ARIA Hotel AI",
    description="AI-powered multimodal concierge system for hotels",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_debug else None,
    redoc_url="/redoc" if settings.app_debug else None,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.hotelpassarim.com.br", "localhost"]
    )

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include routers
app.include_router(whatsapp.router)

# TODO: Add more routers
# app.include_router(voice.router)
# app.include_router(reservations.router, prefix="/api/v1")
# app.include_router(services.router, prefix="/api/v1")
# app.include_router(payments.router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ARIA Hotel AI",
        "version": "0.1.0",
        "status": "operational",
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "webhooks": {
                "whatsapp": "/webhooks/whatsapp"
            }
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check Redis connection
    redis_healthy = False
    try:
        if session_manager._connected:
            await session_manager.redis.ping()
            redis_healthy = True
    except Exception as e:
        logger.error("Redis health check failed", error=str(e))
    
    # Overall health
    healthy = redis_healthy
    
    return {
        "status": "healthy" if healthy else "unhealthy",
        "checks": {
            "redis": "healthy" if redis_healthy else "unhealthy"
        },
        "version": "0.1.0",
        "environment": settings.app_env
    }


@app.get("/api/v1/stats")
async def get_stats():
    """Get application statistics."""
    active_sessions = await session_manager.get_active_sessions_count()
    
    return {
        "active_sessions": active_sessions,
        "environment": settings.app_env,
        "features": {
            "voice_calls": settings.enable_voice_calls,
            "vision_analysis": settings.enable_vision_analysis,
            "proactive_messaging": settings.enable_proactive_messaging
        }
    }


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc):
    """Handle 404 errors."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not found",
            "message": "The requested resource was not found",
            "path": str(request.url.path)
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """Handle 500 errors."""
    logger.error(
        "Internal server error",
        path=str(request.url.path),
        error=str(exc)
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred"
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "aria.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.app_debug,
        log_level=settings.log_level.lower()
    )
