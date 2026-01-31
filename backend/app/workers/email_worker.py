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
        
        # CRITICAL: Check for duplicates using email_logs (most reliable method)
        # This prevents duplicate sends even if tasks are queued multiple times
        from app.models.email_log import EmailLog, EmailStatus
        
        existing_email = db.query(EmailLog).filter(
            EmailLog.lead_id == lead_id,
            EmailLog.campaign_id == campaign_id,
            EmailLog.followup_step == followup_step,
            EmailLog.status.in_([EmailStatus.SENT, EmailStatus.REPLIED, EmailStatus.SENDING])
        ).first()
        
        if existing_email:
            logger.info(
                f"Lead {lead.email} already has email for step {followup_step} (log_id: {existing_email.id}), skipping duplicate",
                extra={
                    "lead_id": lead_id,
                    "campaign_id": campaign_id,
                    "followup_step": followup_step,
                    "existing_log_id": existing_email.id
                }
            )
            return {"status": "skipped", "message": f"Step {followup_step} already sent (log_id: {existing_email.id})"}
        
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
                # Extract wait time from error message (format: "Wait {seconds} seconds")
                wait_time = 60  # Default to 60 seconds
                if "Wait" in result.error_message:
                    try:
                        # Extract number from "Wait 994 seconds" or similar
                        import re
                        match = re.search(r'Wait\s+(\d+)\s+seconds', result.error_message)
                        if match:
                            wait_time = int(match.group(1))
                            # Cap at 1 hour (3600 seconds) to avoid extremely long retries
                            wait_time = min(wait_time, 3600)
                    except (ValueError, AttributeError):
                        pass  # Use default if parsing fails
                
                # Retry with calculated wait time
                raise self.retry(
                    exc=Exception(result.error_message),
                    countdown=wait_time
                )
            else:
                return {
                    "status": "failed",
                    "error": result.error_message,
                    "lead_email": lead.email
                }
                
        except Exception as e:
            logger.error(f"Email task error: {str(e)}")
            # Extract wait time from error message if it's a rate limit error
            wait_time = 60  # Default to 60 seconds
            error_str = str(e)
            if "Wait" in error_str:
                try:
                    import re
                    match = re.search(r'Wait\s+(\d+)\s+seconds', error_str)
                    if match:
                        wait_time = int(match.group(1))
                        wait_time = min(wait_time, 3600)  # Cap at 1 hour
                except (ValueError, AttributeError):
                    pass
            
            raise self.retry(exc=e, countdown=wait_time)


