"""
XenFlow Mailer - Email Log Model
Complete audit trail of all email activity
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class EmailStatus(str, enum.Enum):
    """Email delivery status"""
    QUEUED = "queued"
    SENDING = "sending"
    SENT = "sent"
    DELIVERED = "delivered"
    OPENED = "opened"
    CLICKED = "clicked"
    REPLIED = "replied"
    BOUNCED = "bounced"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BounceType(str, enum.Enum):
    """Bounce classification"""
    HARD = "hard"  # Permanent - invalid email, domain doesn't exist
    SOFT = "soft"  # Temporary - mailbox full, server down
    COMPLAINT = "complaint"  # Marked as spam
    UNSUBSCRIBE = "unsubscribe"


class EmailType(str, enum.Enum):
    """Type of email sent"""
    INITIAL = "initial"
    FOLLOWUP = "followup"


class EmailLog(Base):
    """
    Email log for complete audit trail.
    
    Tracks:
    - Every email sent
    - Delivery status
    - Bounces and errors
    - Opens and clicks (if tracking enabled)
    - Full message details for debugging
    """
    
    __tablename__ = "email_logs"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Associations
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True, index=True)
    sender_id = Column(Integer, ForeignKey("senders.id"), nullable=True, index=True)
    
    # Email type
    email_type = Column(
        SQLEnum(EmailType),
        default=EmailType.INITIAL,
        nullable=False
    )
    followup_step = Column(Integer, default=0, nullable=False)  # 0 for initial, 1+ for follow-ups
    
    # Recipient info
    to_email = Column(String(255), nullable=False, index=True)
    to_name = Column(String(255), nullable=True)
    from_email = Column(String(255), nullable=False)
    from_name = Column(String(255), nullable=True)
    reply_to = Column(String(255), nullable=True)
    
    # Email content
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=True)
    body_plain = Column(Text, nullable=True)
    
    # Headers (for threading, etc.)
    message_id = Column(String(255), nullable=True, unique=True, index=True)
    in_reply_to = Column(String(255), nullable=True)  # For follow-ups in thread
    references = Column(Text, nullable=True)  # Message IDs for threading
    
    # Status tracking
    status = Column(
        SQLEnum(EmailStatus),
        default=EmailStatus.QUEUED,
        nullable=False,
        index=True
    )
    
    # Timing
    queued_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)
    replied_at = Column(DateTime(timezone=True), nullable=True)
    
    # Bounce/Error info
    bounced_at = Column(DateTime(timezone=True), nullable=True)
    bounce_type = Column(SQLEnum(BounceType), nullable=True)
    bounce_code = Column(String(50), nullable=True)  # SMTP error code
    bounce_message = Column(Text, nullable=True)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Provider response
    provider_message_id = Column(String(255), nullable=True)  # ID from Gmail/SMTP
    provider_response = Column(JSON, nullable=True)
    
    # Tracking
    open_count = Column(Integer, default=0, nullable=False)
    click_count = Column(Integer, default=0, nullable=False)
    tracking_pixel_url = Column(String(500), nullable=True)
    
    # Extra data
    extra_data = Column(JSON, default=dict, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="email_logs")
    lead = relationship("Lead", back_populates="email_logs")
    sender = relationship("Sender", back_populates="email_logs")
    
    # Indexes
    __table_args__ = (
        Index("ix_email_logs_campaign_status", "campaign_id", "status"),
        Index("ix_email_logs_sent_at", "sent_at"),
        Index("ix_email_logs_to_email_sent", "to_email", "sent_at"),
    )
    
    @property
    def is_delivered(self) -> bool:
        """Check if email was successfully delivered"""
        return self.status in [
            EmailStatus.DELIVERED, 
            EmailStatus.OPENED, 
            EmailStatus.CLICKED,
            EmailStatus.REPLIED
        ]
    
    @property
    def is_failed(self) -> bool:
        """Check if email failed"""
        return self.status in [EmailStatus.BOUNCED, EmailStatus.FAILED]
    
    def mark_sent(self, message_id: str = None, provider_id: str = None) -> None:
        """Mark email as sent"""
        self.status = EmailStatus.SENT
        self.sent_at = datetime.utcnow()
        if message_id:
            self.message_id = message_id
        if provider_id:
            self.provider_message_id = provider_id
    
    def mark_bounced(self, bounce_type: BounceType, code: str = None, message: str = None) -> None:
        """Mark email as bounced"""
        self.status = EmailStatus.BOUNCED
        self.bounced_at = datetime.utcnow()
        self.bounce_type = bounce_type
        self.bounce_code = code
        self.bounce_message = message
    
    def mark_replied(self) -> None:
        """Mark email as replied"""
        self.status = EmailStatus.REPLIED
        self.replied_at = datetime.utcnow()
    
    def __repr__(self) -> str:
        return f"<EmailLog(id={self.id}, to='{self.to_email}', status='{self.status}')>"

