"""
XenFlow Mailer - Analytics API
"""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.database import get_db
from app.models import Lead, Campaign, Sender, EmailLog, Suppression
from app.models.lead import LeadStatus
from app.models.campaign import CampaignStatus
from app.models.sender import SenderStatus
from app.models.email_log import EmailStatus, EmailType
from app.schemas.analytics import (
    DashboardStats, CampaignAnalytics, TimeSeriesData,
    EmailLogResponse, EmailLogListResponse
)
from app.config import SafetyLimits
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard_stats(
    days: int = Query(7, ge=1, le=90, description="Number of days to show in charts"),
    db: Session = Depends(get_db)
):
    """Get main dashboard statistics."""
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    period_start = today - timedelta(days=days-1)
    
    # Overview counts
    total_leads = db.query(Lead).count()
    active_campaigns = db.query(Campaign).filter(
        Campaign.status == CampaignStatus.ACTIVE
    ).count()
    total_senders = db.query(Sender).count()
    
    # Today's stats
    # Count all successfully sent emails today (SENT, DELIVERED, OPENED, REPLIED)
    # Exclude FAILED, BOUNCED, CANCELLED, QUEUED, SENDING
    # Use COALESCE to fall back to created_at if sent_at is NULL (for emails that were sent but sent_at wasn't set)
    emails_today = db.query(EmailLog).filter(
        func.coalesce(EmailLog.sent_at, EmailLog.created_at) >= today,
        EmailLog.status.in_([
            EmailStatus.SENT,
            EmailStatus.DELIVERED,
            EmailStatus.OPENED,
            EmailStatus.CLICKED,
            EmailStatus.REPLIED
        ])
    ).count()
    
    # Follow-ups sent today
    followups_today = db.query(EmailLog).filter(
        func.coalesce(EmailLog.sent_at, EmailLog.created_at) >= today,
        EmailLog.email_type == EmailType.FOLLOWUP,
        EmailLog.status.in_([
            EmailStatus.SENT,
            EmailStatus.DELIVERED,
            EmailStatus.OPENED,
            EmailStatus.CLICKED,
            EmailStatus.REPLIED
        ])
    ).count()
    
    # Count replies from EmailLog (more accurate than Lead.replied)
    replies_today = db.query(EmailLog).filter(
        EmailLog.replied_at >= today,
        EmailLog.status == EmailStatus.REPLIED
    ).count()
    
    bounces_today = db.query(EmailLog).filter(
        EmailLog.bounced_at >= today,
        EmailLog.status == EmailStatus.BOUNCED
    ).count()
    
    # Overall metrics - exclude FAILED, BOUNCED, CANCELLED, QUEUED, SENDING
    total_sent = db.query(EmailLog).filter(
        EmailLog.status.in_([
            EmailStatus.SENT,
            EmailStatus.DELIVERED, 
            EmailStatus.OPENED,
            EmailStatus.CLICKED,
            EmailStatus.REPLIED
        ])
    ).count()
    
    # Total follow-ups sent
    total_followups = db.query(EmailLog).filter(
        EmailLog.email_type == EmailType.FOLLOWUP,
        EmailLog.status.in_([
            EmailStatus.SENT,
            EmailStatus.DELIVERED,
            EmailStatus.OPENED,
            EmailStatus.CLICKED,
            EmailStatus.REPLIED
        ])
    ).count()
    
    # Count replies from EmailLog (more accurate)
    total_replies = db.query(EmailLog).filter(
        EmailLog.status == EmailStatus.REPLIED
    ).count()
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
    
    # Recent replies with sender information
    recent_replies_query = (
        db.query(EmailLog, Lead, Sender)
        .join(Lead, EmailLog.lead_id == Lead.id)
        .join(Sender, EmailLog.sender_id == Sender.id)
        .filter(EmailLog.status == EmailStatus.REPLIED)
        .order_by(EmailLog.replied_at.desc())
        .limit(10)
    )
    recent_replies_data = recent_replies_query.all()
    
    recent_replies = []
    for email_log, lead, sender in recent_replies_data:
        recent_replies.append({
            "lead_id": lead.id,
            "email": lead.email,
            "name": lead.display_name,
            "replied_at": email_log.replied_at.isoformat() if email_log.replied_at else None,
            "sender_id": sender.id,
            "sender_email": sender.email,
            "sender_name": sender.name,
            "subject": email_log.subject,
            "campaign_id": email_log.campaign_id
        })
    
    # Time series data - combine sends and replies by day
    emails_by_day = []
    
    for i in range(days):
        day = period_start + timedelta(days=i)
        next_day = day + timedelta(days=1)
        
        day_sends = db.query(EmailLog).filter(
            and_(
                func.coalesce(EmailLog.sent_at, EmailLog.created_at) >= day,
                func.coalesce(EmailLog.sent_at, EmailLog.created_at) < next_day,
                EmailLog.status.in_([EmailStatus.SENT, EmailStatus.DELIVERED, EmailStatus.OPENED, EmailStatus.CLICKED, EmailStatus.REPLIED])
            )
        ).count()
        
        day_replies = db.query(EmailLog).filter(
            and_(
                EmailLog.replied_at >= day,
                EmailLog.replied_at < next_day,
                EmailLog.status == EmailStatus.REPLIED
            )
        ).count()
        
        day_bounces = db.query(EmailLog).filter(
            and_(
                EmailLog.bounced_at >= day,
                EmailLog.bounced_at < next_day,
                EmailLog.status == EmailStatus.BOUNCED
            )
        ).count()
        
        emails_by_day.append({
            "date": day.date().isoformat(),
            "sent": day_sends,
            "replies": day_replies,
            "bounces": day_bounces
        })
    
    # Also keep the old format for backwards compatibility
    from datetime import date as date_type
    sends_last_7_days = [TimeSeriesData(date=date_type.fromisoformat(day["date"]), value=day["sent"]) for day in emails_by_day[-7:]]
    replies_last_7_days = [TimeSeriesData(date=date_type.fromisoformat(day["date"]), value=day["replies"]) for day in emails_by_day[-7:]]
    
    # Safety check
    is_safe, safety_warnings = check_system_safety(db)
    
    return DashboardStats(
        total_leads=total_leads,
        active_campaigns=active_campaigns,
        total_senders=total_senders,
        emails_sent_today=emails_today,
        followups_sent_today=followups_today,
        replies_today=replies_today,
        bounces_today=bounces_today,
        total_emails_sent=total_sent,
        total_followups_sent=total_followups,
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
        recent_replies=recent_replies,
        sends_last_7_days=sends_last_7_days,
        replies_last_7_days=replies_last_7_days,
        emails_by_day=emails_by_day,
        is_safe_to_send=is_safe,
        safety_warnings=safety_warnings
    )


