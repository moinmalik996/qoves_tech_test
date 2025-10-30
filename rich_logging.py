"""
Rich logging configuration for beautiful console output with structured logging.
Provides enhanced logging with colors, progress bars, and formatted output.
"""

import logging
from typing import Dict, Any
from datetime import datetime
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.table import Table
from rich.panel import Panel
from rich.traceback import install as install_rich_traceback
from rich.theme import Theme
import json

# Custom theme for the application
custom_theme = Theme({
    "info": "dim cyan",
    "warning": "magenta",
    "error": "bold red",
    "critical": "bold white on red",
    "success": "bold green",
    "task": "blue",
    "metric": "yellow",
    "api": "bright_blue",
    "celery": "bright_green",
    "image": "bright_magenta",
})

# Global console instance
console = Console(theme=custom_theme, force_terminal=True)

# Install rich traceback handler for better error display
install_rich_traceback(console=console, show_locals=True)

class RichMetricsFormatter(logging.Formatter):
    """Custom formatter that adds metrics information to log records."""
    
    def format(self, record):
        # Add timestamp if not present
        if not hasattr(record, 'timestamp'):
            record.timestamp = datetime.utcnow().isoformat()
        
        # Add component info
        if not hasattr(record, 'component'):
            record.component = getattr(record, 'name', 'unknown')
        
        return super().format(record)

def setup_rich_logging(
    level: int = logging.INFO,
    show_time: bool = True,
    show_path: bool = False,
    enable_link_path: bool = True,
    rich_tracebacks: bool = True
) -> logging.Logger:
    """
    Setup rich logging with beautiful console output.
    
    Args:
        level: Logging level (default: INFO)
        show_time: Show timestamp in logs
        show_path: Show file path in logs
        enable_link_path: Enable clickable paths in terminal
        rich_tracebacks: Enable rich traceback formatting
    
    Returns:
        Configured logger instance
    """
    
    # Configure rich handler
    rich_handler = RichHandler(
        console=console,
        show_time=show_time,
        show_path=show_path,
        enable_link_path=enable_link_path,
        rich_tracebacks=rich_tracebacks,
        markup=True
    )
    
    # Set custom formatter
    rich_handler.setFormatter(RichMetricsFormatter(
        fmt="%(message)s",
        datefmt="[%X]"
    ))
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[rich_handler]
    )
    
    # Create main application logger
    logger = logging.getLogger("facial_processing")
    logger.setLevel(level)
    
    return logger

def log_startup_info(app_name: str, version: str, host: str, port: int):
    """Display beautiful startup information."""
    startup_panel = Panel.fit(
        f"[bold green]{app_name}[/] v{version}\n"
        f"[dim]Running on[/] [link=http://{host}:{port}]http://{host}:{port}[/]\n"
        f"[dim]Started at[/] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        title="🚀 Service Started",
        border_style="green"
    )
    console.print(startup_panel)

def log_api_request(method: str, path: str, status_code: int, duration_ms: float, 
                   client_ip: str = "", user_agent: str = ""):
    """Log API request with rich formatting."""
    
    # Determine status color
    if status_code < 300:
        status_style = "success"
    elif status_code < 400:
        status_style = "warning"
    else:
        status_style = "error"
    
    # Format duration with appropriate unit
    if duration_ms < 1000:
        duration_str = f"{duration_ms:.1f}ms"
    else:
        duration_str = f"{duration_ms/1000:.2f}s"
    
    console.print(
        f"[api]{method:>6}[/] [dim]{path}[/] "
        f"[{status_style}]{status_code}[/] "
        f"[dim]{duration_str}[/] "
        f"[dim]{client_ip}[/]",
        highlight=False
    )

def log_task_started(task_id: str, task_type: str, **kwargs):
    """Log task start with rich formatting."""
    console.print(
        f"[task]📋 Task Started[/] [dim]{task_id[:8]}[/] "
        f"[bright_blue]{task_type}[/]",
        highlight=False
    )

