"""
XenFlow Mailer - Lead Model
Stores all lead information with tracking fields
"""

from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, 
    ForeignKey, JSON, Index, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class LeadStatus(str, enum.Enum):
    """Lead status enumeration"""
    NEW = "new"
    QUEUED = "queued"
    CONTACTED = "contacted"
    REPLIED = "replied"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"
    CONVERTED = "converted"
    PAUSED = "paused"


class Lead(Base):
    """
    Lead model for storing prospect information.
    
    Each lead tracks:
    - Contact information
    - Campaign association
    - Follow-up progress (step)
    - Engagement status (replied, bounced, unsubscribed)
    - Custom fields for personalization
    """
    
    __tablename__ = "leads"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Contact information
    email = Column(String(255), nullable=False, index=True)
    name = Column(String(255), nullable=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    company = Column(String(255), nullable=True)
    industry = Column(String(100), nullable=True)
    title = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Custom fields for dynamic placeholders (JSON)
    custom_fields = Column(JSON, default=dict, nullable=False)
    
    # Campaign association
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=True, index=True)
    
    # Status tracking
    status = Column(
        SQLEnum(LeadStatus), 
        default=LeadStatus.NEW, 
        nullable=False,
        index=True
    )
    
    # Follow-up tracking
    step = Column(Integer, default=0, nullable=False)  # Current follow-up step (0 = initial)
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    next_followup_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    # Engagement flags (CRITICAL for safety)
    replied = Column(Boolean, default=False, nullable=False, index=True)
    replied_at = Column(DateTime(timezone=True), nullable=True)
    
    bounced = Column(Boolean, default=False, nullable=False, index=True)
    bounced_at = Column(DateTime(timezone=True), nullable=True)
    bounce_type = Column(String(50), nullable=True)  # "hard" or "soft"
    bounce_count = Column(Integer, default=0, nullable=False)
    
    unsubscribed = Column(Boolean, default=False, nullable=False, index=True)
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Email tracking
    emails_sent = Column(Integer, default=0, nullable=False)
    emails_opened = Column(Integer, default=0, nullable=False)
    links_clicked = Column(Integer, default=0, nullable=False)
    
    # Timezone for send window
    timezone = Column(String(50), default="America/New_York", nullable=False)
    
    # Metadata
    source = Column(String(100), nullable=True)  # How they were imported
    tags = Column(JSON, default=list, nullable=False)
    notes = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="leads")
    email_logs = relationship("EmailLog", back_populates="lead", cascade="all, delete-orphan")
    
    # Indexes for common queries
    __table_args__ = (
        Index("ix_leads_campaign_status", "campaign_id", "status"),
        Index("ix_leads_followup", "campaign_id", "status", "next_followup_at"),
        Index("ix_leads_email_campaign", "email", "campaign_id", unique=True),
    )
    
    @property
    def is_contactable(self) -> bool:
        """Check if lead can receive emails"""
        return (
            not self.replied 
            and not self.bounced 
            and not self.unsubscribed
            and self.status not in [LeadStatus.BOUNCED, LeadStatus.UNSUBSCRIBED, LeadStatus.PAUSED]
        )
    
    @property
    def display_name(self) -> str:
        """Get display name for email personalization"""
        if self.first_name:
            return self.first_name
        if self.name:
            return self.name.split()[0] if self.name else ""
        return ""
    
    def get_placeholder_data(self) -> Dict[str, Any]:
        """Get all data available for template placeholders"""
        data = {
            "name": self.display_name or "there",
            "full_name": self.name or "",
            "first_name": self.first_name or self.display_name or "",
            "last_name": self.last_name or "",
            "email": self.email,
            "company": self.company or "",
            "industry": self.industry or "",
            "title": self.title or "",
        }
        # Merge custom fields
        if self.custom_fields:
            data.update(self.custom_fields)
        return data
    
    def mark_replied(self) -> None:
        """Mark lead as replied (stops all follow-ups)"""
        self.replied = True
        self.replied_at = datetime.utcnow()
        self.status = LeadStatus.REPLIED
        self.next_followup_at = None
    
    def mark_bounced(self, bounce_type: str = "hard") -> None:
        """Mark lead as bounced"""
        self.bounced = True
        self.bounced_at = datetime.utcnow()
        self.bounce_type = bounce_type
        self.bounce_count += 1
        if bounce_type == "hard" or self.bounce_count >= 3:
            self.status = LeadStatus.BOUNCED
            self.next_followup_at = None
    
    def mark_unsubscribed(self) -> None:
        """Mark lead as unsubscribed (legally required to stop)"""
        self.unsubscribed = True
        self.unsubscribed_at = datetime.utcnow()
        self.status = LeadStatus.UNSUBSCRIBED
        self.next_followup_at = None
    
    def __repr__(self) -> str:
        return f"<Lead(id={self.id}, email='{self.email}', status='{self.status}')>"

