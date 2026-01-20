"""
XenFlow Mailer - Warmup Worker
Celery tasks for sender warmup management
"""

from datetime import date
from celery import shared_task

from app.workers.celery_app import celery_app
from app.database import get_db_context
from app.models import Sender, Campaign
from app.models.sender import SenderStatus
from app.services.warmup_engine import WarmupEngine
from app.services.rate_limiter import RateLimiter
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(name="app.workers.warmup_worker.update_warmup_task")
def update_warmup_task():
    """
    Update warmup status for all senders.
    
    Called daily by Celery Beat at midnight.
    """
    logger.info("Updating warmup for all senders")
    
    with get_db_context() as db:
        warmup_engine = WarmupEngine(db)
        updated = warmup_engine.update_all_senders()
        
        # Also reset daily counters
        senders = db.query(Sender).filter(
            Sender.status.in_([SenderStatus.ACTIVE, SenderStatus.WARMING_UP])
        ).all()
        
        for sender in senders:
            sender.reset_daily_stats()
        
        db.commit()
        
        return {
            "status": "complete",
            "senders_updated": updated
        }


@celery_app.task(name="app.workers.warmup_worker.reset_hourly_counters_task")
def reset_hourly_counters_task():
    """
    Reset hourly email counters.
    
    Called every hour by Celery Beat.
    """
    logger.info("Resetting hourly counters")
    
    with get_db_context() as db:
        # Reset sender counters
        senders = db.query(Sender).filter(
            Sender.status.in_([SenderStatus.ACTIVE, SenderStatus.WARMING_UP])
        ).all()
        
        for sender in senders:
            sender.reset_hourly_stats()
        
        # Reset campaign counters
        campaigns = db.query(Campaign).filter(
            Campaign.status == "active"
        ).all()
        
        for campaign in campaigns:
            campaign.reset_hourly_counters()
        
        db.commit()
        
        return {
            "status": "complete",
            "senders_reset": len(senders),
            "campaigns_reset": len(campaigns)
        }


@celery_app.task(name="app.workers.warmup_worker.start_warmup_task")
def start_warmup_task(sender_id: int):
    """
    Start warmup for a specific sender.
    """
    with get_db_context() as db:
        sender = db.query(Sender).filter(Sender.id == sender_id).first()
        
        if not sender:
            return {"status": "error", "message": "Sender not found"}
        
        warmup_engine = WarmupEngine(db)
        warmup_engine.start_warmup(sender)
        
        return {
            "status": "started",
            "sender_id": sender_id,
            "daily_limit": sender.current_daily_limit
        }


@celery_app.task(name="app.workers.warmup_worker.skip_warmup_task")
def skip_warmup_task(sender_id: int):
    """
    Skip warmup for a sender (use with caution).
    """
    with get_db_context() as db:
        sender = db.query(Sender).filter(Sender.id == sender_id).first()
        
        if not sender:
            return {"status": "error", "message": "Sender not found"}
        
        warmup_engine = WarmupEngine(db)
        warmup_engine.skip_warmup(sender)
        
        logger.warning(f"Warmup skipped for sender {sender_id}")
        
        return {
            "status": "skipped",
            "sender_id": sender_id,
            "daily_limit": sender.current_daily_limit
        }


@celery_app.task(name="app.workers.warmup_worker.reset_warmup_task")
def reset_warmup_task(sender_id: int):
    """
    Reset warmup for a sender (start fresh).
    """
    with get_db_context() as db:
        sender = db.query(Sender).filter(Sender.id == sender_id).first()
        
        if not sender:
            return {"status": "error", "message": "Sender not found"}
        
        warmup_engine = WarmupEngine(db)
        warmup_engine.reset_warmup(sender)
        
        return {
            "status": "reset",
            "sender_id": sender_id
        }


@celery_app.task(name="app.workers.warmup_worker.get_warmup_status_task")
def get_warmup_status_task(sender_id: int):
    """
    Get warmup status for a sender.
    """
    with get_db_context() as db:
        sender = db.query(Sender).filter(Sender.id == sender_id).first()
        
        if not sender:
            return {"status": "error", "message": "Sender not found"}
        
        warmup_engine = WarmupEngine(db)
        status = warmup_engine.get_warmup_status(sender)
        
        return status

