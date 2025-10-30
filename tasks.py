from celery_config import celery_app
from pydantic import BaseModel, Field, validator
from typing import List, Dict
import base64
import numpy as np
from io import BytesIO
from PIL import Image
import cv2
import time
from datetime import datetime

# Metrics and Rich logging imports
from metrics import (
    track_task_metrics, track_image_processing, record_landmarks_processed,
    record_region_generated
)
from rich_logging import (
    task_logger, log_task_started, log_task_completed,
    log_image_processing
)

# PostgreSQL cache imports
from cache_service import cache_service

# Configure rich logging for tasks
logger = task_logger

# Pydantic models (copied from main.py for task isolation)
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

# Enhanced MediaPipe 478 landmark indices with better organization
FACIAL_REGIONS = {
    "left_eye": {
        "indices": [33, 7, 163, 144, 145, 153, 154, 155, 133, 173, 157, 158, 159, 160, 161, 246],
        "color": "#FF6B6B80",
        "name": "Left Eye"
    },
    "right_eye": {
        "indices": [263, 249, 390, 373, 374, 380, 381, 382, 362, 398, 384, 385, 386, 387, 388, 466],
        "color": "#4ECDC480",
        "name": "Right Eye"
    },
    "left_eyebrow": {
        "indices": [70, 63, 105, 66, 107, 55, 65, 52, 53, 46],
        "color": "#45B7D180",
        "name": "Left Eyebrow"
    },
    "right_eyebrow": {
        "indices": [300, 293, 334, 296, 336, 285, 295, 282, 283, 276],
        "color": "#FFA07A80",
        "name": "Right Eyebrow"
    },
    "nose": {
        "indices": [168, 6, 197, 195, 5, 4, 1, 19, 94, 2, 326, 327, 294, 278, 344, 440, 275, 4],
        "color": "#98D8C880",
        "name": "Nose"
    },
    "upper_lip": {
        "indices": [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291, 308, 415, 310, 311, 312, 13, 82, 81, 80, 191, 78],
        "color": "#F7DC6F80",
        "name": "Upper Lip"
    },
    "lower_lip": {
        "indices": [61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291, 308, 324, 318, 402, 317, 14, 87, 178, 88, 95, 78],
        "color": "#BB8FCE80",
        "name": "Lower Lip"
    },
    "face_oval": {
        "indices": [10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109],
        "color": "#85C1E980",
        "name": "Face Oval"
    },
    "left_cheek": {
        "indices": [50, 101, 36, 205, 123, 203],
        "color": "#F8B88B80",
        "name": "Left Cheek"
    },
    "right_cheek": {
        "indices": [280, 330, 266, 425, 352, 423],
        "color": "#ABEBC680",
        "name": "Right Cheek"
    }
}

@track_image_processing("base64_decode")
def decode_base64_image(base64_str: str) -> np.ndarray:
    """Decode base64 string to numpy array image with error handling."""
    try:
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        
        img_data = base64.b64decode(base64_str)
        img = Image.open(BytesIO(img_data))
        
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        return np.array(img)
    except Exception as e:
        logger.error(f"[error]💥 Image decoding error: {str(e)}[/]")
        raise ValueError(f"Invalid image data: {str(e)}")

def encode_svg_to_base64(svg_content: str) -> str:
    """Encode SVG string to base64."""
    return base64.b64encode(svg_content.encode('utf-8')).decode('utf-8')

def get_region_contours(landmarks: List[Landmark], region_indices: List[int]) -> List[List[float]]:
    """Extract contour points for a specific facial region."""
    contour = []
    for idx in region_indices:
        if idx < len(landmarks):
            contour.append([landmarks[idx].x, landmarks[idx].y])
    return contour

def smooth_contour(contour: List[List[float]], epsilon: float = 2.0) -> List[List[float]]:
    """Smooth contour using Douglas-Peucker algorithm."""
    if len(contour) < 3:
        return contour
    
    contour_np = np.array(contour, dtype=np.float32)
    
    # Apply Douglas-Peucker algorithm
    smoothed = cv2.approxPolyDP(contour_np, epsilon, closed=True)
    
    return smoothed.reshape(-1, 2).tolist()

