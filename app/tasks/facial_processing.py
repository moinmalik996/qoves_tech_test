"""Celery task processing for facial region extraction."""
from celery import Task
from typing import Dict, List

from app.core.celery_app import celery_app
from app.database.models import TaskResult
from app.database.connection import SessionLocal
from app.database.utils import generate_cache_key
from app.core.config import MEDIAPIPE_FACE_REGIONS, DEFAULT_REGION_COLORS
from app.utils.image_processing import encode_svg_to_base64, get_region_contours
from app.utils.svg_generation import generate_svg_mask_overlay
from app.monitoring import task_counter, get_logger

logger = get_logger()


class CallbackTask(Task):
    """Task that supports completion callbacks."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Called when task completes successfully."""
        if 'callback_url' in kwargs and kwargs['callback_url']:
            # Here you would implement HTTP callback
            # For now, just log it
            logger.info(f"Task {task_id} completed, callback URL: {kwargs['callback_url']}")


@celery_app.task(
    bind=True,
    base=CallbackTask,
    name='tasks.process_facial_regions_task',
    max_retries=3,
    default_retry_delay=60
)
def process_facial_regions_task(
    self,
    image_base64: str,
    landmarks: List[Dict],
    dimensions: List[int],
    show_labels: bool = True,
    region_opacity: float = 0.65,
    stroke_width: int = 0,
    **kwargs
) -> Dict:
    """
    Process facial regions from MediaPipe landmarks and generate SVG masks.
    
    Args:
        image_base64: Base64 encoded image
        landmarks: List of 478 MediaPipe facial landmarks
        dimensions: [width, height] of the image
        show_labels: Whether to show region labels (numbers)
        region_opacity: Opacity level for region masks (0.0 to 1.0)
        stroke_width: Width of stroke around regions (0 for no stroke)
        **kwargs: Additional parameters (callback_url, etc.)
    
    Returns:
        Dict with status, svg_base64, and region_data
    """
    task_counter.labels(task_type='process_facial_regions', status='started').inc()
    
    task_id = self.request.id
    logger.info(f"[Task {task_id}] Starting facial region processing")
    
    try:
        # Validate input
        if len(landmarks) < 478:
            raise ValueError(f"Expected 478 landmarks, got {len(landmarks)}")
        
        # Convert landmarks to expected format
        landmark_points = [
            {"x": lm.get("x", 0.0), "y": lm.get("y", 0.0)}
            for lm in landmarks
        ]
        
        # Generate SVG mask overlay with MediaPipe regions
        # Following the exact structure from the provided script
        svg_content = generate_svg_mask_overlay(
            dimensions=dimensions,
            landmarks=landmark_points,
            image_base64=image_base64,
            facial_regions=MEDIAPIPE_FACE_REGIONS,
            region_colors=DEFAULT_REGION_COLORS,
            region_opacity={region: region_opacity for region in MEDIAPIPE_FACE_REGIONS.keys()},
            show_labels=show_labels,
            stroke_width=stroke_width
        )
        
        # Encode SVG to base64
        svg_base64 = encode_svg_to_base64(svg_content)
        
        # Extract region contours
        region_data = {}
        for region_name, indices in MEDIAPIPE_FACE_REGIONS.items():
            contours = get_region_contours(landmark_points, indices)
            region_data[region_name] = contours
        
        result = {
            'status': 'completed',
            'svg_base64': svg_base64,
            'region_data': region_data
        }
        
        # Cache the result in database
        try:
            cache_key = generate_cache_key(landmarks, dimensions)
            db = SessionLocal()
            
            # Check if already cached
            existing = db.query(TaskResult).filter_by(cache_key=cache_key).first()
            if existing:
                logger.info(f"[Task {task_id}] Updating existing cache entry")
                existing.result = result
                existing.task_id = task_id
            else:
                logger.info(f"[Task {task_id}] Creating new cache entry")
                task_result = TaskResult(
                    task_id=task_id,
                    cache_key=cache_key,
                    result=result
                )
                db.add(task_result)
            
            db.commit()
            db.close()
            
        except Exception as cache_error:
            logger.error(f"[Task {task_id}] Cache storage failed: {cache_error}")
            # Don't fail the task if caching fails
        
        task_counter.labels(task_type='process_facial_regions', status='success').inc()
        logger.info(f"[Task {task_id}] Successfully completed facial region processing")
        
        return result
        
    except Exception as e:
        task_counter.labels(task_type='process_facial_regions', status='failed').inc()
        logger.error(f"[Task {task_id}] Failed: {str(e)}")
        
        # Retry on failure
        try:
            raise self.retry(exc=e)
        except Exception:
            logger.error(f"[Task {task_id}] Max retries exceeded")
            return {
                'status': 'failed',
                'error': str(e)
            }
