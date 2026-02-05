"""
XenFlow Mailer - Email Service
Central service for sending emails with all safety checks
"""

from typing import Optional, Dict, Any
from datetime import datetime
import asyncio
from jinja2 import Template, Environment, BaseLoader
from urllib.parse import quote
from email_validator import validate_email, EmailNotValidError

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
        references: str = None,
    ) -> EmailResult:
        """
        Send email to a lead with full safety checks.

        This is the main entry point for sending emails.
        """
        try:
            # CRITICAL: Lock lead row to prevent race conditions (SELECT FOR UPDATE)
            # This ensures only one email can be sent to a lead at a time
            # Use NOWAIT to fail fast if another process has the lock (prevents deadlocks)
            try:
                locked_lead = (
                    self.db.query(Lead)
                    .filter(Lead.id == lead.id)
                    .with_for_update(nowait=True)
                    .first()
                )
            except Exception as lock_error:
                # Handle lock errors gracefully - another worker is processing this lead
                # This is normal with concurrent workers processing the same campaign
                error_str = str(lock_error)
                if "LockNotAvailable" in error_str or "could not obtain lock" in error_str.lower():
                    logger.debug(
                        f"Could not acquire lock for lead {lead.id}, another process is sending (this is normal with concurrent workers)",
                        extra={
                            "lead_id": lead.id,
                            "campaign_id": campaign.id if campaign else None,
                            "error": error_str
                        }
                    )
                    return EmailResult.failed("LOCKED", "Lead is being processed by another task")
                else:
                    # Re-raise if it's a different error
                    raise
            
            if not locked_lead:
                logger.warning(f"Could not acquire lock for lead {lead.id}, another process may be sending")
                return EmailResult.failed("LOCKED", "Lead is being processed by another task")
            
            # Refresh lead from locked row
            self.db.refresh(locked_lead)
            lead = locked_lead
            
            # CRITICAL: Duplicate prevention - check email_logs directly (most reliable)
            # Check if this exact step has already been sent for this lead
            # Skip duplicate check for manual replies (followup_step >= 999)
            logger.debug(
                f"Checking duplicate for lead {lead.email}",
                extra={
                    "lead_id": lead.id,
                    "campaign_id": campaign.id if campaign else None,
                    "followup_step": followup_step,
                    "template_provided": template is not None
                }
            )
            
            if followup_step < 999:
                # Build query - handle case where campaign might be None
                query = self.db.query(EmailLog).filter(
                    EmailLog.lead_id == lead.id,
                    EmailLog.followup_step == followup_step,
                    EmailLog.status.in_([EmailStatus.SENT, EmailStatus.REPLIED, EmailStatus.SENDING])
                )
                
                # Only filter by campaign_id if campaign exists
                if campaign:
                    query = query.filter(EmailLog.campaign_id == campaign.id)
                else:
                    query = query.filter(EmailLog.campaign_id.is_(None))
                
                existing_email = query.first()
                
                if existing_email:
                    logger.info(
                        f"Lead {lead.email} already has email for step {followup_step} (log_id: {existing_email.id}), skipping duplicate",
                        extra={
                            "lead_id": lead.id,
                            "campaign_id": campaign.id if campaign else None,
                            "followup_step": followup_step,
                            "existing_log_id": existing_email.id
                        }
                    )
                    return EmailResult.failed("DUPLICATE", f"Email for step {followup_step} already sent")
            else:
                logger.debug(
                    f"Skipping duplicate check for manual reply (followup_step={followup_step})",
                    extra={
                        "lead_id": lead.id,
                        "campaign_id": campaign.id if campaign else None,
                        "followup_step": followup_step
                    }
                )
            
            # Safety check 0: Validate email format before sending
            # This catches invalid emails that might have been imported before validation was added
            try:
                validate_email(lead.email, check_deliverability=False)
            except EmailNotValidError as e:
                logger.warning(
                    f"Invalid email format for lead {lead.id}: {lead.email} - {str(e)}",
                    extra={
                        "lead_id": lead.id,
                        "email": lead.email,
                        "error": str(e)
                    }
                )
                # Mark lead as bounced and add to suppression list
                lead.bounced = True
                lead.bounce_type = "hard"
                lead.bounced_at = datetime.utcnow()
                lead.status = "bounced"
                self.suppression_service.add_suppression(
                    email=lead.email,
                    reason=SuppressionReason.INVALID_EMAIL,
                    source="email_validation"
                )
                self.db.commit()
                return EmailResult.failed("INVALID_EMAIL", f"Invalid email format: {str(e)}")
            
            # Safety check 1: Is lead contactable?
            # Skip this check for manual replies (followup_step >= 999) - we want to allow replies to replied leads
            # BUT still check for critical statuses (unsubscribed, bounced) even for manual replies
            if followup_step < 999:
                # Full contactable check for automated emails
                if not lead.is_contactable:
                    logger.warning(f"Lead {lead.email} is not contactable")
                    return EmailResult.failed("NOT_CONTACTABLE", f"Lead status: {lead.status}")
            else:
                # For manual replies, only check critical statuses (compliance/legal)
                # Use string comparison to avoid import issues
                if lead.unsubscribed or lead.status == "unsubscribed":
                    logger.warning(f"Lead {lead.email} has unsubscribed - cannot send even manual reply")
                    return EmailResult.failed("UNSUBSCRIBED", "Lead has unsubscribed - cannot send")
                if lead.status == "bounced":
                    logger.warning(f"Lead {lead.email} has bounced - risky to send manual reply")
                    # Allow but log warning - user explicitly wants to send
                    logger.info(f"Allowing manual reply to bounced lead {lead.email} (user override)")

            # Safety check 2: Is email suppressed?
            # ALWAYS check suppression list - critical for compliance and reputation
            # Suppression list includes spam complaints, hard bounces, etc.
            if self.suppression_service.is_suppressed(lead.email):
                logger.warning(f"Email {lead.email} is in suppression list")
                return EmailResult.failed("SUPPRESSED", "Email is in suppression list - cannot send")

            # Safety check 3: Campaign status (must be ACTIVE)
            # Skip campaign status check for manual replies - user explicitly wants to send
            if followup_step < 999 and campaign:
                from app.models.campaign import CampaignStatus
                if campaign.status != CampaignStatus.ACTIVE:
                    logger.warning(f"Campaign {campaign.id} is not active (status: {campaign.status}), cannot send")
                    return EmailResult.failed("CAMPAIGN_NOT_ACTIVE", f"Campaign status: {campaign.status}")
                
                is_safe, reason = campaign.is_safe_to_send
                if not is_safe and campaign.stop_on_threshold:
                    logger.error(f"Campaign {campaign.id} unsafe: {reason}")
                    return EmailResult.failed("CAMPAIGN_UNSAFE", reason)

                # Safety check 4: Can send now (rate limits)?
                # Hourly limit removed per user request
                can_send, reason = campaign.can_send_now
                if not can_send:
                    logger.warning(f"Campaign {campaign.id} rate limited: {reason}")
                    return EmailResult.rate_limited(reason)

            # Choose sender (single or multi-sender rotation)
            sender = self._choose_sender_for_campaign(campaign)
            
            # Calculate number of senders in rotation for adaptive rate limiting
            num_rotation_senders = 1
            if getattr(campaign, "sender_rotation_enabled", False) and getattr(campaign, "campaign_senders", None):
                num_rotation_senders = len(campaign.campaign_senders) or 1

            # Safety check 5: Global safety limits for chosen sender
            # Skip global safety limits for manual replies - user explicitly wants to send
            if followup_step < 999:
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

                # Safety check 6: Rate limiter (Redis-based) with adaptive settings
                # Adaptive delays and batch pause based on rotation count
                # Skip rate limiting for manual replies - user explicitly wants to send
                if campaign:
                    # Campaign-level daily limits disabled; only sender-level limits apply.
                    allowed, wait_time = await self.rate_limiter.check_rate_limit(
                        sender_id=sender.id,
                        campaign_id=campaign.id,
                        num_rotation_senders=num_rotation_senders,
                        sender_daily_limit=sender.current_daily_limit,
                        campaign_daily_limit=None,
                    )
                    if not allowed:
                        logger.warning(f"Rate limited, wait {wait_time}s (rotation: {num_rotation_senders} senders)")
                        return EmailResult.rate_limited(f"Wait {wait_time} seconds")

            # Choose template (initial or follow-up)
            # If template is explicitly provided, use it (for manual replies, etc.)
            if template:
                # Use the provided template directly
                subject = template.subject
                body_html = template.body_html
                body_plain = template.body_plain
            elif followup_step > 0:
                # Follow-up email - MUST use follow-up templates only
                if getattr(campaign, "template_category", None):
                    # Category-based follow-up rotation
                    from app.models import Template as CategoryTemplate

                    followup_templates = (
                        self.db.query(CategoryTemplate)
                        .filter(
                            CategoryTemplate.category == campaign.template_category,
                            CategoryTemplate.template_type == "followup",
                            CategoryTemplate.template_type.isnot(None),  # Ensure not None
                            CategoryTemplate.is_active == True,
                        )
                        .order_by(CategoryTemplate.created_at.asc())
                        .all()
                    )

                    if not followup_templates:
                        return EmailResult.failed(
                            "NO_TEMPLATE",
                            f"No active follow-up templates in category '{campaign.template_category}'",
                        )

                    # Validate all templates are actually follow-up type
                    invalid_templates = [t for t in followup_templates if t.template_type != "followup"]
                    if invalid_templates:
                        logger.error(
                            f"Found {len(invalid_templates)} templates with wrong type in follow-up query",
                            extra={
                                "campaign_id": campaign.id,
                                "category": campaign.template_category,
                                "invalid_template_ids": [t.id for t in invalid_templates]
                            }
                        )

                    import random

                    followup_template = random.choice(followup_templates)
                    
                    # CRITICAL: Verify selected template is actually a follow-up template
                    if followup_template.template_type != "followup":
                        logger.error(
                            f"Selected template {followup_template.id} has wrong type: {followup_template.template_type} (expected 'followup')",
                            extra={
                                "template_id": followup_template.id,
                                "template_name": followup_template.name,
                                "template_type": followup_template.template_type,
                                "campaign_id": campaign.id,
                                "lead_id": lead.id,
                                "followup_step": followup_step
                            }
                        )
                        return EmailResult.failed(
                            "INVALID_TEMPLATE",
                            f"Selected template '{followup_template.name}' is not a follow-up template (type: {followup_template.template_type})"
                        )
                    
                    logger.debug(
                        "Selected follow-up template for rotation",
                        extra={
                            "template_id": followup_template.id,
                            "template_name": followup_template.name,
                            "template_type": followup_template.template_type,
                            "campaign_id": campaign.id,
                            "lead_id": lead.id,
                            "category": campaign.template_category,
                            "available_templates": len(followup_templates),
                            "followup_step": followup_step,
                        },
                    )
                else:
                    # Legacy per-campaign follow-up templates
                    followup_template = self._get_followup_template(campaign, followup_step)
                    if not followup_template:
                        return EmailResult.failed(
                            "NO_TEMPLATE", f"No follow-up template for step {followup_step}"
                        )

                subject = followup_template.subject
                body_html = followup_template.body_html
                body_plain = followup_template.body_plain
            else:
                # Initial email (followup_step == 0) - MUST use initial templates only
                if getattr(campaign, "template_category", None):
                    # Category-based initial rotation
                    from app.models import Template as CategoryTemplate

                    initial_templates = (
                        self.db.query(CategoryTemplate)
                        .filter(
                            CategoryTemplate.category == campaign.template_category,
                            CategoryTemplate.template_type == "initial",
                            CategoryTemplate.template_type.isnot(None),  # Ensure not None
                            CategoryTemplate.is_active == True,
                        )
                        .order_by(CategoryTemplate.created_at.asc())
                        .all()
                    )

                    if not initial_templates:
                        return EmailResult.failed(
                            "NO_TEMPLATE",
                            f"No active initial templates in category '{campaign.template_category}'",
                        )

                    # Validate all templates are actually initial type
                    invalid_templates = [t for t in initial_templates if t.template_type != "initial"]
                    if invalid_templates:
                        logger.error(
                            f"Found {len(invalid_templates)} templates with wrong type in initial query",
                            extra={
                                "campaign_id": campaign.id,
                                "category": campaign.template_category,
                                "invalid_template_ids": [t.id for t in invalid_templates]
                            }
                        )

                    import random

                    template = random.choice(initial_templates)
                    
                    # CRITICAL: Verify selected template is actually an initial template
                    if template.template_type != "initial":
                        logger.error(
                            f"Selected template {template.id} has wrong type: {template.template_type} (expected 'initial')",
                            extra={
                                "template_id": template.id,
                                "template_name": template.name,
                                "template_type": template.template_type,
                                "campaign_id": campaign.id,
                                "lead_id": lead.id,
                                "followup_step": followup_step
                            }
                        )
                        return EmailResult.failed(
                            "INVALID_TEMPLATE",
                            f"Selected template '{template.name}' is not an initial template (type: {template.template_type})"
                        )
                    
                    logger.debug(
                        "Selected initial template for rotation",
                        extra={
                            "template_id": template.id,
                            "template_name": template.name,
                            "template_type": template.template_type,
                            "campaign_id": campaign.id,
                            "lead_id": lead.id,
                            "category": campaign.template_category,
                            "available_templates": len(initial_templates),
                            "followup_step": followup_step,
                        },
                    )
                else:
                    # Legacy single-template mode
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
            rendered_body_plain = (
                self._render_template(body_plain, placeholder_data) if body_plain else None
            )

            # Add signature
            if sender.signature_html:
                rendered_body_html += f"\n\n{sender.signature_html}"
            if sender.signature_plain and rendered_body_plain:
                rendered_body_plain += f"\n\n{sender.signature_plain}"

            # Wrap links with tracking URL for click tracking (HTML only)
            try:
                if rendered_body_html:
                    from bs4 import BeautifulSoup  # type: ignore

                    soup = BeautifulSoup(rendered_body_html, "html.parser")
                    for a_tag in soup.find_all("a", href=True):
                        href = a_tag.get("href")
                        # Skip mailto:, tel:, and already-tracked links
                        if not href or href.startswith(("mailto:", "tel:")):
                            continue
                        if "/api/v1/tracking/click" in href:
                            continue

                        base_url = settings.PUBLIC_BASE_URL.rstrip("/")
                        # EmailLog is not created yet; use a placeholder and update after flush
                        # We'll temporarily store the destination URL in a data attribute
                        # and replace it after we know email_log.id
                        a_tag["data-xen-dest"] = href
                        a_tag["href"] = f"{base_url}{settings.API_PREFIX}/tracking/click/__LOG_ID__?u={quote(href)}"

                    rendered_body_html = str(soup)
            except Exception as e:
                logger.warning(f"Failed to wrap links for click tracking: {e}")

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
                followup_step=followup_step,
            )

            # Reuse existing QUEUED log (created by send_bulk_emails_task) or create new
            existing_queued = (
                self.db.query(EmailLog)
                .filter(
                    EmailLog.lead_id == lead.id,
                    EmailLog.campaign_id == campaign.id,
                    EmailLog.followup_step == followup_step,
                    EmailLog.status == EmailStatus.QUEUED,
                )
                .first()
            )
            if existing_queued:
                email_log = existing_queued
                email_log.sender_id = sender.id
                email_log.email_type = EmailType.FOLLOWUP if followup_step > 0 else EmailType.INITIAL
                email_log.to_email = lead.email
                email_log.to_name = lead.display_name
                email_log.from_email = sender.email
                email_log.from_name = sender.name
                email_log.reply_to = sender.reply_to or sender.email
                email_log.subject = rendered_subject
                email_log.body_html = rendered_body_html
                email_log.body_plain = rendered_body_plain
                email_log.message_id = message.message_id
                email_log.in_reply_to = in_reply_to
                email_log.references = references
                email_log.status = EmailStatus.SENDING
                self.db.flush()
            else:
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
                    status=EmailStatus.SENDING,
                )
                self.db.add(email_log)
                self.db.flush()

            # Now that we know email_log.id, replace placeholder __LOG_ID__ in HTML
            if email_log.id and rendered_body_html and "__LOG_ID__" in rendered_body_html:
                base_url = settings.PUBLIC_BASE_URL.rstrip("/")
                rendered_body_html = rendered_body_html.replace(
                    f"{base_url}{settings.API_PREFIX}/tracking/click/__LOG_ID__",
                    f"{base_url}{settings.API_PREFIX}/tracking/click/{email_log.id}",
                )
                email_log.body_html = rendered_body_html

            # Get provider and send
            provider = await self._get_provider(sender)
            result = await provider.send_email(message)

            # Update email log with result
            if result.is_success:
                email_log.mark_sent(message.message_id, result.provider_message_id)

                # CRITICAL: Use atomic database updates for counters to prevent race conditions
                # This ensures counters are always accurate even with concurrent sends
                from sqlalchemy.sql import func
                
                # Atomic increment for campaign counter
                update_dict = {
                    Campaign.emails_sent: Campaign.emails_sent + 1,
                    Campaign.emails_today: Campaign.emails_today + 1,
                    # Hourly counter removed per user request
                    Campaign.last_sent_at: func.now()
                }
                
                # Increment followups_sent if this is a follow-up email
                if followup_step > 0:
                    update_dict[Campaign.followups_sent] = Campaign.followups_sent + 1
                
                self.db.query(Campaign).filter(Campaign.id == campaign.id).update(
                    update_dict, synchronize_session=False
                )
                
                # Atomic increment for sender counter
                from app.models.sender import Sender
                self.db.query(Sender).filter(Sender.id == sender.id).update({
                    Sender.emails_sent_today: Sender.emails_sent_today + 1,
                    Sender.emails_sent_this_hour: Sender.emails_sent_this_hour + 1,
                    Sender.total_emails_sent: Sender.total_emails_sent + 1
                }, synchronize_session=False)
                
                # Update lead (using locked row)
                lead.emails_sent += 1
                lead.step = followup_step
                lead.last_sent_at = datetime.utcnow()

                # Update lead status to CONTACTED if this was the initial email
                if followup_step == 0:
                    lead.status = "contacted"  # Use string value instead of enum

                # Record rate limit with rotation count for adaptive batch pause
                await self.rate_limiter.record_send(
                    sender.id, 
                    campaign.id,
                    num_rotation_senders=num_rotation_senders
                )

                # Schedule next follow-up if this was an initial email (step 0)
                if followup_step == 0 and campaign.followup_enabled:
                    from app.workers.followup_worker import schedule_followup_task
                    schedule_followup_task.delay(lead.id, campaign.id)

                logger.info(
                    "Email sent successfully",
                    extra={
                        "to": lead.email,
                        "campaign_id": campaign.id,
                        "step": followup_step,
                        "message_id": message.message_id,
                    },
                )

            elif result.is_bounced:
                email_log.mark_bounced(
                    bounce_type=result.error_code,
                    code=result.error_code,
                    message=result.error_message,
                )

                # Handle bounce
                await self._handle_bounce(lead, campaign, sender, result)

            elif result.status.value == "rate_limited":
                # Gmail daily limit hit - pause this sender temporarily
                email_log.status = EmailStatus.FAILED
                email_log.error_message = result.error_message
                email_log.retry_count += 1
                
                # Pause sender temporarily (will be reactivated at midnight)
                from app.models.sender import SenderStatus
                sender.status = SenderStatus.PAUSED
                logger.warning(
                    f"Pausing sender {sender.id} ({sender.email}) due to Gmail daily limit",
                    extra={
                        "sender_id": sender.id,
                        "sender_email": sender.email,
                        "error": result.error_message
                    }
                )

            else:
                email_log.status = EmailStatus.FAILED
                email_log.error_message = result.error_message
                email_log.retry_count += 1

                # If failure is SMTP connection/auth, mark sender as disconnected so UI shows correct status
                err = (result.error_message or "").lower()
                if any(
                    x in err
                    for x in (
                        "failed to connect to smtp",
                        "please log in with your web browser",
                        "534",
                        "535",
                        "connection lost",
                        "authentication failed",
                        "invalid credentials",
                    )
                ):
                    from app.models.sender import SenderStatus
                    sender.connection_error = (result.error_message or "SMTP connection failed")[:2000]
                    sender.status = SenderStatus.DISCONNECTED
                    logger.warning(
                        f"Marked sender {sender.id} ({sender.email}) as disconnected due to SMTP error",
                        extra={"sender_id": sender.id, "error": result.error_message},
                    )

                logger.error(
                    "Email send failed",
                    extra={
                        "to": lead.email,
                        "error": result.error_message,
                    },
                )

            self.db.commit()
            return result

        except Exception as e:
            self.db.rollback()
            logger.exception(f"Email service error: {str(e)}")
            return EmailResult.failed("INTERNAL_ERROR", str(e))

    def _choose_sender_for_campaign(self, campaign: Campaign) -> Sender:
        """
        Select an appropriate sender for this campaign.

        - If rotation is disabled or no rotation senders configured, fall back to campaign.sender
        - If rotation is enabled, pick the least-used sender (by emails_sent_today)
          that is allowed to send based on sender.can_send and global safety limits.
        """
        # Simple single-sender mode (backwards compatible)
        if not getattr(campaign, "sender_rotation_enabled", False) or not getattr(
            campaign, "campaign_senders", None
        ):
            if not campaign.sender:
                raise ValueError("No sender configured for campaign")
            return campaign.sender

        from collections import defaultdict

        sender_ids = [cs.sender_id for cs in campaign.campaign_senders]
        if not sender_ids:
            if not campaign.sender:
                raise ValueError("No senders configured for rotation")
            return campaign.sender

        # Load sender records
        senders = (
            self.db.query(Sender)
            .filter(Sender.id.in_(sender_ids))
            .all()
        )
        if not senders:
            if not campaign.sender:
                raise ValueError("No valid senders found for campaign")
            return campaign.sender

        # Order by emails_sent_today (least used first)
        ordered_senders = sorted(senders, key=lambda s: s.emails_sent_today or 0)

        # Pick first sender that can send and passes global safety checks
        # Skip senders that are paused (e.g., hit Gmail limit)
        for sender in ordered_senders:
            # Skip paused senders (they hit limits and should be temporarily disabled)
            if sender.status == "paused":
                logger.debug(
                    f"Skipping paused sender {sender.id} ({sender.email})",
                    extra={"sender_id": sender.id, "sender_email": sender.email}
                )
                continue
            
            can_send, _reason = sender.can_send
            if not can_send:
                continue

            daily_sent = sender.emails_sent_today
            hourly_sent = sender.emails_sent_this_hour
            bounce_rate = sender.bounce_rate / 100
            complaint_rate = sender.complaint_rate / 100

            is_safe, _global_reason = SafetyLimits.is_safe_to_send(
                daily_sent, hourly_sent, bounce_rate, complaint_rate
            )
            if not is_safe:
                continue

            return sender

        # Fallback: if none are safe, use primary sender to surface error
        if campaign.sender:
            return campaign.sender
        raise ValueError("No eligible senders available for campaign")
    
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
        from app.services.bounce_handler import BounceHandler
        
        bounce_handler = BounceHandler(self.db)
        error_msg = (result.error_message or '').lower()
        
        # Classify bounce using bounce handler
        bounce_type, suppression_reason = bounce_handler.classify_bounce(
            error_code=result.error_code,
            error_message=result.error_message
        )
        
        # Update lead - mark as bounced
        lead.mark_bounced(bounce_type.value)
        
        # For "address not found" or "message blocked" errors, also mark as unsubscribed
        if any(keyword in error_msg for keyword in ['address not found', 'message blocked', 'user not found']):
            lead.unsubscribed = True
            lead.unsubscribed_at = datetime.utcnow()
            campaign.unsubscribes_count += 1
            logger.info(
                f"Marked lead as unsubscribed due to address error: {lead.email}",
                extra={"lead_id": lead.id, "campaign_id": campaign.id}
            )
        
        # Update campaign stats
        campaign.bounces_count += 1
        
        # Update sender stats
        sender.total_bounces += 1
        
        # Add to suppression list if hard bounce
        if bounce_type.value == "hard" or bounce_type.value == "complaint":
            self.suppression_service.add_suppression(
                email=lead.email,
                reason=suppression_reason,
                source=f"campaign_{campaign.id}",
                campaign_id=campaign.id,
                error_code=result.error_code,
                error_message=result.error_message
            )
        
        logger.warning(
            f"Bounce handled",
            extra={
                "email": lead.email,
                "bounce_type": bounce_type.value,
                "campaign_id": campaign.id
            }
        )
    
    async def close(self) -> None:
        """Close all provider connections."""
        for provider in self._providers.values():
            await provider.disconnect()
        self._providers.clear()

