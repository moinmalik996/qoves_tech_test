#!/usr/bin/env python3
"""
Celery worker startup script for facial processing tasks.
"""

from celery_config import celery_app

if __name__ == '__main__':
    # Start the Celery worker
    celery_app.worker_main([
        'worker',
        '--loglevel=info',
        '--concurrency=2',
        '--queues=facial_processing',
        '--hostname=facial_worker@%h'
    ])