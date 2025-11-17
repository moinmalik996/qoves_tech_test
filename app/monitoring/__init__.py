"""Monitoring package initialization."""
from app.monitoring.metrics import (
    # Metrics objects
    api_requests_total,
    api_request_duration,
    task_submissions_total,
    task_completions_total,
    task_processing_duration,
    task_counter,  # Alias for task_completions_total
    errors_total,
    instrumentator,
    
    # Functions
    setup_metrics,
    get_metrics,
    track_task_metrics,
    record_landmarks_processed,
    record_region_generated,
)

from app.monitoring.logging import (
    setup_rich_logging,
    get_logger,
    log_startup_info,
)

__all__ = [
    # Metrics
    'api_requests_total',
    'api_request_duration',
    'task_submissions_total',
    'task_completions_total',
    'task_processing_duration',
    'task_counter',
    'errors_total',
    'instrumentator',
    'setup_metrics',
    'get_metrics',
    'track_task_metrics',
    'record_landmarks_processed',
    'record_region_generated',
    
    # Logging
    'setup_rich_logging',
    'get_logger',
    'log_startup_info',
]
