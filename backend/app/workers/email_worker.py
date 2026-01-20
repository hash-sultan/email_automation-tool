"""
XenFlow Mailer - Email Worker
Celery tasks for sending emails
"""

import asyncio
from typing import List, Optional
from celery import shared_task
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.database import get_db_context
from app.models import Lead, Campaign, Template, EmailLog
from app.models.lead import LeadStatus
from app.models.campaign import CampaignStatus
from app.services.email_service import EmailService
from app.services.rate_limiter import RateLimiter
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(
    bind=True,
    name="app.workers.email_worker.send_email_task",
    max_retries=3,
    default_retry_delay=60,
    rate_limit="10/m"  # Max 10 tasks per minute per worker
)
def send_email_task(
    self,
    lead_id: int,
    campaign_id: int,
    followup_step: int = 0,
    in_reply_to: str = None,
    references: str = None
):
    """
    Send email to a single lead.
    
    This is the main email sending task.
    """
    logger.info(
        f"Processing email task",
        extra={
            "lead_id": lead_id,
            "campaign_id": campaign_id,
            "followup_step": followup_step
        }
    )
    
    with get_db_context() as db:
        # Load entities
        lead = db.query(Lead).filter(Lead.id == lead_id).first()
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        
        if not lead or not campaign:
            logger.error(f"Lead or Campaign not found: lead={lead_id}, campaign={campaign_id}")
            return {"status": "error", "message": "Lead or Campaign not found"}
        
        # Check if campaign is still active
        if campaign.status != CampaignStatus.ACTIVE:
            logger.info(f"Campaign {campaign_id} is not active, skipping")
            return {"status": "skipped", "message": f"Campaign status: {campaign.status}"}
        
        # Check if lead is still contactable
        if not lead.is_contactable:
            logger.info(f"Lead {lead.email} is not contactable, skipping")
            return {"status": "skipped", "message": f"Lead status: {lead.status}"}
        
        # Send email
        email_service = EmailService(db)
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            result = loop.run_until_complete(
                email_service.send_to_lead(
                    lead=lead,
                    campaign=campaign,
                    followup_step=followup_step,
                    in_reply_to=in_reply_to,
                    references=references
                )
            )
            
            loop.run_until_complete(email_service.close())
            loop.close()
            
            if result.is_success:
                return {
                    "status": "success",
                    "message_id": result.message_id,
                    "lead_email": lead.email
                }
            elif result.status.value == "rate_limited":
                # Retry later
                raise self.retry(
                    exc=Exception(result.error_message),
                    countdown=60  # Retry in 1 minute
                )
            else:
                return {
                    "status": "failed",
                    "error": result.error_message,
                    "lead_email": lead.email
                }
                
        except Exception as e:
            logger.error(f"Email task error: {str(e)}")
            raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    name="app.workers.email_worker.send_bulk_emails_task",
    max_retries=1
)
def send_bulk_emails_task(
    self,
    campaign_id: int,
    limit: int = 50
):
    """
    Queue emails for multiple leads in a campaign.
    
    This task fans out to individual send_email_task calls.
    """
    logger.info(f"Processing bulk email task for campaign {campaign_id}")
    
    with get_db_context() as db:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        
        if not campaign or campaign.status != CampaignStatus.ACTIVE:
            return {"status": "skipped", "message": "Campaign not active"}
        
        # Get leads to contact
        leads = db.query(Lead).filter(
            Lead.campaign_id == campaign_id,
            Lead.status == LeadStatus.QUEUED,
            Lead.replied == False,
            Lead.bounced == False,
            Lead.unsubscribed == False
        ).limit(limit).all()
        
        if not leads:
            return {"status": "complete", "message": "No leads to contact"}
        
        # Queue individual send tasks
        queued = 0
        rate_limiter = RateLimiter()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for lead in leads:
            # Get random delay for human-like sending
            delay = loop.run_until_complete(
                rate_limiter.get_random_delay(
                    min_seconds=campaign.min_interval_seconds,
                    max_seconds=campaign.max_interval_seconds
                )
            )
            
            # Queue with countdown
            send_email_task.apply_async(
                args=[lead.id, campaign_id, 0],
                countdown=delay * queued  # Stagger the sends
            )
            
            queued += 1
        
        loop.close()
        
        logger.info(f"Queued {queued} emails for campaign {campaign_id}")
        
        return {
            "status": "queued",
            "count": queued,
            "campaign_id": campaign_id
        }


@celery_app.task(name="app.workers.email_worker.start_campaign_task")
def start_campaign_task(campaign_id: int):
    """
    Start a campaign - activates it and begins sending.
    """
    with get_db_context() as db:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        
        if not campaign:
            return {"status": "error", "message": "Campaign not found"}
        
        if campaign.status == CampaignStatus.ACTIVE:
            return {"status": "already_active"}
        
        # Update leads to QUEUED status
        db.query(Lead).filter(
            Lead.campaign_id == campaign_id,
            Lead.status == LeadStatus.NEW
        ).update({Lead.status: LeadStatus.QUEUED})
        
        # Activate campaign
        campaign.status = CampaignStatus.ACTIVE
        # Use SQLAlchemy func via model's metadata bind
        from sqlalchemy.sql import func
        campaign.started_at = func.now()
        
        db.commit()
        
        # Trigger initial send
        send_bulk_emails_task.delay(campaign_id)
        
        return {"status": "started", "campaign_id": campaign_id}


@celery_app.task(name="app.workers.email_worker.pause_campaign_task")
def pause_campaign_task(campaign_id: int):
    """
    Pause a campaign - stops sending but preserves state.
    """
    with get_db_context() as db:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        
        if not campaign:
            return {"status": "error", "message": "Campaign not found"}
        
        campaign.status = CampaignStatus.PAUSED
        db.commit()
        
        return {"status": "paused", "campaign_id": campaign_id}

