"""
XenFlow Mailer - Bounce Handler
Bounce classification and suppression management
"""

from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import Lead, Sender, Campaign, EmailLog, Suppression
from app.models.lead import LeadStatus
from app.models.email_log import BounceType, EmailStatus
from app.models.suppression import SuppressionReason
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class BounceHandler:
    """
    Bounce classification and handling.
    
    Hard Bounces (permanent):
    - Invalid email address
    - Domain doesn't exist
    - Mailbox doesn't exist
    → Immediately suppress
    
    Soft Bounces (temporary):
    - Mailbox full
    - Server temporarily unavailable
    - Message too large
    → Allow retries, suppress after 3 attempts
    
    Complaints:
    - Marked as spam
    → Immediately suppress, high priority
    """
    
    # SMTP error codes that indicate hard bounces
    HARD_BOUNCE_CODES = [
        '550',  # Mailbox unavailable
        '551',  # User not local
        '552',  # Exceeded storage
        '553',  # Mailbox name invalid
        '554',  # Transaction failed
        '500',  # Syntax error
        '501',  # Syntax error in parameters
        '503',  # Bad sequence
        '521',  # Domain does not accept mail
        '541',  # Recipient rejected
        '556',  # Domain not accepting mail
    ]
    
    # Keywords in error messages indicating hard bounces
    HARD_BOUNCE_KEYWORDS = [
        'invalid',
        'not exist',
        'does not exist',
        'user unknown',
        'mailbox not found',
        'no such user',
        'unknown user',
        'rejected',
        'blocked',
        'blacklisted',
        'permanently rejected',
        'address rejected',
        'bad destination',
    ]
    
    # Keywords indicating soft bounces
    SOFT_BOUNCE_KEYWORDS = [
        'temporarily',
        'try again',
        'retry',
        'mailbox full',
        'quota exceeded',
        'over quota',
        'too many',
        'rate limit',
        'service unavailable',
        'connection timeout',
        'server busy',
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def classify_bounce(
        self, 
        error_code: str = None, 
        error_message: str = None
    ) -> Tuple[BounceType, SuppressionReason]:
        """
        Classify a bounce as hard or soft based on error code and message.
        
        Returns (BounceType, SuppressionReason)
        """
        error_code = error_code or ""
        error_message = (error_message or "").lower()
        
        # Check for hard bounce codes
        for code in self.HARD_BOUNCE_CODES:
            if code in error_code:
                return BounceType.HARD, SuppressionReason.HARD_BOUNCE
        
        # Check for hard bounce keywords
        for keyword in self.HARD_BOUNCE_KEYWORDS:
            if keyword in error_message:
                return BounceType.HARD, SuppressionReason.HARD_BOUNCE
        
        # Check for soft bounce keywords
        for keyword in self.SOFT_BOUNCE_KEYWORDS:
            if keyword in error_message:
                return BounceType.SOFT, SuppressionReason.SOFT_BOUNCE_LIMIT
        
        # Check for spam complaints
        if 'spam' in error_message or 'complaint' in error_message:
            return BounceType.COMPLAINT, SuppressionReason.COMPLAINT
        
        # Default to soft bounce (safer assumption)
        return BounceType.SOFT, SuppressionReason.SOFT_BOUNCE_LIMIT
    
    def handle_bounce(
        self,
        lead: Lead,
        campaign: Campaign,
        sender: Sender,
        error_code: str = None,
        error_message: str = None
    ) -> Dict[str, Any]:
        """
        Handle a bounced email.
        
        Returns action taken and details.
        """
        bounce_type, suppression_reason = self.classify_bounce(error_code, error_message)
        
        result = {
            "lead_id": lead.id,
            "email": lead.email,
            "bounce_type": bounce_type.value,
            "action": None,
            "suppressed": False
        }
        
        if bounce_type == BounceType.HARD or bounce_type == BounceType.COMPLAINT:
            # Immediate suppression
            lead.mark_bounced(bounce_type="hard")
            
            # Add to suppression list
            self._add_suppression(
                email=lead.email,
                reason=suppression_reason,
                campaign_id=campaign.id,
                error_code=error_code,
                error_message=error_message
            )
            
            result["action"] = "suppressed"
            result["suppressed"] = True
            
            logger.warning(
                f"Hard bounce suppressed: {lead.email}",
                extra={
                    "lead_id": lead.id,
                    "campaign_id": campaign.id,
                    "bounce_type": bounce_type.value
                }
            )
        
        else:
            # Soft bounce - increment counter
            lead.bounce_count += 1
            lead.bounced_at = datetime.utcnow()
            
            if lead.bounce_count >= settings.SOFT_BOUNCE_THRESHOLD:
                # Too many soft bounces - suppress
                lead.mark_bounced(bounce_type="soft")
                
                self._add_suppression(
                    email=lead.email,
                    reason=SuppressionReason.SOFT_BOUNCE_LIMIT,
                    campaign_id=campaign.id,
                    error_code=error_code,
                    error_message=f"Soft bounce limit reached ({lead.bounce_count})"
                )
                
                result["action"] = "suppressed_after_threshold"
                result["suppressed"] = True
                
                logger.warning(
                    f"Soft bounce limit reached: {lead.email}",
                    extra={"bounce_count": lead.bounce_count}
                )
            else:
                result["action"] = "recorded"
                
                logger.info(
                    f"Soft bounce recorded: {lead.email}",
                    extra={
                        "bounce_count": lead.bounce_count,
                        "threshold": settings.SOFT_BOUNCE_THRESHOLD
                    }
                )
        
        # Update campaign stats
        campaign.bounces_count += 1
        
        # Update sender stats
        sender.total_bounces += 1
        
        # Check if campaign should stop due to bounce rate
        if campaign.stop_on_threshold:
            bounce_rate = (campaign.bounces_count / max(campaign.emails_sent, 1)) * 100
            if bounce_rate >= campaign.max_bounce_rate:
                from app.models.campaign import CampaignStatus
                campaign.status = CampaignStatus.STOPPED
                result["campaign_stopped"] = True
                
                logger.error(
                    f"Campaign stopped due to high bounce rate",
                    extra={
                        "campaign_id": campaign.id,
                        "bounce_rate": bounce_rate
                    }
                )
        
        self.db.commit()
        return result
    
    def _add_suppression(
        self,
        email: str,
        reason: SuppressionReason,
        campaign_id: int = None,
        error_code: str = None,
        error_message: str = None
    ) -> Suppression:
        """Add email to suppression list."""
        # Check if already exists
        existing = self.db.query(Suppression).filter(
            Suppression.email == email.lower()
        ).first()
        
        if existing:
            existing.bounce_count += 1
            existing.updated_at = datetime.utcnow()
            return existing
        
        suppression = Suppression(
            email=email.lower(),
            reason=reason,
            source=f"bounce_handler",
            campaign_id=campaign_id,
            error_code=error_code,
            error_message=error_message
        )
        
        self.db.add(suppression)
        return suppression
    
    def process_bounce_notification(
        self,
        email: str,
        bounce_type: str,
        diagnostic_code: str = None,
        timestamp: datetime = None
    ) -> Optional[Dict[str, Any]]:
        """
        Process bounce notification from external source (webhook, etc.)
        """
        # Find the lead
        lead = self.db.query(Lead).filter(
            and_(
                Lead.email == email.lower(),
                Lead.bounced == False
            )
        ).first()
        
        if not lead:
            # Lead not found or already bounced
            # Still add to suppression if hard bounce
            if bounce_type.lower() == 'hard':
                self._add_suppression(
                    email=email,
                    reason=SuppressionReason.HARD_BOUNCE,
                    error_code=diagnostic_code,
                    error_message=f"External bounce notification: {bounce_type}"
                )
                self.db.commit()
            return None
        
        # Find associated campaign and sender
        campaign = None
        sender = None
        
        if lead.campaign_id:
            campaign = self.db.query(Campaign).filter(
                Campaign.id == lead.campaign_id
            ).first()
            if campaign:
                sender = campaign.sender
        
        if not campaign or not sender:
            # Just suppress without full handling
            lead.mark_bounced(bounce_type.lower())
            self._add_suppression(
                email=email,
                reason=SuppressionReason.HARD_BOUNCE if bounce_type.lower() == 'hard' else SuppressionReason.SOFT_BOUNCE_LIMIT,
                error_code=diagnostic_code
            )
            self.db.commit()
            return {"action": "suppressed", "email": email}
        
        return self.handle_bounce(
            lead=lead,
            campaign=campaign,
            sender=sender,
            error_code=diagnostic_code,
            error_message=f"External notification: {bounce_type}"
        )
    
    def get_bounce_stats(self, campaign_id: int = None) -> Dict[str, Any]:
        """
        Get bounce statistics.
        """
        query = self.db.query(EmailLog).filter(
            EmailLog.status == EmailStatus.BOUNCED
        )
        
        if campaign_id:
            query = query.filter(EmailLog.campaign_id == campaign_id)
        
        total_bounces = query.count()
        hard_bounces = query.filter(EmailLog.bounce_type == BounceType.HARD).count()
        soft_bounces = query.filter(EmailLog.bounce_type == BounceType.SOFT).count()
        complaints = query.filter(EmailLog.bounce_type == BounceType.COMPLAINT).count()
        
        return {
            "total": total_bounces,
            "hard": hard_bounces,
            "soft": soft_bounces,
            "complaints": complaints,
            "hard_rate": round((hard_bounces / max(total_bounces, 1)) * 100, 2),
            "soft_rate": round((soft_bounces / max(total_bounces, 1)) * 100, 2)
        }

