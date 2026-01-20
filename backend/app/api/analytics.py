"""
XenFlow Mailer - Analytics API
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from app.database import get_db
from app.models import Lead, Campaign, Sender, EmailLog, Suppression
from app.models.lead import LeadStatus
from app.models.campaign import CampaignStatus
from app.models.sender import SenderStatus
from app.models.email_log import EmailStatus
from app.schemas.analytics import (
    DashboardStats, CampaignAnalytics, TimeSeriesData,
    EmailLogResponse, EmailLogListResponse
)
from app.config import SafetyLimits
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get main dashboard statistics."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = today - timedelta(days=7)
    
    # Overview counts
    total_leads = db.query(Lead).count()
    active_campaigns = db.query(Campaign).filter(
        Campaign.status == CampaignStatus.ACTIVE
    ).count()
    total_senders = db.query(Sender).count()
    
    # Today's stats
    emails_today = db.query(EmailLog).filter(
        EmailLog.sent_at >= today,
        EmailLog.status == EmailStatus.SENT
    ).count()
    
    replies_today = db.query(Lead).filter(
        Lead.replied_at >= today
    ).count()
    
    bounces_today = db.query(EmailLog).filter(
        EmailLog.bounced_at >= today
    ).count()
    
    # Overall metrics
    total_sent = db.query(EmailLog).filter(
        EmailLog.status.in_([EmailStatus.SENT, EmailStatus.DELIVERED, 
                            EmailStatus.OPENED, EmailStatus.REPLIED])
    ).count()
    
    total_replies = db.query(Lead).filter(Lead.replied == True).count()
    total_bounces = db.query(EmailLog).filter(
        EmailLog.status == EmailStatus.BOUNCED
    ).count()
    
    reply_rate = (total_replies / max(total_sent, 1)) * 100
    bounce_rate = (total_bounces / max(total_sent, 1)) * 100
    delivery_rate = ((total_sent - total_bounces) / max(total_sent, 1)) * 100
    
    # Sender health
    senders_healthy = db.query(Sender).filter(
        Sender.status == SenderStatus.ACTIVE,
        Sender.reputation_score >= 80
    ).count()
    
    senders_warning = db.query(Sender).filter(
        Sender.status.in_([SenderStatus.ACTIVE, SenderStatus.WARMING_UP]),
        Sender.reputation_score.between(50, 79)
    ).count()
    
    senders_critical = db.query(Sender).filter(
        Sender.reputation_score < 50
    ).count()
    
    # Recent campaigns
    recent_campaigns = db.query(Campaign).order_by(
        Campaign.updated_at.desc()
    ).limit(5).all()
    
    # Recent replies
    recent_replies = db.query(Lead).filter(
        Lead.replied == True
    ).order_by(Lead.replied_at.desc()).limit(5).all()
    
    # Time series data
    sends_7_days = []
    replies_7_days = []
    
    for i in range(7):
        day = today - timedelta(days=6-i)
        next_day = day + timedelta(days=1)
        
        day_sends = db.query(EmailLog).filter(
            and_(
                EmailLog.sent_at >= day,
                EmailLog.sent_at < next_day,
                EmailLog.status.in_([EmailStatus.SENT, EmailStatus.DELIVERED])
            )
        ).count()
        
        day_replies = db.query(Lead).filter(
            and_(
                Lead.replied_at >= day,
                Lead.replied_at < next_day
            )
        ).count()
        
        sends_7_days.append(TimeSeriesData(date=day.date(), value=day_sends))
        replies_7_days.append(TimeSeriesData(date=day.date(), value=day_replies))
    
    # Safety check
    is_safe, safety_warnings = check_system_safety(db)
    
    return DashboardStats(
        total_leads=total_leads,
        active_campaigns=active_campaigns,
        total_senders=total_senders,
        emails_sent_today=emails_today,
        replies_today=replies_today,
        bounces_today=bounces_today,
        total_emails_sent=total_sent,
        total_replies=total_replies,
        overall_reply_rate=round(reply_rate, 2),
        overall_bounce_rate=round(bounce_rate, 2),
        overall_delivery_rate=round(delivery_rate, 2),
        senders_healthy=senders_healthy,
        senders_warning=senders_warning,
        senders_critical=senders_critical,
        recent_campaigns=[
            {
                "id": c.id,
                "name": c.name,
                "status": c.status.value,
                "emails_sent": c.emails_sent,
                "reply_rate": round(c.reply_rate, 1)
            }
            for c in recent_campaigns
        ],
        recent_replies=[
            {
                "lead_id": l.id,
                "email": l.email,
                "name": l.display_name,
                "replied_at": l.replied_at.isoformat() if l.replied_at else None
            }
            for l in recent_replies
        ],
        sends_last_7_days=sends_7_days,
        replies_last_7_days=replies_7_days,
        is_safe_to_send=is_safe,
        safety_warnings=safety_warnings
    )


@router.get("/campaigns/{campaign_id}")
def get_campaign_analytics(campaign_id: int, db: Session = Depends(get_db)):
    """Get detailed analytics for a campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Lead status breakdown
    lead_statuses = {}
    for status in LeadStatus:
        count = db.query(Lead).filter(
            Lead.campaign_id == campaign_id,
            Lead.status == status
        ).count()
        lead_statuses[status.value] = count
    
    # Email status breakdown
    email_statuses = {}
    for status in EmailStatus:
        count = db.query(EmailLog).filter(
            EmailLog.campaign_id == campaign_id,
            EmailLog.status == status
        ).count()
        if count > 0:
            email_statuses[status.value] = count
    
    # Follow-up breakdown
    followup_stats = db.query(
        EmailLog.followup_step,
        func.count(EmailLog.id)
    ).filter(
        EmailLog.campaign_id == campaign_id
    ).group_by(EmailLog.followup_step).all()
    
    followup_data = {f"step_{step}": count for step, count in followup_stats}
    
    return {
        "campaign_id": campaign_id,
        "campaign_name": campaign.name,
        "status": campaign.status.value,
        "overview": {
            "total_leads": campaign.total_leads,
            "emails_sent": campaign.emails_sent,
            "replies": campaign.replies_count,
            "bounces": campaign.bounces_count,
            "unsubscribes": campaign.unsubscribes_count
        },
        "rates": {
            "reply_rate": round(campaign.reply_rate, 2),
            "bounce_rate": round(campaign.bounce_rate, 2),
            "open_rate": 0,  # Would need tracking
            "click_rate": 0
        },
        "lead_statuses": lead_statuses,
        "email_statuses": email_statuses,
        "followup_breakdown": followup_data
    }


