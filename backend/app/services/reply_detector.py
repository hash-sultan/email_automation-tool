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
            
            for msg_id in message_ids[-100:]:  # Limit to last 100 messages
                reply = await self._process_email(imap, msg_id.decode(), sender)
                if reply:
                    detected_replies.append(reply)
            
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
            
            # Extract relevant headers
            from_email = self._extract_email(msg.get('From', ''))
            subject = self._decode_header(msg.get('Subject', ''))
            in_reply_to = msg.get('In-Reply-To', '')
            references = msg.get('References', '')
            message_id = msg.get('Message-ID', '')
            date_str = msg.get('Date', '')
            
            # Skip if from our own sender
            if from_email.lower() == sender.email.lower():
                return None
            
            # Check if this is a reply to one of our emails
            original_message_id = None
            
            if in_reply_to:
                original_message_id = in_reply_to.strip('<> ')
            elif references:
                # Get the first (original) message ID from references
                ref_ids = references.split()
                if ref_ids:
                    original_message_id = ref_ids[0].strip('<> ')
            
            if not original_message_id:
                # Check if subject starts with Re: and matches a sent email
                if subject.lower().startswith('re:'):
                    original_subject = subject[3:].strip()
                    # Try to find matching sent email
                    email_log = self.db.query(EmailLog).filter(
                        and_(
                            EmailLog.sender_id == sender.id,
                            EmailLog.to_email == from_email,
                            EmailLog.subject == original_subject
                        )
                    ).first()
                    
                    if email_log:
                        original_message_id = email_log.message_id
                else:
                    return None
            
            # Verify this message ID is from one of our sent emails
            email_log = self.db.query(EmailLog).filter(
                EmailLog.message_id == original_message_id
            ).first()
            
            if not email_log:
                return None
            
            # Get email body to check for unsubscribe
            status, body_data = await imap.fetch(msg_id, '(BODY[TEXT])')
            body_text = ""
            if status == 'OK' and body_data[1]:
                body_bytes = body_data[1]
                if isinstance(body_bytes, tuple):
                    body_bytes = body_bytes[1]
                try:
                    body_text = body_bytes.decode('utf-8', errors='ignore')
                except:
                    body_text = str(body_bytes)
            
            # Check for unsubscribe intent
            is_unsubscribe = self._check_unsubscribe_intent(subject + " " + body_text)
            
            return {
                "from_email": from_email,
                "subject": subject,
                "original_message_id": original_message_id,
                "email_log_id": email_log.id,
                "lead_id": email_log.lead_id,
                "campaign_id": email_log.campaign_id,
                "is_unsubscribe": is_unsubscribe,
                "received_at": date_str
            }
            
        except Exception as e:
            logger.error(f"Error processing email {msg_id}: {str(e)}")
            return None
    
    async def _handle_reply(self, reply: Dict[str, Any], sender: Sender) -> None:
        """
        Handle a detected reply - update lead and campaign.
        """
        lead_id = reply.get('lead_id')
        campaign_id = reply.get('campaign_id')
        email_log_id = reply.get('email_log_id')
        is_unsubscribe = reply.get('is_unsubscribe', False)
        
        if lead_id:
            lead = self.db.query(Lead).filter(Lead.id == lead_id).first()
            if lead and not lead.replied:
                if is_unsubscribe:
                    lead.mark_unsubscribed()
                    logger.info(f"Lead {lead.email} unsubscribed via reply")
                else:
                    lead.mark_replied()
                    logger.info(f"Reply detected from {lead.email}")
        
        if campaign_id:
            campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
            if campaign:
                if is_unsubscribe:
                    campaign.unsubscribes_count += 1
                else:
                    campaign.replies_count += 1
        
        if email_log_id:
            email_log = self.db.query(EmailLog).filter(EmailLog.id == email_log_id).first()
            if email_log:
                email_log.mark_replied()
        
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

