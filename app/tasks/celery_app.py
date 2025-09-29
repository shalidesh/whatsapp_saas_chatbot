from celery import Celery
from ..config.settings import config

# Create Celery instance
celery_app = Celery(
    'whatsapp_saas',
    broker=config.CELERY_BROKER_URL,
    backend=config.CELERY_RESULT_BACKEND,
    include=['app.tasks.ai_processing', 'app.tasks.document_processing']
)

# Celery configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Colombo',
    enable_utc=True,
    task_track_started=True,
    worker_send_task_events=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=10,
    worker_max_memory_per_child=200000,  # 200MB memory limit
    worker_pool='solo',  # Use solo pool for Windows compatibility
)

# Task routing
celery_app.conf.task_routes = {
    'app.tasks.ai_processing.process_whatsapp_message': {'queue': 'high_priority'},
    'app.tasks.document_processing.process_document_upload': {'queue': 'low_priority'},
}