from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field, validator
from typing import List
import logging
from datetime import datetime

# Celery imports
from tasks import process_facial_regions_task

# PostgreSQL cache imports
from cache_service import cache_service
from database import init_database

# Prometheus and Rich logging imports
from metrics import instrumentator, setup_metrics, get_metrics
from rich_logging import setup_rich_logging, log_startup_info

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

# Pydantic models
class Landmark(BaseModel):
    x: float = Field(..., ge=0, description="X coordinate")
    y: float = Field(..., ge=0, description="Y coordinate")

class FacialRequest(BaseModel):
    image: str = Field(..., description="Base64 encoded image")
    landmarks: List[Landmark] = Field(..., min_items=478, max_items=478)
    segmentation_map: str = Field(..., description="Base64 encoded segmentation map")
    
    @validator('landmarks')
    def validate_landmarks_count(cls, v):
        if len(v) != 478:
            raise ValueError(f'Expected exactly 478 landmarks, got {len(v)}')
        return v



# Task-related models
class TaskSubmissionResponse(BaseModel):
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Status message")
    submitted_at: str = Field(..., description="Submission timestamp")
    estimated_completion_time: int = Field(..., description="Estimated completion time in seconds")

class TaskStatusResponse(BaseModel):
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status (PENDING, PROGRESS, SUCCESS, FAILURE)")
    result: dict = Field(None, description="Task result if completed successfully")
    error: dict = Field(None, description="Error information if task failed")
    progress: dict = Field(None, description="Progress information if task is running")
    submitted_at: str = Field(None, description="Task submission timestamp")
    completed_at: str = Field(None, description="Task completion timestamp")
    processing_time_ms: float = Field(None, description="Total processing time in milliseconds")

# Cache-related models
class CacheStatsResponse(BaseModel):
    period_days: int = Field(..., description="Statistics period in days")
    total_requests: int = Field(..., description="Total requests in period")
    cache_hits: int = Field(..., description="Number of cache hits")
    cache_hit_ratio: float = Field(..., description="Cache hit ratio percentage")
    successful_tasks: int = Field(..., description="Successfully completed tasks")
    avg_processing_time_ms: float = Field(..., description="Average processing time")
    total_cached_entries: int = Field(..., description="Total entries in cache")
    cache_efficiency: str = Field(..., description="Cache efficiency rating")

class RecentTaskResponse(BaseModel):
    task_id: str = Field(..., description="Task identifier (first 8 chars)")
    status: str = Field(..., description="Task status")
    submitted_at: str = Field(..., description="Submission timestamp")
    processing_time_ms: float = Field(None, description="Processing time if completed")
    regions_detected: int = Field(None, description="Number of regions detected")
    cache_hits: int = Field(..., description="Number of times served from cache")
    error_type: str = Field(None, description="Error type if failed")



