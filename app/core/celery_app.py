"""Celery configuration."""
from celery import Celery
from kombu import Queue
from app.core.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# Create Celery app
celery_app = Celery(
    'facial_processing',
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=['app.tasks.facial_processing']
)

# Celery configuration
celery_app.conf.update(
    # Task serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    
    # Task routing
    task_routes={
        'app.tasks.facial_processing.process_facial_regions_task': {'queue': 'facial_processing'}
    },
    
    # Task settings
    task_track_started=True,
    task_time_limit=300,  # 5 minutes
    task_soft_time_limit=240,  # 4 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    
    # Result backend settings
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Queue configuration
    task_default_queue='facial_processing',
    task_queues=(
        Queue('facial_processing', routing_key='facial_processing'),
    ),
)

if __name__ == '__main__':
    celery_app.start()