def log_task_completed(task_id: str, task_type: str, duration_s: float, status: str = "success"):
    """Log task completion with rich formatting."""
    status_emoji = "✅" if status == "success" else "❌"
    
    console.print(
        f"[task]{status_emoji} Task {status.title()}[/] [dim]{task_id[:8]}[/] "
        f"[bright_blue]{task_type}[/] [dim]{duration_s:.2f}s[/]",
        highlight=False
    )

def log_metrics_update(metric_name: str, value: Any, labels: Dict[str, str] = None):
    """Log metrics updates with rich formatting."""
    labels_str = ""
    if labels:
        labels_str = " ".join([f"{k}={v}" for k, v in labels.items()])
    
    console.print(
        f"[metric]📊 Metric[/] [yellow]{metric_name}[/] "
        f"[dim]=[/] [bold]{value}[/] "
        f"[dim]{labels_str}[/]",
        highlight=False
    )

def create_progress_tracker(description: str = "Processing...") -> Progress:
    """Create a rich progress tracker for long-running operations."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console
    )

def log_image_processing(operation: str, image_size: tuple, processing_time: float):
    """Log image processing operations."""
    console.print(
        f"[image]🖼️  Image Processing[/] [bright_magenta]{operation}[/] "
        f"[dim]{image_size[0]}x{image_size[1]}[/] "
        f"[dim]{processing_time:.3f}s[/]",
        highlight=False
    )

def log_error_with_context(error: Exception, context: Dict[str, Any] = None):
    """Log errors with rich formatting and context."""
    error_panel = Panel(
        f"[bold red]{type(error).__name__}:[/] {str(error)}\n"
        f"[dim]Context:[/] {json.dumps(context or {}, indent=2)}",
        title="❌ Error Occurred",
        border_style="red"
    )
    console.print(error_panel)

def display_metrics_dashboard(metrics_data: Dict[str, Any]):
    """Display a live metrics dashboard."""
    table = Table(title="📊 Live Metrics Dashboard")
    
    table.add_column("Metric", style="cyan", no_wrap=True)
    table.add_column("Value", style="magenta")
    table.add_column("Description", style="green")
    
    for name, data in metrics_data.items():
        value = data.get('value', 'N/A')
        description = data.get('description', '')
        table.add_row(name, str(value), description)
    
    return table

def log_celery_worker_status(worker_name: str, status: str, queue_sizes: Dict[str, int] = None):
    """Log Celery worker status with rich formatting."""
    status_emoji = {"online": "🟢", "offline": "🔴", "busy": "🟡"}.get(status, "⚪")
    
    queue_info = ""
    if queue_sizes:
        queue_info = " | ".join([f"{q}:{s}" for q, s in queue_sizes.items()])
    
    console.print(
        f"[celery]{status_emoji} Worker[/] [bright_green]{worker_name}[/] "
        f"[dim]{status}[/] "
        f"[dim]{queue_info}[/]",
        highlight=False
    )

class RichLoggerAdapter(logging.LoggerAdapter):
    """Logger adapter that adds rich formatting context."""
    
    def __init__(self, logger: logging.Logger, extra: Dict[str, Any] = None):
        super().__init__(logger, extra or {})
    
    def process(self, msg, kwargs):
        # Add rich markup to messages based on level
        level_styles = {
            'DEBUG': 'dim',
            'INFO': 'info',
            'WARNING': 'warning',
            'ERROR': 'error',
            'CRITICAL': 'critical'
        }
        
        # Get current log level
        level_name = kwargs.get('level', 'INFO')
        style = level_styles.get(level_name, 'info')
        
        # Apply style if message doesn't already have markup
        if not any(marker in str(msg) for marker in ['[', ']']):
            msg = f"[{style}]{msg}[/]"
        
        return msg, kwargs

def get_rich_logger(name: str, extra: Dict[str, Any] = None) -> RichLoggerAdapter:
    """Get a rich logger adapter with formatting."""
    logger = logging.getLogger(name)
    return RichLoggerAdapter(logger, extra)

# Pre-configured loggers for different components
api_logger = get_rich_logger("api", {"component": "api"})
task_logger = get_rich_logger("tasks", {"component": "celery"})
metrics_logger = get_rich_logger("metrics", {"component": "prometheus"})
image_logger = get_rich_logger("image_processing", {"component": "opencv"})