@app.post("/api/v1/frontal/crop/submit", response_model=TaskSubmissionResponse)
async def submit_facial_processing_task(
    request: FacialRequest,
    show_landmarks: bool = Query(False, description="Include landmark points in SVG"),
    region_opacity: float = Query(0.7, ge=0.0, le=1.0, description="Opacity of region masks")
):
    """
    Submit facial image processing task to background queue.
    Returns task ID for polling the result.
    
    Args:
        request: FacialRequest containing image, landmarks, and segmentation map
        show_landmarks: Whether to include landmark points in the SVG
        region_opacity: Opacity level for region masks (0.0 to 1.0)
    
    Returns:
        TaskSubmissionResponse with task ID and submission details
    """
    try:
        logger.info("Submitting new facial region processing task")
        
        # Basic validation - decode base64 headers to ensure they're valid
        try:
            # Just validate the headers without processing the full images
            if ',' in request.image:
                request.image.split(',')[1]
            if ',' in request.segmentation_map:
                request.segmentation_map.split(',')[1]
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="Invalid base64 image data format"
            )
        
        # Submit the task to Celery
        task = process_facial_regions_task.delay(
            request_data=request.dict(),
            show_landmarks=show_landmarks,
            region_opacity=region_opacity
        )
        
        submission_time = datetime.utcnow().isoformat()
        
        logger.info(f"Task {task.id} submitted successfully")
        
        return TaskSubmissionResponse(
            task_id=task.id,
            status="PENDING",
            message="Task submitted successfully and is queued for processing",
            submitted_at=submission_time,
            estimated_completion_time=30  # Estimated 30 seconds
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Task submission error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Task submission error: {str(e)}")

@app.get("/api/v1/frontal/crop/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Poll the status of a facial processing task.
    
    Args:
        task_id: The unique task identifier returned from submit endpoint
    
    Returns:
        TaskStatusResponse with current task status and results if completed
    """
    try:
        logger.info(f"Polling status for task {task_id}")
        
        # Get task result from Celery
        task_result = process_facial_regions_task.AsyncResult(task_id)
        
        response = TaskStatusResponse(
            task_id=task_id,
            status=task_result.status
        )
        
        if task_result.status == 'PENDING':
            response.result = None
            response.error = None
            response.progress = {"message": "Task is queued and waiting to be processed"}
            
        elif task_result.status == 'PROGRESS':
            response.result = None
            response.error = None
            response.progress = task_result.info
            
        elif task_result.status == 'SUCCESS':
            result_data = task_result.result
            response.result = {
                "svg": result_data["svg"],
                "mask_contours": result_data["mask_contours"],
                "regions_detected": result_data["regions_detected"],
                "processing_time_ms": result_data["processing_time_ms"]
            }
            response.error = None
            response.progress = None
            response.completed_at = result_data.get("completed_at")
            response.processing_time_ms = result_data["processing_time_ms"]
            
        elif task_result.status == 'FAILURE':
            response.result = None
            response.error = {
                "message": str(task_result.info),
                "type": "ProcessingError",
                "task_id": task_id
            }
            response.progress = None
            
        else:
            # Handle other statuses
            response.result = None
            response.error = None
            response.progress = {"message": f"Task status: {task_result.status}"}
        
        logger.debug(f"Task {task_id} status: {task_result.status}")
        return response
        
    except Exception as e:
        logger.error(f"Error polling task {task_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"Error retrieving task status: {str(e)}"
        )

@app.get("/api/v1/cache/stats", response_model=CacheStatsResponse)
async def get_cache_stats(days: int = Query(7, ge=1, le=30, description="Number of days for statistics")):
    """
    Get PostgreSQL cache performance statistics.
    
    Args:
        days: Number of days to include in statistics (1-30)
        
    Returns:
        Cache performance metrics including hit ratio, processing times, etc.
    """
    try:
        logger.info(f"Retrieving cache statistics for {days} days")
        stats = cache_service.get_cache_stats(days=days)
        
        if "error" in stats:
            raise HTTPException(status_code=500, detail=stats["error"])
            
        return CacheStatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Cache stats error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cache stats: {str(e)}")

@app.get("/api/v1/cache/recent", response_model=List[RecentTaskResponse])
async def get_recent_tasks(limit: int = Query(10, ge=1, le=50, description="Number of recent tasks to return")):
    """
    Get recent task results from cache for monitoring.
    
    Args:
        limit: Maximum number of tasks to return (1-50)
        
    Returns:
        List of recent task information
    """
    try:
        logger.info(f"Retrieving {limit} recent tasks from cache")
        recent_tasks = cache_service.get_recent_tasks(limit=limit)
        return [RecentTaskResponse(**task) for task in recent_tasks]
        
    except Exception as e:
        logger.error(f"Recent tasks error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to retrieve recent tasks: {str(e)}")

@app.post("/api/v1/cache/cleanup")
async def cleanup_cache():
    """
    Clean up expired cache entries.
    
    Returns:
        Number of entries cleaned up
    """
    try:
        logger.info("Starting cache cleanup")
        deleted_count = cache_service.cleanup_expired_cache()
        
        return {
            "message": "Cache cleanup completed",
            "deleted_entries": deleted_count,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Cache cleanup error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cache cleanup failed: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Facial Region SVG Service",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@app.get("/api/v1/database/health")
async def database_health_check():
    """Database-specific health check."""
    try:
        from database_setup import get_database_stats, test_database_connection
        
        # Test connection
        connection_ok = test_database_connection()
        if not connection_ok:
            raise HTTPException(status_code=503, detail="Database connection failed")
        
        # Get statistics
        stats = get_database_stats()
        
        return {
            "status": "healthy",
            "database_connection": "ok",
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"Database health check failed: {str(e)}"
        )

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