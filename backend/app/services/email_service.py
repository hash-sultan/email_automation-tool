"""
XenFlow Mailer - Email Service
Central service for sending emails with all safety checks
"""

from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
from jinja2 import Template, Environment, BaseLoader

from sqlalchemy.orm import Session

from app.models import Lead, Campaign, Sender, EmailLog, Suppression, Template as EmailTemplate
from app.models.email_log import EmailType, EmailStatus
from app.models.suppression import SuppressionReason
from app.providers.base import EmailMessage, EmailResult, EmailResultStatus
from app.providers.smtp import SMTPProvider
from app.providers.gmail import GmailProvider
from app.providers.outlook import OutlookProvider
from app.services.rate_limiter import RateLimiter
from app.services.suppression import SuppressionService
from app.config import get_settings, SafetyLimits
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class EmailService:
    """
    Central email service with full safety controls.
    
    Responsibilities:
    - Template rendering with placeholders
    - Provider selection and management
    - Rate limit enforcement
    - Suppression checking
    - Email logging
    - Safety threshold monitoring
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.rate_limiter = RateLimiter()
        self.suppression_service = SuppressionService(db)
        self._providers: Dict[int, Any] = {}  # Cache providers by sender_id
        
        # Jinja2 environment for template rendering
        self.jinja_env = Environment(loader=BaseLoader())
    
    async def send_to_lead(
        self,
        lead: Lead,
        campaign: Campaign,
        template: EmailTemplate = None,
        followup_step: int = 0,
        in_reply_to: str = None,
        references: str = None
    ) -> EmailResult:
        """
        Send email to a lead with full safety checks.
        
        This is the main entry point for sending emails.
        """
        try:
            # Safety check 1: Is lead contactable?
            if not lead.is_contactable:
                logger.warning(f"Lead {lead.email} is not contactable")
                return EmailResult.failed("NOT_CONTACTABLE", f"Lead status: {lead.status}")
            
            # Safety check 2: Is email suppressed?
            if self.suppression_service.is_suppressed(lead.email):
                logger.warning(f"Email {lead.email} is suppressed")
                return EmailResult.failed("SUPPRESSED", "Email is in suppression list")
            
            # Safety check 3: Campaign safety thresholds
            is_safe, reason = campaign.is_safe_to_send
            if not is_safe and campaign.stop_on_threshold:
                logger.error(f"Campaign {campaign.id} unsafe: {reason}")
                return EmailResult.failed("CAMPAIGN_UNSAFE", reason)
            
            # Safety check 4: Can send now (rate limits)?
            can_send, reason = campaign.can_send_now
            if not can_send:
                logger.warning(f"Campaign {campaign.id} rate limited: {reason}")
                return EmailResult.rate_limited(reason)
            
            # Safety check 5: Global safety limits
            sender = campaign.sender
            daily_sent = sender.emails_sent_today
            hourly_sent = sender.emails_sent_this_hour
            bounce_rate = sender.bounce_rate / 100
            complaint_rate = sender.complaint_rate / 100
            
            is_global_safe, global_reason = SafetyLimits.is_safe_to_send(
                daily_sent, hourly_sent, bounce_rate, complaint_rate
            )
            if not is_global_safe:
                logger.error(f"Global safety limit reached: {global_reason}")
                return EmailResult.failed("GLOBAL_LIMIT", global_reason)
            
            # Safety check 6: Rate limiter (Redis-based)
            allowed, wait_time = await self.rate_limiter.check_rate_limit(
                sender_id=sender.id,
                campaign_id=campaign.id
            )
            if not allowed:
                logger.warning(f"Rate limited, wait {wait_time}s")
                return EmailResult.rate_limited(f"Wait {wait_time} seconds")
            
            # Get template (initial or follow-up)
            if followup_step > 0:
                # Get follow-up template
                followup_template = self._get_followup_template(campaign, followup_step)
                if not followup_template:
                    return EmailResult.failed("NO_TEMPLATE", f"No follow-up template for step {followup_step}")
                subject = followup_template.subject
                body_html = followup_template.body_html
                body_plain = followup_template.body_plain
            else:
                # Initial template
                if not template and campaign.template:
                    template = campaign.template
                if not template:
                    return EmailResult.failed("NO_TEMPLATE", "No template configured")
                subject = template.subject
                body_html = template.body_html
                body_plain = template.body_plain
            
            # Render template with lead data
            placeholder_data = lead.get_placeholder_data()
            rendered_subject = self._render_template(subject, placeholder_data)
            rendered_body_html = self._render_template(body_html, placeholder_data)
            rendered_body_plain = self._render_template(body_plain, placeholder_data) if body_plain else None
            
            # Add signature
            if sender.signature_html:
                rendered_body_html += f"\n\n{sender.signature_html}"
            if sender.signature_plain and rendered_body_plain:
                rendered_body_plain += f"\n\n{sender.signature_plain}"
            
            # Build email message
            message = EmailMessage(
                to_email=lead.email,
                to_name=lead.display_name,
                from_email=sender.email,
                from_name=sender.name,
                reply_to=sender.reply_to or sender.email,
                subject=rendered_subject,
                body_html=rendered_body_html,
                body_plain=rendered_body_plain,
                in_reply_to=in_reply_to,
                references=references,
                campaign_id=campaign.id,
                lead_id=lead.id,
                followup_step=followup_step
            )
            
            # Create email log entry
            email_log = EmailLog(
                campaign_id=campaign.id,
                lead_id=lead.id,
                sender_id=sender.id,
                email_type=EmailType.FOLLOWUP if followup_step > 0 else EmailType.INITIAL,
                followup_step=followup_step,
                to_email=lead.email,
                to_name=lead.display_name,
                from_email=sender.email,
                from_name=sender.name,
                reply_to=sender.reply_to or sender.email,
                subject=rendered_subject,
                body_html=rendered_body_html,
                body_plain=rendered_body_plain,
                message_id=message.message_id,
                in_reply_to=in_reply_to,
                references=references,
                status=EmailStatus.SENDING
            )
            self.db.add(email_log)
            self.db.flush()
            
            # Get provider and send
            provider = await self._get_provider(sender)
            result = await provider.send_email(message)
            
            # Update email log with result
            if result.is_success:
                email_log.mark_sent(message.message_id, result.provider_message_id)
                
                # Update counters
                sender.increment_sent()
                campaign.increment_sent()
                lead.emails_sent += 1
                lead.step = followup_step
                lead.last_sent_at = datetime.utcnow()
                
                # Record rate limit
                await self.rate_limiter.record_send(sender.id, campaign.id)
                
                logger.info(
                    f"Email sent successfully",
                    extra={
                        "to": lead.email,
                        "campaign_id": campaign.id,
                        "step": followup_step,
                        "message_id": message.message_id
                    }
                )
            
            elif result.is_bounced:
                email_log.mark_bounced(
                    bounce_type=result.error_code,
                    code=result.error_code,
                    message=result.error_message
                )
                
                # Handle bounce
                await self._handle_bounce(lead, campaign, sender, result)
            
            else:
                email_log.status = EmailStatus.FAILED
                email_log.error_message = result.error_message
                email_log.retry_count += 1
                
                logger.error(
                    f"Email send failed",
                    extra={
                        "to": lead.email,
                        "error": result.error_message
                    }
                )
            
            self.db.commit()
            return result
            
        except Exception as e:
            self.db.rollback()
            logger.exception(f"Email service error: {str(e)}")
            return EmailResult.failed("INTERNAL_ERROR", str(e))
    
    def _render_template(self, template_str: str, data: Dict[str, Any]) -> str:
        """
        Render template with placeholder data.
        Supports {{placeholder}} syntax.
        """
        if not template_str:
            return ""
        
        try:
            # Convert {{placeholder}} to Jinja2 syntax
            jinja_template = template_str.replace('{{', '{{ ').replace('}}', ' }}')
            template = self.jinja_env.from_string(jinja_template)
            return template.render(**data)
        except Exception as e:
            logger.warning(f"Template rendering error: {str(e)}")
            return template_str
    
    def _get_followup_template(self, campaign: Campaign, step: int):
        """Get follow-up template for a specific step."""
        for template in campaign.followup_templates:
            if template.step == step and template.is_active:
                return template
        return None
    
    async def _get_provider(self, sender: Sender):
        """
        Get or create email provider for sender.
        Caches providers for reuse.
        """
        if sender.id in self._providers:
            provider = self._providers[sender.id]
            if provider.is_connected:
                return provider
        
        # Create new provider based on type
        if sender.provider_type.value == "gmail":
            provider = GmailProvider(
                sender_email=sender.email,
                sender_name=sender.name,
                access_token=sender.oauth_access_token,
                refresh_token=sender.oauth_refresh_token,
                client_id=settings.GMAIL_CLIENT_ID,
                client_secret=settings.GMAIL_CLIENT_SECRET,
                token_expiry=sender.oauth_token_expiry
            )
        elif sender.provider_type.value == "outlook":
            provider = OutlookProvider(
                sender_email=sender.email,
                sender_name=sender.name,
                access_token=sender.oauth_access_token,
                refresh_token=sender.oauth_refresh_token,
                client_id=settings.GMAIL_CLIENT_ID,  # Should be separate Outlook credentials
                client_secret=settings.GMAIL_CLIENT_SECRET,
                token_expiry=sender.oauth_token_expiry
            )
        else:  # Custom SMTP
            provider = SMTPProvider(
                sender_email=sender.email,
                sender_name=sender.name,
                smtp_host=sender.smtp_host,
                smtp_port=sender.smtp_port,
                smtp_username=sender.smtp_username,
                smtp_password=sender.smtp_password_encrypted,  # Should be decrypted
                use_tls=sender.smtp_use_tls
            )
        
        # Connect
        await provider.connect()
        self._providers[sender.id] = provider
        
        return provider
    
    async def _handle_bounce(
        self, 
        lead: Lead, 
        campaign: Campaign, 
        sender: Sender, 
        result: EmailResult
    ) -> None:
        """Handle email bounce."""
        # Determine bounce type
        is_hard_bounce = 'invalid' in (result.error_message or '').lower() or \
                        'not exist' in (result.error_message or '').lower() or \
                        result.error_code in ['550', '551', '552', '553', '554']
        
        bounce_type = "hard" if is_hard_bounce else "soft"
        
        # Update lead
        lead.mark_bounced(bounce_type)
        
        # Update campaign stats
        campaign.bounces_count += 1
        
        # Update sender stats
        sender.total_bounces += 1
        
        # Add to suppression list if hard bounce
        if is_hard_bounce:
            self.suppression_service.add_suppression(
                email=lead.email,
                reason=SuppressionReason.HARD_BOUNCE,
                source=f"campaign_{campaign.id}",
                campaign_id=campaign.id,
                error_code=result.error_code,
                error_message=result.error_message
            )
        
        logger.warning(
            f"Bounce handled",
            extra={
                "email": lead.email,
                "bounce_type": bounce_type,
                "campaign_id": campaign.id
            }
        )
    
    async def close(self) -> None:
        """Close all provider connections."""
        for provider in self._providers.values():
            await provider.disconnect()
        self._providers.clear()

