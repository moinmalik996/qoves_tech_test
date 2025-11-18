"""Celery task processing for facial region extraction."""
from celery import Task
from typing import Dict, List

from app.core.celery_app import celery_app
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
    segmentation_map: Dict[str, List[int]] = None,
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
        segmentation_map: Custom region mapping (dict of region_name -> landmark indices)
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
        
        # Use custom segmentation_map if provided, otherwise use default MEDIAPIPE_FACE_REGIONS
        facial_regions = segmentation_map if segmentation_map else MEDIAPIPE_FACE_REGIONS
        
        # Generate region colors - use defaults or create colors for custom regions
        if segmentation_map:
            # For custom regions, use default purple color or map to existing colors
            region_colors = {}
            for region_name in segmentation_map.keys():
                # Try to match with default colors, otherwise use purple
                region_colors[region_name] = DEFAULT_REGION_COLORS.get(region_name, '#B695C0')
        else:
            region_colors = DEFAULT_REGION_COLORS
        
        # Generate SVG mask overlay with regions
        # Following the exact structure from the provided script
        svg_content = generate_svg_mask_overlay(
            dimensions=dimensions,
            landmarks=landmark_points,
            image_base64=image_base64,
            facial_regions=facial_regions,
            region_colors=region_colors,
            region_opacity={region: region_opacity for region in facial_regions.keys()},
            show_labels=show_labels,
            stroke_width=stroke_width
        )
        
        # Encode SVG to base64
        svg_base64 = encode_svg_to_base64(svg_content)
        
        # Extract region contours using the actual facial_regions (custom or default)
        region_data = {}
        for region_name, indices in facial_regions.items():
            contours = get_region_contours(landmark_points, indices)
            region_data[region_name] = contours
        
        result = {
            'status': 'completed',
            'svg_base64': svg_base64,
            'region_data': region_data
        }
        
        # Cache the result with perceptual hashing
        try:
            from app.services.cache import cache_service
            
            success = cache_service.store_task_result_with_phash(
                task_id=task_id,
                image_base64=image_base64,
                landmarks=landmarks,
                result_data=result,
                show_labels=show_labels,
                region_opacity=region_opacity,
                stroke_width=stroke_width,
                processing_time_ms=0.0  # Can add timing later
            )
            
            if success:
                logger.info(f"[Task {task_id}] Result cached with perceptual hash")
            else:
                logger.warning(f"[Task {task_id}] Failed to cache result")
            
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
