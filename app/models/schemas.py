"""Pydantic models for API request/response validation."""
from pydantic import BaseModel, Field, validator
from typing import List


class Landmark(BaseModel):
    """Facial landmark point with x,y coordinates."""
    x: float = Field(..., ge=0, description="X coordinate")
    y: float = Field(..., ge=0, description="Y coordinate")


class FacialRequest(BaseModel):
    """Request model for facial region processing."""
    image: str = Field(..., description="Base64 encoded image")
    landmarks: List[Landmark] = Field(..., min_items=478, max_items=478)
    segmentation_map: str = Field(..., description="Base64 encoded segmentation map")
    
    @validator('landmarks')
    def validate_landmarks_count(cls, v):
        if len(v) != 478:
            raise ValueError(f'Expected exactly 478 landmarks, got {len(v)}')
        return v


class TaskSubmissionResponse(BaseModel):
    """Response model for task submission."""
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status")
    message: str = Field(..., description="Status message")
    submitted_at: str = Field(..., description="Submission timestamp")
    estimated_completion_time: int = Field(..., description="Estimated completion time in seconds")


class TaskStatusResponse(BaseModel):
    """Response model for task status check."""
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field(..., description="Task status (PENDING, PROGRESS, SUCCESS, FAILURE)")
    result: dict = Field(None, description="Task result if completed successfully")
    error: dict = Field(None, description="Error information if task failed")
    progress: dict = Field(None, description="Progress information if task is running")
    submitted_at: str = Field(None, description="Task submission timestamp")
    completed_at: str = Field(None, description="Task completion timestamp")
    processing_time_ms: float = Field(None, description="Total processing time in milliseconds")


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""
    period_days: int = Field(..., description="Statistics period in days")
    total_requests: int = Field(..., description="Total requests in period")
    cache_hits: int = Field(..., description="Number of cache hits")
    cache_hit_ratio: float = Field(..., description="Cache hit ratio percentage")
    successful_tasks: int = Field(..., description="Successfully completed tasks")
    avg_processing_time_ms: float = Field(..., description="Average processing time")
    total_cached_entries: int = Field(..., description="Total entries in cache")
    cache_efficiency: str = Field(..., description="Cache efficiency rating")


class RecentTaskResponse(BaseModel):
    """Response model for recent task information."""
    task_id: str = Field(..., description="Task identifier (first 8 chars)")
    status: str = Field(..., description="Task status")
    submitted_at: str = Field(..., description="Submission timestamp")
    processing_time_ms: float = Field(None, description="Processing time if completed")
    regions_detected: int = Field(None, description="Number of regions detected")
    cache_hits: int = Field(..., description="Number of times served from cache")
    error_type: str = Field(None, description="Error type if failed")
