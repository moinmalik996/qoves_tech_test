"""API route handlers."""
from fastapi import APIRouter, HTTPException, Query
from typing import List
from datetime import datetime

from app.utils.image_processing import decode_base64_image

from app.models.schemas import (
    FacialRequest,
    TaskSubmissionResponse,
    TaskStatusResponse,
    CacheStatsResponse,
    RecentTaskResponse
)
from app.tasks.facial_processing import process_facial_regions_task
from app.services import cache_service
from app.database import get_database_stats, test_db_conn as test_database_connection
from app.monitoring import get_logger

logger = get_logger()

router = APIRouter()


@router.post("/api/v1/frontal/crop/submit", response_model=TaskSubmissionResponse)
async def submit_facial_processing_task_async(
    request: FacialRequest,
    show_labels: bool = Query(True, description="Show region labels (numbers) in SVG"),
    region_opacity: float = Query(0.65, ge=0.0, le=1.0, description="Opacity of region masks"),
    stroke_width: int = Query(0, ge=0, description="Width of stroke around regions")
):
    """
    Submit facial image processing task to background queue (async version).
    Returns task ID for polling the result.
    
    Args:
        request: FacialRequest containing image, landmarks, and segmentation map
        show_labels: Whether to show region labels (numbers) in the SVG
        region_opacity: Opacity level for region masks (0.0 to 1.0)
        stroke_width: Width of stroke around regions (0 for no stroke)
    
    Returns:
        TaskSubmissionResponse with task ID and submission details
    """
    try:
        logger.info("Submitting new facial region processing task")
        
        # Decode image to extract dimensions
        try:
            img_array = decode_base64_image(request.image)
            dimensions = [img_array.shape[1], img_array.shape[0]]  # [width, height]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid image data: {str(e)}")
        
        # Convert landmarks to dict format
        landmarks = [{"x": lm.x, "y": lm.y} for lm in request.landmarks]
        
        # Submit the task to Celery with optional parameters
        task = process_facial_regions_task.delay(
            image_base64=request.image,
            landmarks=landmarks,
            dimensions=dimensions,
            show_labels=show_labels,
            region_opacity=region_opacity,
            stroke_width=stroke_width
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


@router.get("/api/v1/frontal/crop/status/{task_id}", response_model=TaskStatusResponse)
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
            response.result = result_data
            response.error = None
            response.progress = None
            response.completed_at = result_data.get("completed_at")
            response.processing_time_ms = result_data.get("processing_time_ms")
            
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


@router.get("/api/v1/cache/stats", response_model=CacheStatsResponse)
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


@router.get("/api/v1/cache/recent", response_model=List[RecentTaskResponse])
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


@router.post("/api/v1/cache/cleanup")
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


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "Facial Region SVG Service",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }


@router.get("/api/v1/database/health")
async def database_health_check():
    """Database-specific health check."""
    try:
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
