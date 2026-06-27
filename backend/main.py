"""
FastAPI Email Server Application
"""
import os
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from app.config import get_settings
from app.api import contacts, templates, emails, tracking, uploads, rate_limit
from app.data.redis_client import init_redis, close_redis
from app.services.email_service import process_scheduled_emails
from app.middleware.error_handler import CustomException, NotFoundException, BadRequestException, ConflictException

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting application...")
    await init_redis()
    
    # Start background task for processing scheduled emails
    asyncio.create_task(background_email_scheduler())
    
    yield
    
    # Shutdown
    logger.info("Shutting down application...")
    await close_redis()

# Create FastAPI app
app = FastAPI(
    title="Email Server API",
    description="Email server with FastAPI, Redis, and AWS SES integration",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add exception handlers
@app.exception_handler(CustomException)
async def custom_exception_handler(request: Request, exc: CustomException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )

@app.exception_handler(NotFoundException)
async def not_found_exception_handler(request: Request, exc: NotFoundException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )

@app.exception_handler(BadRequestException)
async def bad_request_exception_handler(request: Request, exc: BadRequestException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )

@app.exception_handler(ConflictException)
async def conflict_exception_handler(request: Request, exc: ConflictException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.message}
    )

# Include API routers
app.include_router(contacts.router, prefix="/api/contacts", tags=["contacts"])
app.include_router(templates.router, prefix="/api/templates", tags=["templates"])
app.include_router(emails.router, prefix="/api/emails", tags=["emails"])
app.include_router(tracking.router, prefix="/api/track", tags=["tracking"])
app.include_router(uploads.router, prefix="/api/uploads", tags=["uploads"])
app.include_router(rate_limit.router, prefix="/api/rate-limit", tags=["rate-limit"])

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "Email Server API is running", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}

async def background_email_scheduler():
    """Background task to process scheduled emails every 30 seconds"""
    while True:
        try:
            await process_scheduled_emails()
        except Exception as e:
            logger.error(f"Error in email scheduler: {e}")
        await asyncio.sleep(30)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=settings.node_env == "development",
        log_level="info"
    )