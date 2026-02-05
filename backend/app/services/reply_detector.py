"""
XenFlow Mailer - Reply Detector
IMAP-based reply detection for automatic follow-up stopping
"""

import asyncio
import email
from email.header import decode_header
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import re
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import Lead, EmailLog, Sender, Campaign
from app.models.lead import LeadStatus
from app.models.email_log import EmailStatus
from app.config import get_settings
from app.utils.logger import get_logger

try:
    import aioimaplib
    IMAP_AVAILABLE = True
except ImportError:
    IMAP_AVAILABLE = False
    aioimaplib = None

logger = get_logger(__name__)
settings = get_settings()


class ReplyDetector:
    """
    IMAP-based reply detection system.
    
    Monitors inbox for replies to sent emails and:
    - Marks leads as replied
    - Cancels pending follow-ups
    - Updates campaign statistics
    - Detects unsubscribe requests
    
    Reply detection is CRITICAL for:
    - Stopping follow-ups (don't annoy people who replied)
    - Accurate campaign statistics
    - Sender reputation (responding to replies shows engagement)
    """
    
    # Common unsubscribe keywords/phrases
    UNSUBSCRIBE_PATTERNS = [
        r'\bunsubscribe\b',
        r'\bremove\s+me\b',
        r'\bstop\s+emailing\b',
        r'\bopt\s*out\b',
        r'\bdo\s+not\s+contact\b',
        r'\btake\s+me\s+off\b',
        r'\bno\s+longer\s+interested\b'
    ]
    
    def __init__(self, db: Session):
        self.db = db
        self._imap_clients: Dict[int, Any] = {}
    
    async def check_replies_for_sender(
        self, 
        sender: Sender,
        since_hours: int = 24
    ) -> List[Dict[str, Any]]:
        """
        Check for new replies for a specific sender.
        
        Returns list of detected replies with details.
        """
        if not IMAP_AVAILABLE:
            logger.warning("aioimaplib not installed, skipping IMAP check")
            return []
        
        if not sender.imap_host or not sender.imap_username:
            logger.debug(f"No IMAP config for sender {sender.email}")
            return []
        
        detected_replies = []
        
        try:
            # Connect to IMAP
            imap = aioimaplib.IMAP4_SSL(
                host=sender.imap_host,
                port=sender.imap_port or 993,
                timeout=30
            )
            
            await imap.wait_hello_from_server()
            await imap.login(sender.imap_username, sender.imap_password_encrypted)
            
            # Select inbox
            await imap.select(sender.imap_folder or "INBOX")
            
            # Search for recent emails
            since_date = (datetime.utcnow() - timedelta(hours=since_hours)).strftime("%d-%b-%Y")
            
            # Search for emails that might be replies
            # Look for emails with In-Reply-To header or RE: in subject
            status, data = await imap.search(f'SINCE {since_date}')
            
            if status != 'OK' or not data[0]:
                await imap.logout()
                return []
            
            message_ids = data[0].split()
            
            logger.info(
                f"Found {len(message_ids)} messages to check for sender {sender.email}",
                extra={"since_hours": since_hours}
            )
            
            # Check recent messages (last 100 to avoid timeout)
            # Track processed reply Message-IDs to avoid processing the same reply multiple times
            processed_reply_message_ids = set()
            checked_count = 0
            processed_count = 0
            for msg_id in message_ids[-100:]:  # Limit to last 100 messages
                checked_count += 1
                reply = await self._process_email(imap, msg_id.decode(), sender)
                if reply:
                    # Get the reply's Message-ID to deduplicate
                    reply_message_id = reply.get('reply_message_id')
                    if reply_message_id and reply_message_id in processed_reply_message_ids:
                        # This reply email was already processed, skip to avoid duplicate counting
                        logger.debug(
                            f"Skipping duplicate reply email: {reply_message_id}",
                            extra={"from": reply.get('from_email')}
                        )
                        continue
                    
                    # Track this reply message ID to prevent processing the same reply email twice
                    if reply_message_id:
                        processed_reply_message_ids.add(reply_message_id)
                    
                    detected_replies.append(reply)
                    processed_count += 1
                    logger.info(
                        f"Reply detected from {reply.get('from_email')}",
                        extra={
                            "email_log_id": reply.get('email_log_id'),
                            "subject": reply.get('subject', '')[:50]
                        }
                    )
            
            logger.info(
                f"Checked {checked_count} messages, found {len(detected_replies)} replies",
                extra={"checked": checked_count, "found": len(detected_replies)}
            )
            
            await imap.logout()
            
        except Exception as e:
            logger.error(f"IMAP error for sender {sender.email}: {str(e)}")
        
        # Process detected replies
        for reply in detected_replies:
            await self._handle_reply(reply, sender)
        
        logger.info(
            f"Reply check complete for {sender.email}",
            extra={"replies_found": len(detected_replies)}
        )
        
        return detected_replies
    
    async def _process_email(
        self, 
        imap, 
        msg_id: str, 
        sender: Sender
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single email to check if it's a reply.
        """
        try:
            status, data = await imap.fetch(msg_id, '(RFC822.HEADER)')
            
            if status != 'OK':
                return None
            
            # Parse headers
            header_data = data[1]
            if isinstance(header_data, tuple):
                header_data = header_data[1]
            
            msg = email.message_from_bytes(header_data)
            
            # Helper to normalize message IDs (remove angle brackets, trim whitespace)
            def normalize_msg_id(msg_id: str) -> str:
                if not msg_id:
                    return ""
                return msg_id.strip('<> ').strip()
            
            # Extract relevant headers
            from_email = self._extract_email(msg.get('From', ''))
            subject = self._decode_header(msg.get('Subject', ''))
            in_reply_to = msg.get('In-Reply-To', '')
            references = msg.get('References', '')
            message_id = msg.get('Message-ID', '')
            reply_message_id = normalize_msg_id(message_id) if message_id else None
            date_str = msg.get('Date', '')
            
            # Skip if from our own sender
            if from_email.lower() == sender.email.lower():
                return None
            
            # Check if this is a reply to one of our emails
            original_message_id = None
            
            if in_reply_to:
                original_message_id = normalize_msg_id(in_reply_to)
            elif references:
                # Get the first (original) message ID from references
                ref_ids = references.split()
                if ref_ids:
                    original_message_id = normalize_msg_id(ref_ids[0])
            
            # Try to find matching email log by message ID
            email_log = None
            if original_message_id:
                # Normalize the original_message_id for comparison
                normalized_original = normalize_msg_id(original_message_id)
                
                # Get all email logs for this sender and check normalized IDs
                # This is more reliable than SQL comparison with angle brackets
                all_logs = self.db.query(EmailLog).filter(
                    EmailLog.sender_id == sender.id,
                    EmailLog.message_id.isnot(None)
                ).all()
                
                for log in all_logs:
                    normalized_log_id = normalize_msg_id(log.message_id)
                    if normalized_log_id == normalized_original:
                        email_log = log
                        logger.debug(
                            f"Matched reply by message ID",
                            extra={
                                "original": original_message_id,
                                "matched_log_id": log.id,
                                "from": from_email
                            }
                        )
                        break
                
                # Fallback: Try LIKE match if exact match failed
                if not email_log:
                    email_log = self.db.query(EmailLog).filter(
                        EmailLog.message_id.like(f"%{normalized_original}%")
                    ).first()
            
            # If still not found, try subject matching
            if not email_log and subject.lower().startswith('re:'):
                original_subject = subject[3:].strip()
                # Remove common reply prefixes (Re:, RE:, Fwd:, etc.)
                original_subject = re.sub(r'^(re|fwd?):\s*', '', original_subject, flags=re.IGNORECASE).strip()
                
                # Try to find matching sent email by subject and recipient
                email_log = self.db.query(EmailLog).filter(
                    and_(
                        EmailLog.sender_id == sender.id,
                        EmailLog.to_email.ilike(from_email),  # Case-insensitive
                        EmailLog.subject.ilike(f"%{original_subject}%")  # Partial match
                    )
                ).order_by(EmailLog.sent_at.desc()).first()  # Get most recent match
                
                if email_log:
                    logger.info(
                        f"Reply matched by subject: '{subject}' -> '{email_log.subject}'",
                        extra={
                            "from": from_email,
                            "to": email_log.to_email,
                            "email_log_id": email_log.id
                        }
                    )
            
            # If still not found, try matching by recipient email and sender
            # This is a fallback for cases where headers are missing
            if not email_log:
                # Look for any email sent to this person from this sender recently
                email_log = self.db.query(EmailLog).filter(
                    and_(
                        EmailLog.sender_id == sender.id,
                        EmailLog.to_email.ilike(from_email),
                        EmailLog.sent_at >= datetime.utcnow() - timedelta(days=7)  # Within last 7 days
                    )
                ).order_by(EmailLog.sent_at.desc()).first()
                
                if email_log:
                    logger.info(
                        f"Reply matched by recipient fallback: {from_email}",
                        extra={
                            "email_log_id": email_log.id,
                            "subject": subject
                        }
                    )
            
            if not email_log:
                # Only log debug for potential replies (has Re: or headers)
                if subject.lower().startswith('re:') or in_reply_to or references:
                    logger.debug(
                        f"No matching email log found for potential reply",
                        extra={
                            "from": from_email,
                            "subject": subject[:50],
                            "in_reply_to": in_reply_to[:50] if in_reply_to else None,
                            "references": references[:100] if references else None
                        }
                    )
                return None
            
            # Get full message and parse to extract clean body (avoid raw MIME in preview)
            body_text = ""
            body_html_text = ""
            status, full_data = await imap.fetch(msg_id, '(RFC822)')
            if status == 'OK' and full_data and full_data[0]:
                raw = full_data[0]
                if isinstance(raw, tuple):
                    raw = raw[1]
                try:
                    if isinstance(raw, bytes):
                        full_msg = email.message_from_bytes(raw)
                    else:
                        full_msg = email.message_from_string(str(raw))
                    body_text, body_html_text = self._extract_body_from_message(full_msg)
                except Exception as e:
                    logger.debug(f"Failed to parse reply body: {e}")
            
            # Extract just the reply portion (remove quoted original message)
            # Common patterns: "On ... wrote:", "-----Original Message-----", etc.
            if body_text:
                # Split on common reply separators
                reply_separators = [
                    '\nOn ',  # "On [date] [name] wrote:"
                    '\n-----Original Message-----',
                    '\nFrom: ',
                    '\n> ',
                    '\n________________________________',
                    '\n---',
                ]
                
                # Find the first separator and take everything before it
                reply_text = body_text
                for separator in reply_separators:
                    if separator in body_text:
                        parts = body_text.split(separator, 1)
                        if len(parts) > 0:
                            reply_text = parts[0].strip()
                            break
                
                # If we couldn't find a separator, use the full text but limit length
                # (very long emails are likely mostly quoted text)
                if reply_text == body_text and len(body_text) > 2000:
                    # Take first 1000 chars as likely reply
                    reply_text = body_text[:1000].strip()
                
                body_text = reply_text
            
            # Check if this is an error message (bounce, "address not found", etc.) - NOT a real reply
            body_lower = body_text.lower()
            subject_lower = subject.lower()
            error_keywords = [
                'address not found', 'message blocked', 'user not found',
                'mailbox not found', 'no such user', 'invalid recipient',
                'recipient address rejected', 'delivery failure', 'undeliverable',
                'mail delivery failed', 'returned mail', 'bounce', '550', '5.1.1', '5.4.1',
                'message could not be delivered', 'delivery status notification'
            ]
            
            # Check subject and body for error indicators
            is_error_message = any(keyword in subject_lower or keyword in body_lower for keyword in error_keywords)
            
            if is_error_message:
                logger.debug(
                    f"Skipping error message as reply: {from_email} - {subject[:50]}",
                    extra={
                        "from": from_email,
                        "subject": subject[:50],
                        "email_log_id": email_log.id if email_log else None
                    }
                )
                return None  # Don't treat error messages as replies
            
            # Check for unsubscribe intent
            is_unsubscribe = self._check_unsubscribe_intent(subject + " " + body_text)
            
            return {
                "from_email": from_email,
                "subject": subject,
                "original_message_id": original_message_id,
                "reply_message_id": reply_message_id,  # For deduplication
                "email_log_id": email_log.id,
                "lead_id": email_log.lead_id,
                "campaign_id": email_log.campaign_id,
                "is_unsubscribe": is_unsubscribe,
                "received_at": date_str,
                "body_text": body_text,  # This is now the extracted reply text only
                "body_html": body_html_text,  # Store HTML version too
            }
            
        except Exception as e:
            logger.error(f"Error processing email {msg_id}: {str(e)}")
            return None
    
    async def _handle_reply(self, reply: Dict[str, Any], sender: Sender) -> None:
        """
        Handle a detected reply - update lead and campaign.
        Counts each unique reply email, even if multiple replies match the same email_log.
        """
        lead_id = reply.get('lead_id')
        campaign_id = reply.get('campaign_id')
        email_log_id = reply.get('email_log_id')
        reply_message_id = reply.get('reply_message_id')
        is_unsubscribe = reply.get('is_unsubscribe', False)
        body_text = reply.get('body_text', '')
        body_html = reply.get('body_html', '')
        
        # Get email_log
        email_log = None
        if email_log_id:
            email_log = self.db.query(EmailLog).filter(EmailLog.id == email_log_id).first()
        
        # Check if this reply has already been processed (email_log already marked as replied)
        # This prevents counting the same reply multiple times across different check runs
        is_new_reply = email_log is None or email_log.replied_at is None
        
        # Mark email_log as replied (if not already replied)
        # This stops follow-ups and stores the reply body for UI
        if email_log and is_new_reply:
            email_log.mark_replied()
            
            # Store the REPLY body (not the original email we sent)
            # We store the reply in body_plain, and keep the original email in body_html
            # This way we can show the reply text in the UI
            if body_text and body_text.strip():
                # Store the extracted reply text (without quoted original)
                email_log.body_plain = body_text.strip()
            elif body_html and body_html.strip():
                # Fallback: if no plain text, extract from HTML
                import re
                import html
                plain_from_html = html.unescape(re.sub(r'<[^>]+>', '', body_html))
                if plain_from_html.strip():
                    email_log.body_plain = plain_from_html.strip()
            
            # Store HTML version of reply if available (for rich formatting)
            # Note: This overwrites the original email HTML, but that's OK since
            # we want to show the reply in the UI, not what we sent
            if body_html and body_html.strip():
                email_log.body_html = body_html.strip()
        
        # Update lead (only if not already replied)
        if lead_id:
            lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
            if lead and not lead.replied:
                if is_unsubscribe:
                    lead.mark_unsubscribed()
                    logger.info(f"Lead {lead.email} unsubscribed via reply")
                else:
                    lead.mark_replied()
                    logger.info(f"Reply detected from {lead.email}")
        
        # Only increment campaign count if this is a new reply (not already processed)
        # This prevents counting the same reply multiple times across different check runs
        if campaign_id and is_new_reply:
            campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if campaign:
                if is_unsubscribe:
                    campaign.unsubscribes_count += 1
                else:
                    campaign.replies_count += 1
                    logger.debug(
                        f"Incremented reply count for campaign {campaign_id}",
                        extra={
                            "campaign_id": campaign_id,
                            "email_log_id": email_log_id,
                            "reply_message_id": reply_message_id
                        }
                    )
        elif campaign_id and not is_new_reply:
            logger.debug(
                f"Skipping reply count increment - email_log {email_log_id} already marked as replied",
                extra={
                    "campaign_id": campaign_id,
                    "email_log_id": email_log_id,
                    "reply_message_id": reply_message_id
                }
            )
        
        self.db.commit()
    
    def _extract_email(self, from_header: str) -> str:
        """Extract email address from From header."""
        match = re.search(r'<([^>]+)>', from_header)
        if match:
            return match.group(1).lower()
        # If no angle brackets, might be just the email
        return from_header.strip().lower()
    
    def _decode_header(self, header: str) -> str:
        """Decode email header (handle encodings)."""
        if not header:
            return ""
        
        decoded_parts = decode_header(header)
        result = []
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    part = part.decode(encoding or 'utf-8', errors='ignore')
                except:
                    part = str(part)
            result.append(part)
        
        return ''.join(result)

    def _extract_body_from_message(self, msg: email.message.Message) -> Tuple[str, str]:
        """
        Extract plain text and HTML body from a parsed email message.
        Walks MIME parts and returns decoded content only (no MIME headers/boundaries).
        """
        plain = ""
        html = ""
        for part in msg.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            ctype = (part.get_content_type() or "").lower()
            if ctype == 'text/plain' and not plain:
                raw = part.get_payload(decode=True)
                if raw:
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        plain = raw.decode(charset, errors='replace').strip()
                    except Exception:
                        plain = raw.decode('utf-8', errors='replace').strip()
            elif ctype == 'text/html' and not html:
                raw = part.get_payload(decode=True)
                if raw:
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        html = raw.decode(charset, errors='replace').strip()
                    except Exception:
                        html = raw.decode('utf-8', errors='replace').strip()
        if html and not plain:
            plain = re.sub(r'<[^>]+>', '', html)
            plain = re.sub(r'\s+', ' ', plain).strip()
        return (plain, html)
    
    def _check_unsubscribe_intent(self, text: str) -> bool:
        """Check if text contains unsubscribe intent."""
        text_lower = text.lower()
        
        for pattern in self.UNSUBSCRIBE_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        
        return False
    
    def check_replies_sync(self, sender_id: int) -> List[Dict[str, Any]]:
        """
        Synchronous wrapper for reply checking.
        Use this from Celery workers.
        """
        sender = self.db.query(Sender).filter(Sender.id == sender_id).first()
        if not sender:
            return []
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(self.check_replies_for_sender(sender))
        finally:
            loop.close()
    
    def mark_reply_manual(
        self, 
        lead_id: int, 
        is_unsubscribe: bool = False
    ) -> bool:
        """
        Manually mark a lead as replied/unsubscribed.
        """
        lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
        if not lead:
            return False
        
        if is_unsubscribe:
            lead.mark_unsubscribed()
        else:
            lead.mark_replied()
        
        # Update campaign stats
        if lead.campaign_id:
            campaign = self.db.query(Campaign).filter(
                Campaign.id == lead.campaign_id
            ).first()
            if campaign:
                if is_unsubscribe:
                    campaign.unsubscribes_count += 1
                else:
                    campaign.replies_count += 1
        
        self.db.commit()
        
        logger.info(
            f"Manual reply marked for lead {lead.email}",
            extra={"is_unsubscribe": is_unsubscribe}
        )
        
        return True