@router.get("/campaigns/{campaign_id}")
def get_campaign_analytics(campaign_id: int, db: Session = Depends(get_db)):
    """Get detailed analytics for a campaign."""
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # -------------------------
    # Lead status breakdown
    # -------------------------
    # Lead status breakdown (by current lead.status)
    lead_statuses = {}
    for status in LeadStatus:
        count = db.query(Lead).filter(
            Lead.campaign_id == campaign_id,
            Lead.status == status,
        ).count()
        lead_statuses[status.value] = count

    # ---------------------------------------------
    # Per-lead delivery outcome for INITIAL emails
    # ---------------------------------------------
    # We want metrics in terms of UNIQUE LEADS, not raw log rows.
    # "Sent"   -> leads that received at least one successful initial email
    # "Failed" -> leads for which all initial attempts ended in error (FAILED/BOUNCED/CANCELLED)
    # "Invalid"/Bounces -> leads that bounced or were auto-unsubscribed due to invalid address

    success_statuses = {
        EmailStatus.SENT,
        EmailStatus.DELIVERED,
        EmailStatus.OPENED,
        EmailStatus.CLICKED,
        EmailStatus.REPLIED,
    }

    initial_logs = (
        db.query(EmailLog.lead_id, EmailLog.status)
        .filter(
            EmailLog.campaign_id == campaign_id,
            EmailLog.email_type == EmailType.INITIAL,
        )
        .all()
    )

    successful_leads: set[int] = set()
    replied_leads: set[int] = set()
    error_leads: set[int] = set()
    clicked_leads: set[int] = set()

    for lead_id, status in initial_logs:
        if status in success_statuses:
            successful_leads.add(lead_id)
        if status == EmailStatus.REPLIED:
            replied_leads.add(lead_id)
        if status == EmailStatus.CLICKED:
            clicked_leads.add(lead_id)
        if status in (EmailStatus.BOUNCED, EmailStatus.FAILED, EmailStatus.CANCELLED):
            error_leads.add(lead_id)

    # Leads that only have errors (no successful initial email)
    failed_leads = error_leads - successful_leads

    # Leads that are unsubscribed or bounced (invalid / should not be contacted again)
    invalid_leads_from_model = db.query(Lead.id).filter(
        Lead.campaign_id == campaign_id,
        or_(Lead.unsubscribed == True, Lead.bounced == True),
    ).all()
    invalid_lead_ids = {row.id for row in invalid_leads_from_model} | failed_leads

    sent_lead_count = len(successful_leads)
    replied_lead_count = len(replied_leads)
    failed_lead_count = len(failed_leads)
    invalid_lead_count = len(invalid_lead_ids)
    clicked_lead_count = len(clicked_leads)

    # Email status breakdown (per-lead, not raw log counts)
    email_statuses = {
        "sent": sent_lead_count,
        "replied": replied_lead_count,
        "failed": failed_lead_count,
    }
    
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
            # Total emails successfully sent (any status in success_statuses)
            "emails_sent": campaign.emails_sent,
            # Replies counted from logs (per-email, not per-lead)
            "replies": db.query(EmailLog)
            .filter(
                EmailLog.campaign_id == campaign_id,
                EmailLog.status == EmailStatus.REPLIED,
            )
            .count(),
            # Combined invalid leads (bounced OR unsubscribed / invalid address)
            "bounces": invalid_lead_count,
            "unsubscribes": campaign.unsubscribes_count,
        },
        "rates": {
            # Rates are based on unique leads that successfully received an email
            "reply_rate": round(
                (replied_lead_count / max(sent_lead_count, 1)) * 100, 2
            ),
            "bounce_rate": round(
                (invalid_lead_count / max(sent_lead_count, 1)) * 100, 2
            ),
            # Open tracking is not implemented yet
            "open_rate": 0,
            # Click rate: distinct leads that clicked / distinct leads that were sent
            "click_rate": round(
                (clicked_lead_count / max(sent_lead_count, 1)) * 100, 2
            ),
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

