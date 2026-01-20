"""
XenFlow Mailer - Campaigns API
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Campaign, Lead
from app.models.campaign import CampaignStatus
from app.models.lead import LeadStatus
from app.schemas.campaign import (
    CampaignCreate, CampaignUpdate, CampaignResponse, 
    CampaignListResponse, CampaignStats
)
from app.workers.email_worker import start_campaign_task, pause_campaign_task, send_bulk_emails_task
from app.workers.followup_worker import pause_campaign_followups_task, resume_campaign_followups_task
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=CampaignListResponse)
def list_campaigns(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List campaigns with pagination."""
    query = db.query(Campaign)
    
    if status:
        query = query.filter(Campaign.status == status)
    
    total = query.count()
    
    campaigns = query.order_by(Campaign.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    return CampaignListResponse(
        items=[CampaignResponse.model_validate(c) for c in campaigns],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/{campaign_id}", response_model=CampaignResponse)
def get_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Get a specific campaign with stats."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    response = CampaignResponse.model_validate(campaign)
    
    # Add stats
    response.stats = CampaignStats(
        total_leads=campaign.total_leads,
        emails_sent=campaign.emails_sent,
        emails_today=campaign.emails_today,
        replies_count=campaign.replies_count,
        bounces_count=campaign.bounces_count,
        unsubscribes_count=campaign.unsubscribes_count,
        reply_rate=campaign.reply_rate,
        bounce_rate=campaign.bounce_rate
    )
    
    return response


@router.post("/", response_model=CampaignResponse)
def create_campaign(campaign_data: CampaignCreate, db: Session = Depends(get_db)):
    """Create a new campaign."""
    campaign = Campaign(**campaign_data.model_dump())
    
    db.add(campaign)
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
    for key, value in update_data.items():
        setattr(campaign, key, value)
    
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
    
    # Queue pause tasks
    pause_campaign_task.delay(campaign_id)
    pause_campaign_followups_task.delay(campaign_id)
    
    return {"status": "pausing", "campaign_id": campaign_id}


@router.post("/{campaign_id}/resume")
def resume_campaign(campaign_id: int, db: Session = Depends(get_db)):
    """Resume a paused campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    if campaign.status != CampaignStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Campaign is not paused")
    
    # Check safety before resuming
    is_safe, reason = campaign.is_safe_to_send
    if not is_safe:
        raise HTTPException(status_code=400, detail=f"Cannot resume: {reason}")
    
    campaign.status = CampaignStatus.ACTIVE
    db.commit()
    
    # Resume follow-ups
    resume_campaign_followups_task.delay(campaign_id)
    
    # Trigger email sending
    send_bulk_emails_task.delay(campaign_id)
    
    return {"status": "resumed", "campaign_id": campaign_id}


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

