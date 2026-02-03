"""
XenFlow Mailer - Celery Application
Task queue configuration
"""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "xenflow_mailer",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.email_worker",
        "app.workers.followup_worker",
        "app.workers.imap_worker",
        "app.workers.warmup_worker",
    ]
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,  # Acknowledge after task completion
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,  # One task at a time for rate limiting
    
    # Result settings
    result_expires=3600,  # 1 hour
    
    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
    
    # Rate limiting (per worker)
    worker_concurrency=2,  # Conservative for email sending
    
    # Task routes: control (start/bulk/wake) first so new campaigns don't wait behind send backlog
    task_routes={
        "app.workers.email_worker.start_campaign_task": {"queue": "control"},
        "app.workers.email_worker.send_bulk_emails_task": {"queue": "control"},
        "app.workers.email_worker.wake_active_campaigns_task": {"queue": "control"},
        "app.workers.email_worker.*": {"queue": "emails"},
        "app.workers.followup_worker.*": {"queue": "followups"},
        "app.workers.imap_worker.*": {"queue": "imap"},
        "app.workers.warmup_worker.*": {"queue": "default"},
    },
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        # Process follow-ups every 5 minutes
        "process-followups": {
            "task": "app.workers.followup_worker.process_followups_task",
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "followups"}
        },
        
        # Check replies every 5 minutes
        "check-replies": {
            "task": "app.workers.imap_worker.check_all_replies_task",
            "schedule": crontab(minute="*/5"),
            "options": {"queue": "imap"}
        },
        
        # Update warmup daily at midnight
        "update-warmup": {
            "task": "app.workers.warmup_worker.update_warmup_task",
            "schedule": crontab(hour=0, minute=5),
            "options": {"queue": "default"}
        },
        
        # Reset hourly counters
        "reset-hourly-counters": {
            "task": "app.workers.warmup_worker.reset_hourly_counters_task",
            "schedule": crontab(minute=0),
            "options": {"queue": "default"}
        },
        # Safety net: wake active campaigns that still have leads (in case scheduled next-batch was lost)
        "wake-active-campaigns": {
            "task": "app.workers.email_worker.wake_active_campaigns_task",
            "schedule": crontab(minute="*/2"),  # every 2 minutes
            "options": {"queue": "control"}
        },
    }
)


# After fork, DB connections from the parent pool are invalid in the child.
# Dispose the pool so the worker creates fresh connections (fixes "Lead or Campaign not found").
from celery.signals import worker_process_init

@worker_process_init.connect
def _dispose_db_pool_on_fork(**kwargs):
    from app.database import engine
    engine.dispose()


# Optional: Event handlers for monitoring
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f"Request: {self.request!r}")
    return "pong"

