"""
XenFlow Mailer - Follow-up Engine
Automated follow-up scheduling and execution
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import pytz

from app.models import Lead, Campaign, EmailLog
from app.models.lead import LeadStatus
from app.models.campaign import CampaignStatus
from app.models.email_log import EmailType, EmailStatus
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class FollowUpEngine:
    """
    Automated follow-up engine with safety controls.
    
    Follow-ups MUST:
    - Only trigger if no reply detected
    - Stop immediately on reply/bounce/unsubscribe
    - Respect per-lead timing rules
    - Support unlimited follow-up steps (user-defined)
    - Log every action
    - Feel human-paced, not robotic
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_leads_ready_for_followup(
        self, 
        campaign_id: int = None,
        limit: int = 100
    ) -> List[Lead]:
        """
        Get leads that are ready for their next follow-up.
        
        Criteria:
        - Lead is contactable (not replied, bounced, unsubscribed)
        - Campaign is active with follow-ups enabled
        - next_followup_at is in the past
        - Current time is within send window
        """
        now = datetime.utcnow()
        
        query = self.db.query(Lead).join(Campaign).filter(
            and_(
                # Lead is contactable
                Lead.replied == False,
                Lead.bounced == False,
                Lead.unsubscribed == False,
                Lead.status.in_([LeadStatus.CONTACTED, LeadStatus.QUEUED]),
                
                # Follow-up is due
                Lead.next_followup_at.isnot(None),
                Lead.next_followup_at <= now,
                
                # Campaign is active with follow-ups
                Campaign.status == CampaignStatus.ACTIVE,
                Campaign.followup_enabled == True,
                
                # Lead hasn't exceeded max steps
                Lead.step < Campaign.max_followup_steps
            )
        )
        
        if campaign_id:
            query = query.filter(Lead.campaign_id == campaign_id)
        
        return query.order_by(Lead.next_followup_at.asc()).limit(limit).all()
    
    def schedule_next_followup(self, lead: Lead, campaign: Campaign) -> Optional[datetime]:
        """
        Schedule the next follow-up for a lead.
        
        Returns the scheduled datetime or None if no more follow-ups.
        """
        # Check if lead can receive more follow-ups
        if not lead.is_contactable:
            logger.debug(f"Lead {lead.email} not contactable, skipping follow-up scheduling")
            return None
        
        # Check if we've reached max steps
        next_step = lead.step + 1
        if next_step > campaign.max_followup_steps:
            logger.debug(f"Lead {lead.email} reached max follow-up steps")
            lead.status = LeadStatus.CONTACTED  # Mark as completed
            lead.next_followup_at = None
            return None
        
        # Get follow-up template for next step
        followup_template = None
        for template in campaign.followup_templates:
            if template.step == next_step and template.is_active:
                followup_template = template
                break
        
        if not followup_template:
            logger.debug(f"No follow-up template for step {next_step}")
            lead.next_followup_at = None
            return None
        
        # Calculate next follow-up time
        base_time = lead.last_sent_at or datetime.utcnow()
        delay_delta = timedelta(
            days=followup_template.delay_days,
            hours=followup_template.delay_hours
        )
        
        next_followup = base_time + delay_delta
        
        # Ensure follow-up is within send window
        next_followup = self._adjust_to_send_window(next_followup, campaign, lead.timezone)
        
        lead.next_followup_at = next_followup
        
        logger.debug(
            f"Scheduled follow-up for {lead.email}",
            extra={
                "lead_id": lead.id,
                "next_step": next_step,
                "scheduled_for": next_followup.isoformat()
            }
        )
        
        return next_followup
    
    def _adjust_to_send_window(
        self, 
        dt: datetime, 
        campaign: Campaign,
        timezone: str = None
    ) -> datetime:
        """
        Adjust datetime to be within the campaign's send window.
        """
        tz = pytz.timezone(timezone or campaign.timezone)
        local_dt = dt.replace(tzinfo=pytz.UTC).astimezone(tz)
        
        send_start = campaign.send_window_start
        send_end = campaign.send_window_end
        
        # If outside send window hours, adjust
        if local_dt.time() < send_start:
            # Before window - set to start of window
            local_dt = local_dt.replace(
                hour=send_start.hour, 
                minute=send_start.minute,
                second=0
            )
        elif local_dt.time() > send_end:
            # After window - set to start of next day's window
            local_dt = local_dt + timedelta(days=1)
            local_dt = local_dt.replace(
                hour=send_start.hour,
                minute=send_start.minute,
                second=0
            )
        
        # Skip weekends if configured
        if campaign.send_weekdays_only:
            while local_dt.weekday() >= 5:  # 5=Saturday, 6=Sunday
                local_dt = local_dt + timedelta(days=1)
        
        # Convert back to UTC
        return local_dt.astimezone(pytz.UTC).replace(tzinfo=None)
    
    def cancel_followups(self, lead: Lead, reason: str = None) -> None:
        """
        Cancel all pending follow-ups for a lead.
        Called on reply, bounce, or unsubscribe.
        """
        lead.next_followup_at = None
        
        logger.info(
            f"Cancelled follow-ups for {lead.email}",
            extra={
                "lead_id": lead.id,
                "reason": reason
            }
        )
    
    def pause_campaign_followups(self, campaign_id: int) -> int:
        """
        Pause all pending follow-ups for a campaign.
        Returns count of affected leads.
        """
        result = self.db.query(Lead).filter(
            and_(
                Lead.campaign_id == campaign_id,
                Lead.next_followup_at.isnot(None)
            )
        ).update(
            {Lead.next_followup_at: None},
            synchronize_session='fetch'
        )
        
        logger.info(f"Paused follow-ups for {result} leads in campaign {campaign_id}")
        return result
    
    def resume_campaign_followups(self, campaign_id: int) -> int:
        """
        Resume follow-ups for a paused campaign.
        Recalculates next follow-up times.
        Only schedules follow-ups for leads that have already received their initial email.
        """
        campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign:
            return 0
        
        # Get leads that had follow-ups paused AND have already received their initial email
        # Only resume follow-ups for leads that have last_sent_at set (initial email was sent)
        leads = self.db.query(Lead).filter(
            and_(
                Lead.campaign_id == campaign_id,
                Lead.replied == False,
                Lead.bounced == False,
                Lead.unsubscribed == False,
                Lead.step < campaign.max_followup_steps,
                Lead.next_followup_at.is_(None),
                Lead.status.in_([LeadStatus.CONTACTED, LeadStatus.QUEUED]),
                Lead.last_sent_at.isnot(None)  # Only leads that have received initial email
            )
        ).all()
        
        count = 0
        for lead in leads:
            if self.schedule_next_followup(lead, campaign):
                count += 1
        
        logger.info(f"Resumed follow-ups for {count} leads in campaign {campaign_id}")
        return count
    
    def get_followup_queue_stats(self, campaign_id: int = None) -> Dict[str, Any]:
        """
        Get statistics about the follow-up queue.
        """
        now = datetime.utcnow()
        
        base_query = self.db.query(Lead).filter(
            Lead.next_followup_at.isnot(None)
        )
        
        if campaign_id:
            base_query = base_query.filter(Lead.campaign_id == campaign_id)
        
        # Count by status
        ready_now = base_query.filter(Lead.next_followup_at <= now).count()
        next_hour = base_query.filter(
            and_(
                Lead.next_followup_at > now,
                Lead.next_followup_at <= now + timedelta(hours=1)
            )
        ).count()
        next_24_hours = base_query.filter(
            and_(
                Lead.next_followup_at > now,
                Lead.next_followup_at <= now + timedelta(hours=24)
            )
        ).count()
        total_scheduled = base_query.count()
        
        # Count by step
        step_counts = {}
        for i in range(1, 11):  # Steps 1-10
            count = base_query.filter(Lead.step == i - 1).count()
            if count > 0:
                step_counts[f"step_{i}"] = count
        
        return {
            "ready_now": ready_now,
            "next_hour": next_hour,
            "next_24_hours": next_24_hours,
            "total_scheduled": total_scheduled,
            "by_step": step_counts
        }
    
    def get_pending_followups(
        self, 
        campaign_id: int = None,
        hours_ahead: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get list of pending follow-ups for preview.
        """
        now = datetime.utcnow()
        
        query = self.db.query(Lead).filter(
            and_(
                Lead.next_followup_at.isnot(None),
                Lead.next_followup_at <= now + timedelta(hours=hours_ahead)
            )
        )
        
        if campaign_id:
            query = query.filter(Lead.campaign_id == campaign_id)
        
        leads = query.order_by(Lead.next_followup_at.asc()).limit(limit).all()
        
        return [
            {
                "lead_id": lead.id,
                "email": lead.email,
                "name": lead.display_name,
                "campaign_id": lead.campaign_id,
                "current_step": lead.step,
                "next_step": lead.step + 1,
                "scheduled_for": lead.next_followup_at.isoformat(),
                "is_ready": lead.next_followup_at <= now
            }
            for lead in leads
        ]

