"""
XenFlow Mailer - Campaigns API
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Campaign, Lead, CampaignSender, EmailLog
from app.models.campaign import CampaignStatus
from app.models.lead import LeadStatus
from app.models.email_log import EmailStatus, EmailType
from app.schemas.campaign import (
    CampaignCreate, CampaignUpdate, CampaignResponse, 
    CampaignListResponse, CampaignStats
)
from app.workers.email_worker import start_campaign_task, pause_campaign_task, send_bulk_emails_task
from app.workers.followup_worker import pause_campaign_followups_task, resume_campaign_followups_task, process_followups_task
from app.utils.logger import get_logger
from sqlalchemy import func

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=CampaignListResponse)
def list_campaigns(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List campaigns with pagination."""
    query = db.query(Campaign)

    if status:
        query = query.filter(Campaign.status == status)

    total = query.count()

    campaigns = (
        query.order_by(Campaign.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    # Pre-compute unique leads contacted and replies per campaign from email logs
    campaign_ids = [c.id for c in campaigns]
    leads_contacted_map: dict[int, int] = {}
    replies_map: dict[int, int] = {}
    followups_sent_map: dict[int, int] = {}
    if campaign_ids:
        # Leads contacted (unique initial emails successfully sent)
        rows = (
            db.query(
                EmailLog.campaign_id,
                func.count(func.distinct(EmailLog.lead_id)).label("leads_contacted"),
            )
            .filter(
                EmailLog.campaign_id.in_(campaign_ids),
                EmailLog.email_type == EmailType.INITIAL,
                EmailLog.status.in_([EmailStatus.SENT, EmailStatus.REPLIED]),
            )
            .group_by(EmailLog.campaign_id)
            .all()
        )
        leads_contacted_map = {row.campaign_id: row.leads_contacted for row in rows}

        # Replies per campaign (from EmailLog, most accurate)
        reply_rows = (
            db.query(
                EmailLog.campaign_id,
                func.count(EmailLog.id).label("replies"),
            )
            .filter(
                EmailLog.campaign_id.in_(campaign_ids),
                EmailLog.status == EmailStatus.REPLIED,
            )
            .group_by(EmailLog.campaign_id)
            .all()
        )
        replies_map = {row.campaign_id: row.replies for row in reply_rows}

        # Follow-ups sent per campaign (from EmailLog)
        followup_rows = (
            db.query(
                EmailLog.campaign_id,
                func.count(EmailLog.id).label("followups_sent"),
            )
            .filter(
                EmailLog.campaign_id.in_(campaign_ids),
                EmailLog.email_type == EmailType.FOLLOWUP,
                EmailLog.status.in_([
                    EmailStatus.SENT,
                    EmailStatus.DELIVERED,
                    EmailStatus.OPENED,
                    EmailStatus.CLICKED,
                    EmailStatus.REPLIED
                ]),
            )
            .group_by(EmailLog.campaign_id)
            .all()
        )
        followups_sent_map = {row.campaign_id: row.followups_sent for row in followup_rows}

    items: List[CampaignResponse] = []
    for c in campaigns:
        resp = CampaignResponse.model_validate(c)
        resp.leads_contacted = leads_contacted_map.get(c.id, 0)
        # Override replies_count from logs so it matches Analytics/Dashboard
        resp.replies_count = replies_map.get(c.id, 0)
        # Override followups_sent from logs for accuracy
        resp.followups_sent = followups_sent_map.get(c.id, 0)
        # Populate sender_ids from campaign_senders relationship
        if c.sender_rotation_enabled and c.campaign_senders:
            resp.sender_ids = [cs.sender_id for cs in sorted(c.campaign_senders, key=lambda x: x.position)]
        items.append(resp)

    return CampaignListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size,
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Get a specific campaign with stats."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    response = CampaignResponse.model_validate(campaign)

    # Populate sender_ids from campaign_senders relationship
    if campaign.sender_rotation_enabled and campaign.campaign_senders:
        response.sender_ids = [cs.sender_id for cs in sorted(campaign.campaign_senders, key=lambda x: x.position)]

    # Compute unique leads contacted for this campaign
    leads_contacted = (
        db.query(func.count(func.distinct(EmailLog.lead_id)))
        .filter(
            EmailLog.campaign_id == campaign_id,
            EmailLog.email_type == EmailType.INITIAL,
            EmailLog.status.in_([EmailStatus.SENT, EmailStatus.REPLIED]),
        )
        .scalar()
        or 0
    )
    response.leads_contacted = leads_contacted

    # Compute replies from EmailLog so it matches analytics/dashboard
    replies_count = (
        db.query(func.count(EmailLog.id))
        .filter(
            EmailLog.campaign_id == campaign_id,
            EmailLog.status == EmailStatus.REPLIED,
        )
        .scalar()
        or 0
    )
    response.replies_count = replies_count

    # Compute follow-ups sent from EmailLog
    followups_sent = (
        db.query(func.count(EmailLog.id))
        .filter(
            EmailLog.campaign_id == campaign_id,
            EmailLog.email_type == EmailType.FOLLOWUP,
            EmailLog.status.in_([
                EmailStatus.SENT,
                EmailStatus.DELIVERED,
                EmailStatus.OPENED,
                EmailStatus.CLICKED,
                EmailStatus.REPLIED
            ]),
        )
        .scalar()
        or 0
    )
    response.followups_sent = followups_sent

    # Add stats
    response.stats = CampaignStats(
        total_leads=campaign.total_leads,
        emails_sent=campaign.emails_sent,
        followups_sent=followups_sent,
        emails_today=campaign.emails_today,
        leads_contacted=leads_contacted,
        replies_count=replies_count,
        bounces_count=campaign.bounces_count,
        unsubscribes_count=campaign.unsubscribes_count,
        reply_rate=campaign.reply_rate,
        bounce_rate=campaign.bounce_rate,
    )

    return response


@router.post("/", response_model=CampaignResponse)
def create_campaign(campaign_data: CampaignCreate, db: Session = Depends(get_db)):
    """Create a new campaign."""
    from app.models import Template, FollowUpTemplate
    from app.api.settings import load_settings
    
    # Extract follow-up template IDs, template category, and sender rotation settings
    # before creating campaign
    followup_template_ids = campaign_data.followup_template_ids or []
    template_category = campaign_data.template_category
    sender_rotation_enabled = campaign_data.sender_rotation_enabled
    sender_ids = campaign_data.sender_ids or []
    max_senders = campaign_data.max_senders

    # Validation: either a single template or a template category must be provided
    if not campaign_data.template_id and not template_category:
        raise HTTPException(
            status_code=400,
            detail="Either template_id or template_category must be provided",
        )

    campaign_dict = campaign_data.model_dump(
        exclude={
            "followup_template_ids",
            "template_category",
            "sender_rotation_enabled",
            "sender_ids",
            "max_senders",
        }
    )
    
    # Use settings default for daily_limit if not explicitly provided
    if 'daily_limit' not in campaign_dict or campaign_dict.get('daily_limit') is None:
        settings = load_settings()
        campaign_dict['daily_limit'] = settings.get('campaign_daily_limit', 500)

    # Attach template_category if provided (category-based mode)
    if template_category:
        campaign_dict["template_category"] = template_category
    
    campaign = Campaign(**campaign_dict)
    
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # Configure sender rotation if enabled
    if sender_rotation_enabled:
        if not sender_ids:
            raise HTTPException(
                status_code=400,
                detail="sender_ids must be provided when sender_rotation_enabled is true",
            )

        # Apply optional max_senders cap
        if max_senders and max_senders > 0:
            sender_ids = sender_ids[:max_senders]

        for position, sender_id in enumerate(sender_ids, start=1):
            db.add(
                CampaignSender(
                    campaign_id=campaign.id,
                    sender_id=sender_id,
                    position=position,
                )
            )
        campaign.sender_rotation_enabled = True
        campaign.max_senders = max_senders
        db.commit()
        db.refresh(campaign)
    
    # Create FollowUpTemplate records from selected templates
    if followup_template_ids and campaign.followup_enabled:
        followup_templates = db.query(Template).filter(
            Template.id.in_(followup_template_ids),
            Template.is_active == True
        ).all()
        
        for idx, template in enumerate(followup_templates, start=1):
            followup_template = FollowUpTemplate(
                campaign_id=campaign.id,
                step=idx,
                delay_days=campaign.followup_delay_days,
                delay_hours=0,
                subject=template.subject,
                body_html=template.body_html,
                body_plain=template.body_plain,
                reply_to_thread=True,
                is_active=True
            )
            db.add(followup_template)
        
        db.commit()
        db.refresh(campaign)
    
    return CampaignResponse.model_validate(campaign)


@router.put("/{campaign_id}", response_model=CampaignResponse)
def update_campaign(
    campaign_id: int, 
    campaign_data: CampaignUpdate, 
    db: Session = Depends(get_db)
):
    """Update a campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    update_data = campaign_data.model_dump(exclude_unset=True)

    # Handle rotation-specific updates
    sender_rotation_enabled = update_data.pop("sender_rotation_enabled", None)
    sender_ids = update_data.pop("sender_ids", None)
    max_senders = update_data.pop("max_senders", None)

    for key, value in update_data.items():
        setattr(campaign, key, value)

    # If rotation flag is explicitly provided, update it
    if sender_rotation_enabled is not None:
        campaign.sender_rotation_enabled = sender_rotation_enabled

        # If turning rotation off, clear association rows
        if not sender_rotation_enabled:
            db.query(CampaignSender).filter(
                CampaignSender.campaign_id == campaign.id
            ).delete()
            campaign.max_senders = None

    # Update rotation senders if provided
    if sender_ids is not None:
        # Clear existing associations
        db.query(CampaignSender).filter(
            CampaignSender.campaign_id == campaign.id
        ).delete()

        if sender_ids:
            if max_senders and max_senders > 0:
                sender_ids = sender_ids[:max_senders]

            for position, sender_id in enumerate(sender_ids, start=1):
                db.add(
                    CampaignSender(
                        campaign_id=campaign.id,
                        sender_id=sender_id,
                        position=position,
                    )
                )

            campaign.sender_rotation_enabled = True
            if max_senders is not None:
                campaign.max_senders = max_senders

    db.commit()
    db.refresh(campaign)

    return CampaignResponse.model_validate(campaign)


@router.delete("/{campaign_id}")
def delete_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Delete a campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status == CampaignStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Cannot delete active campaign")
    
    db.delete(campaign)
    db.commit()
    
    return {"status": "deleted", "campaign_id": campaign_id}


@router.post("/{campaign_id}/start")
def start_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Start a campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status == CampaignStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Campaign is already active")
    
    # Check safety
    is_safe, reason = campaign.is_safe_to_send
    if not is_safe:
        raise HTTPException(status_code=400, detail=f"Cannot start: {reason}")
    
    # Queue start task
    start_campaign_task.delay(campaign_id)
    
    return {"status": "starting", "campaign_id": campaign_id}


@router.post("/{campaign_id}/pause")
def pause_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Pause a campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != CampaignStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Campaign is not active")
    
    # Update status immediately (synchronous)
    campaign.status = CampaignStatus.PAUSED
    db.commit()
    db.refresh(campaign)
    
    # Queue background tasks for cleanup (follow-ups, etc.)
    pause_campaign_followups_task.delay(campaign_id)
    
    # Return updated campaign
    from app.schemas.campaign import CampaignResponse
    response = CampaignResponse.model_validate(campaign)
    return response


@router.post("/{campaign_id}/resume")
def resume_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Resume a paused campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != CampaignStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Campaign is not paused")
    
    # Update status immediately (synchronous)
    campaign.status = CampaignStatus.ACTIVE
    db.commit()
    db.refresh(campaign)
    
    # Queue background tasks for resuming
    resume_campaign_followups_task.delay(campaign_id)
    
    # Trigger initial send
    send_bulk_emails_task.delay(campaign_id)
    
    # Return updated campaign
    from app.schemas.campaign import CampaignResponse
    response = CampaignResponse.model_validate(campaign)
    return response


@router.post("/{campaign_id}/trigger-followups")
def trigger_followups(campaign_id: int, db: Session = Depends(get_db)):
    """Manually trigger follow-up processing for a campaign."""
    from datetime import datetime
    from sqlalchemy import and_
    from app.models.lead import Lead, LeadStatus
    
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != CampaignStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Campaign must be active to trigger follow-ups")
    
    if not campaign.followup_enabled:
        raise HTTPException(status_code=400, detail="Follow-ups are not enabled for this campaign")
    
    # When manually triggering, update next_followup_at to now for eligible leads
    # This allows immediate processing regardless of scheduled time
    from datetime import timezone
    now = datetime.now(timezone.utc)
    eligible_leads = db.query(Lead).filter(
        and_(
            Lead.campaign_id == campaign_id,
            Lead.replied == False,
            Lead.bounced == False,
            Lead.unsubscribed == False,
            Lead.status.in_([LeadStatus.CONTACTED, LeadStatus.QUEUED]),
            Lead.step < campaign.max_followup_steps,
            Lead.next_followup_at.isnot(None)
        )
    ).all()
    
    updated_count = 0
    for lead in eligible_leads:
        # Compare timezone-aware datetimes
        if lead.next_followup_at and lead.next_followup_at > now:
            lead.next_followup_at = now
            updated_count += 1
    
    if updated_count > 0:
        db.commit()
        logger.info(
            f"Updated {updated_count} leads to be ready for immediate follow-up processing",
            extra={"campaign_id": campaign_id, "updated_leads": updated_count}
        )
    
    # Queue the follow-up processing task
    task = process_followups_task.delay(campaign_id=campaign_id, limit=100)
    
    logger.info(
        f"Manually triggered follow-ups for campaign {campaign_id}",
        extra={"campaign_id": campaign_id, "task_id": task.id, "leads_updated": updated_count}
    )
    
    return {
        "status": "triggered",
        "campaign_id": campaign_id,
        "task_id": task.id,
        "leads_updated": updated_count,
        "message": f"Follow-up processing has been queued. {updated_count} leads updated for immediate processing."
    }


@router.post("/{campaign_id}/stop")
def stop_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Stop a campaign completely."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    campaign.status = CampaignStatus.STOPPED
    db.commit()
    
    # Pause all follow-ups
    pause_campaign_followups_task.delay(campaign_id)
    
    return {"status": "stopped", "campaign_id": campaign_id}


@router.get("/{campaign_id}/stats")
def get_campaign_stats(campaign_id: int, db: Session = Depends(get_db)):
    """Get detailed campaign statistics."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Get lead counts by status
    lead_counts = {}
    for status in LeadStatus:
        count = db.query(Lead).filter(
            Lead.campaign_id == campaign_id,
            Lead.status == status
        ).count()
        lead_counts[status.value] = count
    
    # Get follow-up stats
    followup_pending = db.query(Lead).filter(
        Lead.campaign_id == campaign_id,
        Lead.next_followup_at.isnot(None)
    ).count()
    
    return {
        "campaign_id": campaign_id,
        "status": campaign.status.value,
        "total_leads": campaign.total_leads,
        "leads_by_status": lead_counts,
        "emails_sent": campaign.emails_sent,
        "emails_today": campaign.emails_today,
        "replies": campaign.replies_count,
        "bounces": campaign.bounces_count,
        "unsubscribes": campaign.unsubscribes_count,
        "reply_rate": round(campaign.reply_rate, 2),
        "bounce_rate": round(campaign.bounce_rate, 2),
        "followups_pending": followup_pending,
        "is_safe": campaign.is_safe_to_send[0],
        "safety_message": campaign.is_safe_to_send[1]
    }


@router.post("/{campaign_id}/recalculate-counters")
def recalculate_campaign_counters(campaign_id: int, db: Session = Depends(get_db)):
    """
    Recalculate campaign counters from email_logs.
    
    This fixes any discrepancies between the campaign.emails_sent counter
    and the actual number of emails sent (from email_logs).
    
    Useful for:
    - Fixing counters after race conditions
    - Recovering from errors
    - Ensuring accuracy
    """
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Count actual emails sent from email_logs
    actual_sent = (
        db.query(func.count(EmailLog.id))
        .filter(
            EmailLog.campaign_id == campaign_id,
            EmailLog.status.in_([EmailStatus.SENT, EmailStatus.REPLIED]),
            EmailLog.email_type == EmailType.INITIAL
        )
        .scalar() or 0
    )
    
    # Count replies
    actual_replies = (
        db.query(func.count(EmailLog.id))
        .filter(
            EmailLog.campaign_id == campaign_id,
            EmailLog.status == EmailStatus.REPLIED
        )
        .scalar() or 0
    )
    
    # Count bounces
    actual_bounces = (
        db.query(func.count(EmailLog.id))
        .filter(
            EmailLog.campaign_id == campaign_id,
            EmailLog.status == EmailStatus.BOUNCED
        )
        .scalar() or 0
    )
    
    # Update campaign counters
    old_emails_sent = campaign.emails_sent
    old_replies = campaign.replies_count
    old_bounces = campaign.bounces_count
    
    campaign.emails_sent = actual_sent
    campaign.replies_count = actual_replies
    campaign.bounces_count = actual_bounces
    
    db.commit()
    
    logger.info(
        f"Recalculated counters for campaign {campaign_id}",
        extra={
            "campaign_id": campaign_id,
            "old_emails_sent": old_emails_sent,
            "new_emails_sent": actual_sent,
            "old_replies": old_replies,
            "new_replies": actual_replies,
            "old_bounces": old_bounces,
            "new_bounces": actual_bounces
        }
    )
    
    return {
        "status": "success",
        "campaign_id": campaign_id,
        "counters_updated": {
            "emails_sent": {"old": old_emails_sent, "new": actual_sent},
            "replies_count": {"old": old_replies, "new": actual_replies},
            "bounces_count": {"old": old_bounces, "new": actual_bounces}
        }
    }

