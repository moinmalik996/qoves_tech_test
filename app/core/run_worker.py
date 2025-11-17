#!/usr/bin/env python3
"""
Celery worker startup script for facial processing tasks.
"""
import sys
from pathlib import Path

from app.core.celery_app import celery_app

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


if __name__ == '__main__':
    # Start the Celery worker
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--concurrency=2',
        '--queues=facial_processing',
        '--hostname=facial_worker@%h'
    ])