@celery_app.task(
    bind=True,
    name="app.workers.email_worker.send_bulk_emails_task",
    max_retries=1
)
def send_bulk_emails_task(
    self,
    campaign_id: int,
    limit: int = 100  # Increased from 50 to 100 for better throughput
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
        
        # Exclude leads that already have a pending initial email (QUEUED or SENDING)
        # so we only select leads we can actually queue and make progress
        from app.models.email_log import EmailLog, EmailStatus
        leads_with_pending = db.query(EmailLog.lead_id).filter(
            EmailLog.campaign_id == campaign_id,
            EmailLog.followup_step == 0,
            EmailLog.status.in_([EmailStatus.QUEUED, EmailStatus.SENDING])
        ).subquery()
        
        # Get leads to contact - only those that haven't been contacted yet and have no pending email
        leads = db.query(Lead).filter(
            Lead.campaign_id == campaign_id,
            Lead.status.in_([LeadStatus.QUEUED, LeadStatus.NEW]),
            Lead.replied == False,
            Lead.bounced == False,
            Lead.unsubscribed == False,
            Lead.last_sent_at.is_(None),
            ~Lead.id.in_(db.query(leads_with_pending.c.lead_id))
        ).limit(limit).all()
        
        if not leads:
            # Check if campaign is complete or just waiting for more leads
            # Refresh campaign to get latest status
            db.refresh(campaign)
            if campaign.status == CampaignStatus.ACTIVE:
                # Double-check if there are any leads that might have been missed
                # (e.g., leads that were just added or status changed)
                leads_with_pending = db.query(EmailLog.lead_id).filter(
                    EmailLog.campaign_id == campaign_id,
                    EmailLog.followup_step == 0,
                    EmailLog.status.in_([EmailStatus.QUEUED, EmailStatus.SENDING])
                ).subquery()
                
                remaining_check = db.query(Lead).filter(
                    Lead.campaign_id == campaign_id,
                    Lead.status.in_([LeadStatus.QUEUED, LeadStatus.NEW]),
                    Lead.replied == False,
                    Lead.bounced == False,
                    Lead.unsubscribed == False,
                    Lead.last_sent_at.is_(None),
                    ~Lead.id.in_(db.query(leads_with_pending.c.lead_id))
                ).count()
                
                if remaining_check > 0:
                    # There are leads, but they might have pending emails - schedule a retry
                    logger.info(
                        f"Campaign {campaign_id} has {remaining_check} leads but none were selected, scheduling retry",
                        extra={"campaign_id": campaign_id, "remaining_leads": remaining_check}
                    )
                    send_bulk_emails_task.apply_async(
                        args=[campaign_id, limit],
                        countdown=60  # Retry in 60 seconds
                    )
                    return {"status": "retry_scheduled", "message": f"Retrying in 60s, {remaining_check} leads remaining"}
            
            return {"status": "complete", "message": "No leads to contact"}
        
        # Queue individual send tasks (leads already exclude pending; inner check is extra safety)
        queued = 0
        skipped = 0
        rate_limiter = RateLimiter()
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        for lead in leads:
            # Check if there's already a pending email for this lead/step
            pending_email = db.query(EmailLog).filter(
                EmailLog.lead_id == lead.id,
                EmailLog.campaign_id == campaign_id,
                EmailLog.followup_step == 0,
                EmailLog.status.in_([EmailStatus.QUEUED, EmailStatus.SENDING])
            ).first()
            
            if pending_email:
                logger.debug(
                    f"Skipping lead {lead.email} - already has pending email (log_id: {pending_email.id})",
                    extra={
                        "lead_id": lead.id,
                        "campaign_id": campaign_id,
                        "pending_log_id": pending_email.id
                    }
                )
                skipped += 1
                continue
            
            # No delay: queue immediately (multiple senders handle throughput)
            send_email_task.apply_async(args=[lead.id, campaign_id, 0])
            
            queued += 1
        
        loop.close()
        
        logger.info(
            f"Queued {queued} emails for campaign {campaign_id} (skipped {skipped} duplicates)",
            extra={
                "campaign_id": campaign_id,
                "queued": queued,
                "skipped": skipped
            }
        )
        
        # Check if there are more leads to send and campaign is still active
        # Refresh campaign to get latest status and counters
        db.refresh(campaign)
        
        if campaign.status == CampaignStatus.ACTIVE:
            # Check if campaign has reached daily limit
            can_send, reason = campaign.can_send_now
            if can_send:
                # Check if there are more leads waiting to be contacted
                leads_with_pending = db.query(EmailLog.lead_id).filter(
                    EmailLog.campaign_id == campaign_id,
                    EmailLog.followup_step == 0,
                    EmailLog.status.in_([EmailStatus.QUEUED, EmailStatus.SENDING])
                ).subquery()
                
                remaining_leads = db.query(Lead).filter(
                    Lead.campaign_id == campaign_id,
                    Lead.status.in_([LeadStatus.QUEUED, LeadStatus.NEW]),
                    Lead.replied == False,
                    Lead.bounced == False,
                    Lead.unsubscribed == False,
                    Lead.last_sent_at.is_(None),
                    ~Lead.id.in_(db.query(leads_with_pending.c.lead_id))
                ).count()
                
                if remaining_leads > 0:
                    # Schedule next batch immediately (no delay; single campaign + multiple senders)
                    logger.info(
                        f"Campaign {campaign_id} has {remaining_leads} remaining leads, scheduling next batch",
                        extra={
                            "campaign_id": campaign_id,
                            "remaining_leads": remaining_leads,
                            "emails_today": campaign.emails_today,
                            "daily_limit": campaign.daily_limit,
                            "queued_in_batch": queued
                        }
                    )
                    send_bulk_emails_task.delay(campaign_id, limit)
                else:
                    logger.info(
                        f"Campaign {campaign_id} has no more leads to contact",
                        extra={
                            "campaign_id": campaign_id,
                            "emails_today": campaign.emails_today,
                            "daily_limit": campaign.daily_limit
                        }
                    )
            else:
                logger.info(
                    f"Campaign {campaign_id} cannot send more: {reason}",
                    extra={
                        "campaign_id": campaign_id,
                        "reason": reason,
                        "emails_today": campaign.emails_today,
                        "daily_limit": campaign.daily_limit
                    }
                )
        
        return {
            "status": "queued",
            "count": queued,
            "skipped": skipped,
            "campaign_id": campaign_id
        }


@celery_app.task(name="app.workers.email_worker.start_campaign_task")
def start_campaign_task(campaign_id: int):
    """
    After API has set campaign ACTIVE: mark NEW leads as QUEUED and trigger first send batch.
    """
    with get_db_context() as db:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        
        if not campaign:
            return {"status": "error", "message": "Campaign not found"}
        
        if campaign.status != CampaignStatus.ACTIVE:
            return {"status": "skipped", "message": "Campaign not active"}
        
        # Update leads to QUEUED status so they are picked for sending
        db.query(Lead).filter(
            Lead.campaign_id == campaign_id,
            Lead.status == LeadStatus.NEW
        ).update({Lead.status: LeadStatus.QUEUED})
        
        db.commit()
        
        # Trigger initial send
        send_bulk_emails_task.delay(campaign_id)
        
        return {"status": "started", "campaign_id": campaign_id}


@celery_app.task(name="app.workers.email_worker.wake_active_campaigns_task")
def wake_active_campaigns_task():
    """
    Safety net: find ACTIVE campaigns that still have leads to contact and queue
    send_bulk_emails_task for them. If a scheduled 'next batch' task was lost
    (worker restart, Redis, etc.), this will wake the campaign within a few minutes.
    """
    from app.models.email_log import EmailStatus

    with get_db_context() as db:
        active = db.query(Campaign).filter(Campaign.status == CampaignStatus.ACTIVE).all()
        if not active:
            return {"status": "ok", "woken": 0}

        woken = 0
        for campaign in active:
            can_send, _ = campaign.can_send_now
            if not can_send:
                continue
            # Same logic as send_bulk_emails_task: leads not yet contacted
            leads_with_pending = (
                db.query(EmailLog.lead_id)
                .filter(
                    EmailLog.campaign_id == campaign.id,
                    EmailLog.followup_step == 0,
                    EmailLog.status.in_([EmailStatus.QUEUED, EmailStatus.SENDING]),
                )
                .subquery()
            )
            remaining = (
                db.query(Lead)
                .filter(
                    Lead.campaign_id == campaign.id,
                    Lead.status.in_([LeadStatus.QUEUED, LeadStatus.NEW]),
                    Lead.replied == False,
                    Lead.bounced == False,
                    Lead.unsubscribed == False,
                    Lead.last_sent_at.is_(None),
                    ~Lead.id.in_(db.query(leads_with_pending.c.lead_id)),
                )
                .count()
            )
            if remaining > 0:
                send_bulk_emails_task.delay(campaign.id)
                woken += 1
                logger.info(
                    "Woke active campaign (safety net)",
                    extra={"campaign_id": campaign.id, "remaining_leads": remaining},
                )
        return {"status": "ok", "woken": woken}


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

