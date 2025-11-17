"""Facial Region SVG Service - Main FastAPI application."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
import logging

# Import database initialization
from app.database import init_database

# Import metrics and logging
from app.monitoring import instrumentator, setup_metrics, get_metrics
from app.monitoring import setup_rich_logging, log_startup_info

# Import API routes
from app.api.routes import router

# Setup Rich logging
logger = setup_rich_logging(level=logging.INFO)

# Setup metrics
setup_metrics()

app = FastAPI(
    title="Facial Region SVG Service",
    description="Processes facial landmarks and segmentation maps to generate SVG masks",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Prometheus metrics
instrumentator.instrument(app).expose(app)

# Include API routes
app.include_router(router)


@app.get("/metrics", response_class=PlainTextResponse)
async def get_prometheus_metrics():
    """Expose Prometheus metrics."""
    return get_metrics()


@app.on_event("startup")
async def startup_event():
    """Initialize database and display startup information with rich formatting."""
    # Initialize PostgreSQL database
    try:
        logger.info("[database]🐘 Initializing PostgreSQL database...[/]")
        init_database()
        logger.info("[success]✅ Database initialized successfully[/]")
    except Exception as e:
        logger.error(f"[error]❌ Database initialization failed: {str(e)}[/]")
        # Don't crash the app, just log the error
    
    # Display startup information
    log_startup_info(
        app_name="Facial Region SVG Service",
        version="1.0.0",
        host="0.0.0.0",
        port=8000
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
        access_log=True
    )