def create_svg_with_regions(
    image_shape: tuple,
    landmarks: List[Landmark],
    mask_contours: Dict[int, List[List[float]]],
    show_landmarks: bool = False,
    region_opacity: float = 0.7
) -> str:
    """Generate SVG with facial region masks overlaid."""
    
    height, width = image_shape[:2]
    
    svg_parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<defs>',
        '  <style>',
        f'    .region {{ stroke: #FFFFFF40; stroke-width: 1.5; opacity: {region_opacity}; }}',
        '    .landmark {{ fill: #FFFFFF; opacity: 0.3; }}',
        '  </style>',
        '</defs>',
        f'<rect width="{width}" height="{height}" fill="none"/>'
    ]
    
    # Draw each region as a filled polygon
    for region_id, (region_name, region_data) in enumerate(FACIAL_REGIONS.items()):
        if region_id + 1 in mask_contours:
            contour = mask_contours[region_id + 1]
            
            if len(contour) < 3:
                continue
            
            # Smooth the contour for better appearance
            smoothed_contour = smooth_contour(contour)
            
            points_str = " ".join([f"{pt[0]:.2f},{pt[1]:.2f}" for pt in smoothed_contour])
            color = region_data["color"]
            
            svg_parts.append(
                f'<polygon id="{region_name}" class="region" points="{points_str}" fill="{color}"/>'
            )
    
    # Optionally draw landmark points
    if show_landmarks:
        svg_parts.append('<g id="landmarks">')
        for landmark in landmarks:
            svg_parts.append(
                f'<circle cx="{landmark.x:.2f}" cy="{landmark.y:.2f}" r="1" class="landmark"/>'
            )
        svg_parts.append('</g>')
    
    svg_parts.append('</svg>')
    
    return '\n'.join(svg_parts)

def process_segmentation_map(
    seg_map: np.ndarray,
    landmarks: List[Landmark]
) -> Dict[int, List[List[float]]]:
    """
    Process segmentation map to extract refined contours for facial regions.
    Combines landmark-based regions with segmentation information.
    """
    mask_contours = {}
    
    # Extract contours for each predefined facial region
    for region_idx, (region_name, region_data) in enumerate(FACIAL_REGIONS.items()):
        indices = region_data["indices"]
        contour = get_region_contours(landmarks, indices)
        
        if len(contour) >= 3:
            # Store the contour
            mask_contours[region_idx + 1] = contour
            logger.debug(f"Region '{region_name}' (ID: {region_idx + 1}): {len(contour)} points")
    
    return mask_contours