@router.get("/emails", response_model=EmailLogListResponse)
def get_email_logs(
    campaign_id: Optional[int] = None,
    status: Optional[str] = None,
    to_email: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get email logs with filtering."""
    query = db.query(EmailLog)
    
    if campaign_id:
        query = query.filter(EmailLog.campaign_id == campaign_id)
    
    if status:
        query = query.filter(EmailLog.status == status)
    
    if to_email:
        query = query.filter(EmailLog.to_email.ilike(f"%{to_email}%"))
    
    total = query.count()
    
    logs = query.order_by(EmailLog.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    # Get campaign names
    campaign_ids = list(set(l.campaign_id for l in logs if l.campaign_id))
    campaigns = {c.id: c.name for c in db.query(Campaign).filter(
        Campaign.id.in_(campaign_ids)
    ).all()}
    
    items = []
    for log in logs:
        item = EmailLogResponse(
            id=log.id,
            campaign_id=log.campaign_id,
            campaign_name=campaigns.get(log.campaign_id),
            lead_id=log.lead_id,
            to_email=log.to_email,
            to_name=log.to_name,
            subject=log.subject,
            status=log.status.value,
            email_type=log.email_type.value,
            followup_step=log.followup_step,
            sent_at=log.sent_at,
            opened_at=log.opened_at,
            replied_at=log.replied_at,
            bounced_at=log.bounced_at,
            bounce_type=log.bounce_type.value if log.bounce_type else None,
            error_message=log.error_message
        )
        items.append(item)
    
    return EmailLogListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/suppressions")
def get_suppression_stats(db: Session = Depends(get_db)):
    """Get suppression list statistics."""
    from app.services.suppression import SuppressionService
    
    service = SuppressionService(db)
    return service.get_suppression_stats()


def check_system_safety(db: Session) -> tuple:
    """Check overall system safety."""
    warnings = []
    
    # Check overall bounce rate
    total_sent = db.query(EmailLog).filter(
        EmailLog.status.in_([EmailStatus.SENT, EmailStatus.DELIVERED])
    ).count()
    
    total_bounced = db.query(EmailLog).filter(
        EmailLog.status == EmailStatus.BOUNCED
    ).count()
    
    if total_sent > 0:
        bounce_rate = total_bounced / total_sent
        if bounce_rate >= SafetyLimits.ABSOLUTE_MAX_BOUNCE_RATE:
            warnings.append(f"System bounce rate ({bounce_rate:.1%}) exceeds safe threshold")
    
    # Check for senders with issues
    problem_senders = db.query(Sender).filter(
        Sender.reputation_score < 50
    ).count()
    
    if problem_senders > 0:
        warnings.append(f"{problem_senders} sender(s) have low reputation scores")
    
    # Check suppression list growth
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    new_suppressions = db.query(Suppression).filter(
        Suppression.created_at >= today
    ).count()
    
    if new_suppressions > 20:
        warnings.append(f"{new_suppressions} emails suppressed today - review needed")
    
    is_safe = len(warnings) == 0
    
    return is_safe, warnings

