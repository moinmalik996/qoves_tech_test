"""
Prometheus metrics configuration for the facial processing service.
Provides comprehensive monitoring of API endpoints, task processing, and system performance.
"""

from prometheus_client import Counter, Histogram, Gauge, Info, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator, metrics
import time
from functools import wraps

# API Metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total number of API requests',
    ['method', 'endpoint', 'status_code']
)

api_request_duration = Histogram(
    'api_request_duration_seconds',
    'Time spent processing API requests',
    ['method', 'endpoint'],
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf'))
)

api_request_size = Histogram(
    'api_request_size_bytes',
    'Size of API request payloads',
    ['endpoint'],
    buckets=(1024, 10240, 102400, 1048576, 10485760, float('inf'))
)

api_response_size = Histogram(
    'api_response_size_bytes',
    'Size of API response payloads',
    ['endpoint'],
    buckets=(1024, 10240, 102400, 1048576, 10485760, float('inf'))
)

# Task Processing Metrics
task_submissions_total = Counter(
    'task_submissions_total',
    'Total number of tasks submitted',
    ['task_type']
)

task_completions_total = Counter(
    'task_completions_total',
    'Total number of tasks completed',
    ['task_type', 'status']
)

task_processing_duration = Histogram(
    'task_processing_duration_seconds',
    'Time spent processing tasks',
    ['task_type'],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, float('inf'))
)

task_queue_size = Gauge(
    'task_queue_size',
    'Number of tasks waiting in queue',
    ['queue_name']
)

active_tasks = Gauge(
    'active_tasks_count',
    'Number of currently processing tasks',
    ['task_type']
)

# Image Processing Metrics
image_processing_duration = Histogram(
    'image_processing_duration_seconds',
    'Time spent processing images',
    ['operation'],
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, float('inf'))
)

landmarks_processed_total = Counter(
    'landmarks_processed_total',
    'Total number of landmarks processed'
)

regions_generated_total = Counter(
    'regions_generated_total',
    'Total number of facial regions generated',
    ['region_type']
)

# System Metrics
memory_usage_bytes = Gauge(
    'memory_usage_bytes',
    'Current memory usage in bytes',
    ['process']
)

cpu_usage_percent = Gauge(
    'cpu_usage_percent',
    'Current CPU usage percentage',
    ['process']
)

# Error Metrics
errors_total = Counter(
    'errors_total',
    'Total number of errors',
    ['error_type', 'component']
)

# Application Info
app_info = Info(
    'app_info',
    'Application information'
)

# Initialize FastAPI instrumentator
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_respect_env_var=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/health", "/metrics"],
    env_var_name="ENABLE_METRICS",
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)

def setup_metrics():
    """Initialize application metrics with default values."""
    app_info.info({
        'version': '1.0.0',
        'service': 'facial-processing-api',
        'python_version': '3.12+'
    })

def track_task_metrics(task_type: str):
    """Decorator to track task execution metrics."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            task_submissions_total.labels(task_type=task_type).inc()
            active_tasks.labels(task_type=task_type).inc()
            
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                task_completions_total.labels(task_type=task_type, status='success').inc()
                return result
            except Exception as e:
                task_completions_total.labels(task_type=task_type, status='failure').inc()
                errors_total.labels(error_type=type(e).__name__, component='task_processor').inc()
                raise
            finally:
                duration = time.time() - start_time
                task_processing_duration.labels(task_type=task_type).observe(duration)
                active_tasks.labels(task_type=task_type).dec()
        
        return wrapper
    return decorator

def track_image_processing(operation: str):
    """Decorator to track image processing operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                errors_total.labels(error_type=type(e).__name__, component='image_processor').inc()
                raise
            finally:
                duration = time.time() - start_time
                image_processing_duration.labels(operation=operation).observe(duration)
        
        return wrapper
    return decorator

def record_landmarks_processed(count: int):
    """Record the number of landmarks processed."""
    landmarks_processed_total.inc(count)

def record_region_generated(region_type: str):
    """Record a facial region generation."""
    regions_generated_total.labels(region_type=region_type).inc()

def update_queue_size(queue_name: str, size: int):
    """Update the current queue size."""
    task_queue_size.labels(queue_name=queue_name).set(size)

def record_api_request(method: str, endpoint: str, status_code: int, duration: float, 
                      request_size: int = 0, response_size: int = 0):
    """Record API request metrics."""
    api_requests_total.labels(method=method, endpoint=endpoint, status_code=status_code).inc()
    api_request_duration.labels(method=method, endpoint=endpoint).observe(duration)
    
    if request_size > 0:
        api_request_size.labels(endpoint=endpoint).observe(request_size)
    
    if response_size > 0:
        api_response_size.labels(endpoint=endpoint).observe(response_size)

def get_metrics() -> str:
    """Get current metrics in Prometheus format."""
    return generate_latest()

# Custom metrics for FastAPI instrumentator
def add_custom_metrics():
    """Add custom metrics to the instrumentator."""
    
    @instrumentator.add_metrics
    def request_size_metric(info: metrics.Info) -> None:
        if hasattr(info.request, 'content_length') and info.request.content_length:
            api_request_size.labels(endpoint=info.modified_handler).observe(info.request.content_length)
    
    @instrumentator.add_metrics  
    def response_size_metric(info: metrics.Info) -> None:
        if hasattr(info.response, 'content_length') and info.response.content_length:
            api_response_size.labels(endpoint=info.modified_handler).observe(info.response.content_length)