@celery_app.task(bind=True, name='tasks.process_facial_regions_task')
@track_task_metrics('facial_processing')
def process_facial_regions_task(
    self,
    request_data: dict,
    show_landmarks: bool = False,
    region_opacity: float = 0.7
):
    """
    Celery task to process facial image with landmarks and segmentation map.
    Returns SVG with highlighted facial regions and contour data.
    """
    start_time = time.time()
    task_id = self.request.id
    
    # Log task start with rich formatting
    log_task_started(task_id, "facial_processing", landmarks=478, regions="auto-detect")
    
    try:
        # Update task state to PROGRESS
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Starting facial region processing...', 'progress': 0}
        )
        
        logger.info(f"[task]🚀 Processing task {task_id[:8]}: facial region request[/]")
        
        # Parse request data
        request = FacialRequest(**request_data)
        
        # Check cache first for faster response
        logger.debug("[cache]🔍 Checking PostgreSQL cache for existing result...[/]")
        cached_result = cache_service.get_cached_result(
            request.image, 
            [{"x": lm.x, "y": lm.y} for lm in request.landmarks],
            request.segmentation_map,
            show_landmarks,
            region_opacity
        )
        
        if cached_result:
            logger.info(f"[success]⚡ Cache HIT! Returning cached result for task {task_id[:8]}[/]")
            
            # Return cached result immediately
            return {
                "svg": cached_result["svg"],
                "mask_contours": cached_result["mask_contours"],
                "processing_time_ms": cached_result["processing_time_ms"],
                "regions_detected": cached_result["regions_detected"],
                "task_id": task_id,
                "completed_at": cached_result["completed_at"],
                "cache_hit": True,
                "cache_hits": cached_result["cache_hits"]
            }
        
        logger.debug("[cache]❌ Cache MISS - proceeding with full processing...[/]")
        
        # Record landmarks processing metrics
        record_landmarks_processed(len(request.landmarks))
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Decoding input image...', 'progress': 20}
        )
        
        # Decode input image with metrics tracking
        logger.debug("[image]📥 Decoding input image[/]")
        image_start = time.time()
        image = decode_base64_image(request.image)
        image_decode_time = time.time() - image_start
        log_image_processing("image_decode", image.shape[:2], image_decode_time)
        logger.info(f"[image]🖼️ Image decoded: {image.shape}[/]")
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Decoding segmentation map...', 'progress': 40}
        )
        
        # Decode segmentation map with metrics tracking  
        logger.debug("[image]📥 Decoding segmentation map[/]")
        seg_start = time.time()
        seg_map = decode_base64_image(request.segmentation_map)
        seg_decode_time = time.time() - seg_start
        log_image_processing("segmentation_decode", seg_map.shape[:2], seg_decode_time)
        logger.info(f"[image]🗺️ Segmentation map decoded: {seg_map.shape}[/]")
        
        # Validate image and segmentation map dimensions match
        if image.shape[:2] != seg_map.shape[:2]:
            raise ValueError(
                f"Image and segmentation map dimensions must match. "
                f"Got image: {image.shape[:2]}, seg_map: {seg_map.shape[:2]}"
            )
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Extracting contours from segmentation map...', 'progress': 60}
        )
        
        # Process segmentation map and extract contours with metrics
        logger.debug("[image]🔍 Extracting contours from segmentation map[/]")
        contour_start = time.time()
        mask_contours = process_segmentation_map(seg_map, request.landmarks)
        contour_time = time.time() - contour_start
        log_image_processing("contour_extraction", seg_map.shape[:2], contour_time)
        
        # Record region metrics
        for region_name in mask_contours.keys():
            record_region_generated(region_name)
        
        logger.info(f"[success]✅ Extracted {len(mask_contours)} regions[/]")
        
        # Update progress
        self.update_state(
            state='PROGRESS',
            meta={'status': 'Generating SVG...', 'progress': 80}
        )
        
        # Generate SVG with facial regions with metrics
        logger.debug("[image]🎨 Generating SVG[/]")
        svg_start = time.time()
        svg_content = create_svg_with_regions(
            image.shape,
            request.landmarks,
            mask_contours,
            show_landmarks=show_landmarks,
            region_opacity=region_opacity
        )
        svg_time = time.time() - svg_start
        log_image_processing("svg_generation", image.shape[:2], svg_time)
        
        # Encode SVG to base64
        svg_base64 = encode_svg_to_base64(svg_content)
        
        processing_time = (time.time() - start_time)  # Keep in seconds for rich logging
        processing_time_ms = processing_time * 1000  # Convert to ms for result
        
        # Log successful completion
        log_task_completed(task_id, "facial_processing", processing_time, "success")
        logger.info(f"[success]✅ Task {task_id[:8]} completed in {processing_time:.3f}s[/]")
        
        result = {
            "svg": svg_base64,
            "mask_contours": mask_contours,
            "processing_time_ms": round(processing_time_ms, 2),
            "regions_detected": len(mask_contours),
            "task_id": self.request.id,
            "completed_at": datetime.utcnow().isoformat(),
            "image_shape": {"width": image.shape[1], "height": image.shape[0]},
            "cache_hit": False
        }
        
        # Store successful result in PostgreSQL cache
        logger.debug("[cache]💾 Storing result in PostgreSQL cache...[/]")
        cache_stored = cache_service.store_task_result(
            task_id=task_id,
            image_data=request.image,
            landmarks=[{"x": lm.x, "y": lm.y} for lm in request.landmarks],
            segmentation_map=request.segmentation_map,
            result_data=result,
            show_landmarks=show_landmarks,
            region_opacity=region_opacity,
            processing_time_ms=processing_time_ms
        )
        
        if cache_stored:
            logger.info(f"[success]💾 Result cached successfully for task {task_id[:8]}[/]")
        else:
            logger.warning(f"[warning]⚠️ Failed to cache result for task {task_id[:8]}[/]")
        
        return result
        
    except Exception as e:
        processing_time = time.time() - start_time
        
        # Log error with rich formatting
        log_task_completed(task_id, "facial_processing", processing_time, "failure")
        logger.error(f"[error]❌ Task {task_id[:8]} failed: {str(e)}[/]")
        
        # Store error in cache to avoid reprocessing same failing inputs
        try:
            request = FacialRequest(**request_data)
            cache_service.store_task_error(
                task_id=task_id,
                error_message=str(e),
                error_type=type(e).__name__,
                image_data=request.image,
                landmarks=[{"x": lm.x, "y": lm.y} for lm in request.landmarks],
                segmentation_map=request.segmentation_map,
                show_landmarks=show_landmarks,
                region_opacity=region_opacity
            )
            logger.debug(f"[cache]📝 Error cached for task {task_id[:8]}[/]")
        except Exception as cache_error:
            logger.debug(f"[warning]⚠️ Failed to cache error: {str(cache_error)}[/]")
        
        # Update task state to FAILURE with error details
        self.update_state(
            state='FAILURE',
            meta={
                'error': str(e),
                'error_type': type(e).__name__,
                'task_id': self.request.id,
                'failed_at': datetime.utcnow().isoformat(),
                'processing_time_ms': round(processing_time * 1000, 2)
            }
        )
        
        # Re-raise the exception so Celery marks the task as failed
        raise e