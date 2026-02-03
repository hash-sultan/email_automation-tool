"""
XenFlow Mailer - Follow-up Worker
Celery tasks for processing follow-ups
"""

import asyncio
from datetime import datetime
from celery import shared_task

from app.workers.celery_app import celery_app
from app.workers.email_worker import send_email_task
from app.database import get_db_context
from app.models import Lead, Campaign, EmailLog
from app.models.campaign import CampaignStatus
from app.services.followup_engine import FollowUpEngine
from app.services.rate_limiter import RateLimiter
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="app.workers.followup_worker.process_followups_task",
    bind=True
)
def process_followups_task(self, campaign_id: int = None, limit: int = 100):
    """
    Process pending follow-ups.
    
    This is called periodically by Celery Beat.
    """
    logger.info("Processing follow-ups", extra={"campaign_id": campaign_id})
    
    with get_db_context() as db:
        followup_engine = FollowUpEngine(db)
        
        # When campaign_id is set (manual trigger), include leads even if campaign is PAUSED
        allow_paused = campaign_id is not None
        leads = followup_engine.get_leads_ready_for_followup(
            campaign_id=campaign_id,
            limit=limit,
            allow_paused_campaign=allow_paused,
        )
        
        if not leads:
            return {"status": "complete", "processed": 0}
        
        queued = 0
        skipped = 0
        rate_limiter = RateLimiter()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for lead in leads:
            next_step = lead.step + 1
            
            # Check if there's already a pending email for this lead/step
            from app.models.email_log import EmailLog, EmailStatus
            pending_email = db.query(EmailLog).filter(
                EmailLog.lead_id == lead.id,
                EmailLog.campaign_id == lead.campaign_id,
                EmailLog.followup_step == next_step,
                EmailLog.status.in_([EmailStatus.QUEUED, EmailStatus.SENDING])
            ).first()
            
            if pending_email:
                logger.debug(
                    f"Skipping follow-up for lead {lead.email} step {next_step} - already has pending email (log_id: {pending_email.id})",
                    extra={
                        "lead_id": lead.id,
                        "campaign_id": lead.campaign_id,
                        "followup_step": next_step,
                        "pending_log_id": pending_email.id
                    }
                )
                skipped += 1
                continue
            
            # Get the last email sent to find in_reply_to
            last_email = db.query(EmailLog).filter(
                EmailLog.lead_id == lead.id
            ).order_by(EmailLog.sent_at.desc()).first()
            
            in_reply_to = last_email.message_id if last_email else None
            references = last_email.references if last_email else None
            
            if in_reply_to and references:
                references = f"{references} {in_reply_to}"
            elif in_reply_to:
                references = in_reply_to
            
            # No delay: queue immediately (single campaign at a time, multiple senders)
            send_email_task.apply_async(
                args=[
                    lead.id,
                    lead.campaign_id,
                    next_step,
                    in_reply_to,
                    references
                ]
            )
            
            queued += 1
        
        loop.close()
        
        logger.info(
            f"Queued {queued} follow-ups (skipped {skipped} duplicates)",
            extra={
                "queued": queued,
                "skipped": skipped,
                "campaign_id": campaign_id,
            }
        )
        
        return {"status": "processed", "queued": queued, "skipped": skipped}


@celery_app.task(name="app.workers.followup_worker.schedule_followup_task")
def schedule_followup_task(lead_id: int, campaign_id: int):
    """
    Schedule the next follow-up for a lead after sending.
    """
    with get_db_context() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        
        if not lead or not campaign:
            return {"status": "error", "message": "Lead or Campaign not found"}
        
        if not campaign.followup_enabled:
            return {"status": "skipped", "message": "Follow-ups disabled"}
        
        followup_engine = FollowUpEngine(db)
        next_followup = followup_engine.schedule_next_followup(lead, campaign)
        
        db.commit()
        
        if next_followup:
            return {
                "status": "scheduled",
                "lead_id": lead_id,
                "next_step": lead.step + 1,
                "scheduled_for": next_followup.isoformat()
            }
        else:
            return {
                "status": "complete",
                "lead_id": lead_id,
                "message": "No more follow-ups scheduled"
            }


@celery_app.task(name="app.workers.followup_worker.cancel_lead_followups_task")
def cancel_lead_followups_task(lead_id: int, reason: str = None):
    """
    Cancel all pending follow-ups for a lead.
    """
    with get_db_context() as db:
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        
        if not lead:
            return {"status": "error", "message": "Lead not found"}
        
        followup_engine = FollowUpEngine(db)
        followup_engine.cancel_followups(lead, reason)
        
        db.commit()
        
        return {"status": "cancelled", "lead_id": lead_id, "reason": reason}


@celery_app.task(name="app.workers.followup_worker.pause_campaign_followups_task")
def pause_campaign_followups_task(campaign_id: int):
    """
    Pause all follow-ups for a campaign.
    """
    with get_db_context() as db:
        followup_engine = FollowUpEngine(db)
        count = followup_engine.pause_campaign_followups(campaign_id)
        
        db.commit()
        
        return {"status": "paused", "campaign_id": campaign_id, "leads_affected": count}


@celery_app.task(name="app.workers.followup_worker.resume_campaign_followups_task")
def resume_campaign_followups_task(campaign_id: int):
    """
    Resume follow-ups for a campaign.
    """
    with get_db_context() as db:
        followup_engine = FollowUpEngine(db)
        count = followup_engine.resume_campaign_followups(campaign_id)
        
        db.commit()
        
        return {"status": "resumed", "campaign_id": campaign_id, "leads_scheduled": count}


@celery_app.task(name="app.workers.followup_worker.get_followup_stats_task")
def get_followup_stats_task(campaign_id: int = None):
    """
    Get follow-up queue statistics.
    """
    with get_db_context() as db:
        followup_engine = FollowUpEngine(db)
        stats = followup_engine.get_followup_queue_stats(campaign_id)
        
        return stats

