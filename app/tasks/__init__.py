"""Celery tasks and processing operations."""
from app.tasks.facial_processing import process_facial_regions_task

__all__ = ["process_facial_regions_task"]
