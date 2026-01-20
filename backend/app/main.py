"""
XenFlow Mailer - Main FastAPI Application
Enterprise Email Automation System
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import time

from app.config import get_settings
from app.database import init_db
from app.api import api_router
from app.utils.logger import setup_logging, get_logger

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    setup_logging()
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    
    # Initialize database
    init_db()
    logger.info("Database initialized")
    
    yield
    
    # Shutdown
    logger.info("Shutting down XenFlow Mailer")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    XenFlow Mailer - Enterprise Email Automation System
    
    A production-safe, reputation-aware, automated email outreach system
    that prioritizes inbox placement and sender reputation.
    
    ## Features
    
    - **Personalized Outreach**: Dynamic template rendering with placeholders
    - **Automated Follow-ups**: Intelligent follow-up scheduling
    - **Provider Agnostic**: Gmail, Outlook, or any SMTP server
    - **Safety First**: Rate limiting, warmup, bounce handling
    - **Full Audit Trail**: Complete email logging
    
    ## Safety Features
    
    - Automatic sender warmup
    - Bounce and complaint monitoring
    - Suppression list management
    - Rate limiting at multiple levels
    """,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request timing middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred"}
    )


# Include API routes
app.include_router(api_router, prefix=settings.API_PREFIX)


# Health check endpoints
@app.get("/health")
async def health_check():
    """Basic health check."""
    return {"status": "healthy", "version": settings.APP_VERSION}


@app.get("/health/ready")
async def readiness_check():
    """Readiness check including dependencies."""
    from app.database import engine
    
    checks = {
        "database": False,
        "redis": False
    }
    
    # Check database
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        checks["database"] = True
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
    
    # Check Redis
    try:
        import redis
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        checks["redis"] = True
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
    
    all_healthy = all(checks.values())
    
    return {
        "status": "ready" if all_healthy else "degraded",
        "checks": checks
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/api/docs",
        "health": "/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )

