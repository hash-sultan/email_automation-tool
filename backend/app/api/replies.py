"""
XenFlow Mailer - Replies API
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from pydantic import BaseModel

from app.database import get_db
from app.models import EmailLog, Lead, Sender, Campaign
from app.models.email_log import EmailStatus
from app.services.email_service import EmailService
from app.utils.logger import get_logger
import re
import base64

logger = get_logger(__name__)
router = APIRouter()


def _decode_base64_body(text: Optional[str]) -> Optional[str]:
    """If text looks like Base64, decode it and return plain text (strip HTML if needed)."""
    if not text or not text.strip():
        return None
    t = text.strip()
    # Base64: alphanumeric, +, /, = only; typically no spaces; min length
    if len(t) < 20 or re.search(r"[^\w+/=]", t):
        return None
    try:
        raw = base64.b64decode(t, validate=True)
        decoded = raw.decode("utf-8", errors="replace").strip()
        if not decoded:
            return None
        # If decoded content is HTML, strip tags for preview
        if "<" in decoded and ">" in decoded:
            decoded = re.sub(r"<[^>]+>", "", decoded)
            decoded = re.sub(r"\s+", " ", decoded).strip()
        return decoded
    except Exception:
        return None


def _strip_mime_headers(text: Optional[str]) -> str:
    """If text looks like raw MIME (boundaries, Content-Type), extract the first real content block."""
    if not text or not text.strip():
        return ""
    t = text.strip()
    # Raw MIME often starts with boundary or Content-* headers
    if re.match(r"^--=?[\w.-]+", t) or re.match(r"^Content-Type:", t, re.I) or re.match(r"^Content-Transfer", t, re.I):
        # Find first double newline and take what's after; then take first block of non-header lines
        parts = re.split(r"\n\s*\n", t, maxsplit=1)
        if len(parts) > 1:
            after_headers = parts[1].strip()
            # Stop at next MIME boundary or header-like line
            lines = []
            for line in after_headers.split("\n"):
                if re.match(r"^--=?[\w.-]+", line.strip()) or re.match(r"^Content-", line.strip(), re.I):
                    break
                lines.append(line)
            return "\n".join(lines).strip()
        return ""
    return t


class ReplyResponse(BaseModel):
    """Reply response schema"""
    id: int
    lead_id: int
    lead_email: str
    lead_name: Optional[str]
    sender_id: int
    sender_email: str
    sender_name: str
    campaign_id: Optional[int]
    campaign_name: Optional[str]
    subject: str
    original_message_id: Optional[str]
    replied_at: Optional[datetime]
    created_at: datetime
    body_text: Optional[str] = None
    body_preview: Optional[str] = None
    
    class Config:
        from_attributes = True


class ReplyListResponse(BaseModel):
    """Paginated replies list"""
    items: List[ReplyResponse]
    total: int
    page: int
    page_size: int
    pages: int


class SendReplyRequest(BaseModel):
    """Request to send a reply"""
    email_log_id: int  # The original email that was replied to
    body_html: str
    body_text: Optional[str] = None
    subject: Optional[str] = None  # If not provided, uses "Re: {original_subject}"


@router.get("/", response_model=ReplyListResponse)
def list_replies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sender_id: Optional[int] = None,
    campaign_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Get all replies with pagination."""
    query = (
        db.query(EmailLog)
        .join(Lead, EmailLog.lead_id == Lead.id)
        .join(Sender, EmailLog.sender_id == Sender.id)
        .filter(EmailLog.status == EmailStatus.REPLIED)
    )
    
    if sender_id:
        query = query.filter(EmailLog.sender_id == sender_id)
    
    if campaign_id:
        query = query.filter(EmailLog.campaign_id == campaign_id)
    
    total = query.count()
    
    replies = (
        query
        .order_by(desc(EmailLog.replied_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    
    # Get campaign names
    campaign_ids = list(set(r.campaign_id for r in replies if r.campaign_id))
    campaigns = {
        c.id: c.name 
        for c in db.query(Campaign).filter(Campaign.id.in_(campaign_ids)).all()
    } if campaign_ids else {}
    
    items = []
    for reply in replies:
        lead = db.query(Lead).filter(Lead.id == reply.lead_id).first()
        sender = db.query(Sender).filter(Sender.id == reply.sender_id).first()

        # Prefer plain text if available; otherwise fall back to HTML truncated
        # Decode Base64 if stored that way; else strip raw MIME so we show actual reply text
        raw_text = reply.body_plain or reply.body_html or ""
        decoded = _decode_base64_body(raw_text)
        if decoded is not None:
            base_text = decoded
        else:
            base_text = _strip_mime_headers(raw_text) or raw_text
        preview = (base_text[:280] + "…") if len(base_text) > 280 else base_text
        
        items.append(ReplyResponse(
            id=reply.id,
            lead_id=reply.lead_id,
            lead_email=reply.to_email,
            lead_name=lead.display_name if lead else None,
            sender_id=reply.sender_id,
            sender_email=sender.email if sender else "",
            sender_name=sender.name if sender else "",
            campaign_id=reply.campaign_id,
            campaign_name=campaigns.get(reply.campaign_id) if reply.campaign_id else None,
            subject=reply.subject,
            original_message_id=reply.message_id,
            replied_at=reply.replied_at,
            created_at=reply.created_at,
            body_text=base_text if base_text else raw_text,
            body_preview=preview
        ))
    
    return ReplyListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.post("/send")
async def send_reply(
    request: SendReplyRequest,
    db: Session = Depends(get_db)
):
    """Send a reply to a lead."""
    # Get the original email log
    original_email = db.query(EmailLog).filter(EmailLog.id == request.email_log_id).first()
    if not original_email:
        raise HTTPException(status_code=404, detail="Original email not found")
    
    if original_email.status != EmailStatus.REPLIED:
        raise HTTPException(status_code=400, detail="This email was not replied to")
    
    # Get lead and sender
    lead = db.query(Lead).filter(Lead.id == original_email.lead_id).first()
    sender = db.query(Sender).filter(Sender.id == original_email.sender_id).first()
    campaign = db.query(Campaign).filter(Campaign.id == original_email.campaign_id).first() if original_email.campaign_id else None
    
    if not lead or not sender:
        raise HTTPException(status_code=404, detail="Lead or sender not found")
    
    # Determine subject
    subject = request.subject or f"Re: {original_email.subject}"
    if not subject.startswith("Re:"):
        subject = f"Re: {subject}"
    
    # Create a temporary template object for the reply
    # The EmailService expects an object with subject, body_html, and body_plain attributes
    class ReplyTemplate:
        def __init__(self, subject, body_html, body_text):
            self.subject = subject
            self.body_html = body_html
            self.body_plain = body_text or body_html.replace('<br>', '\n').replace('<br/>', '\n').replace('<p>', '').replace('</p>', '\n')
    
    reply_template = ReplyTemplate(
        subject=subject,
        body_html=request.body_html,
        body_text=request.body_text
    )
    
    # Use EmailService to send the reply
    # We use followup_step=999 (special value for manual replies) to avoid duplicate check conflicts
    # The in_reply_to and references will make it a proper reply
    email_service = EmailService(db)
    
    try:
        logger.info(
            f"Sending manual reply",
            extra={
                "lead_id": lead.id,
                "lead_email": lead.email,
                "sender_id": sender.id,
                "campaign_id": campaign.id if campaign else None,
                "original_email_id": original_email.id,
                "followup_step": 999
            }
        )
        
        result = await email_service.send_to_lead(
            lead=lead,
            campaign=campaign,
            template=reply_template,
            followup_step=999,  # Special step for manual replies (bypasses duplicate check)
            in_reply_to=original_email.message_id,
            references=original_email.message_id
        )
        
        if result.is_success:
            logger.info(
                f"Manual reply sent successfully",
                extra={
                    "to": lead.email,
                    "sender_id": sender.id,
                    "original_email_id": original_email.id,
                    "message_id": result.message_id
                }
            )
            return {
                "status": "success",
                "message_id": result.message_id,
                "to": lead.email
            }
        else:
            logger.error(
                f"Failed to send manual reply",
                extra={
                    "lead_id": lead.id,
                    "error_code": result.error_code,
                    "error_message": result.error_message,
                    "followup_step": 999
                }
            )
            raise HTTPException(status_code=400, detail=result.error_message)
    finally:
        await email_service.close()
