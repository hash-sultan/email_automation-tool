"""
XenFlow Mailer - Template Models
Email templates with placeholder support
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Template(Base):
    """
    Email template for initial outreach.
    
    Supports dynamic placeholders:
    - {{name}}, {{first_name}}, {{last_name}}
    - {{company}}, {{industry}}, {{title}}
    - {{custom_field}} - any custom field from lead
    """
    
    __tablename__ = "templates"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Template info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Email content
    subject = Column(String(255), nullable=False)
    body_html = Column(Text, nullable=False)
    body_plain = Column(Text, nullable=True)  # Plain text fallback
    
    # Signature (appended to body)
    signature_html = Column(Text, nullable=True)
    signature_plain = Column(Text, nullable=True)
    
    # Template settings
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Track which placeholders are used
    placeholders_used = Column(JSON, default=list, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    campaigns = relationship("Campaign", back_populates="template")
    
    def __repr__(self) -> str:
        return f"<Template(id={self.id}, name='{self.name}')>"


class FollowUpTemplate(Base):
    """
    Follow-up email template.
    
    Each follow-up has:
    - Step number (1, 2, 3, etc.)
    - Delay in days from previous email
    - Subject and body (can reference previous thread)
    """
    
    __tablename__ = "followup_templates"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Campaign association
    campaign_id = Column(Integer, ForeignKey("campaigns.id"), nullable=False, index=True)
    
    # Follow-up sequence
    step = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    
    # Timing
    delay_days = Column(Integer, default=3, nullable=False)  # Days after previous email
    delay_hours = Column(Integer, default=0, nullable=False)  # Additional hours
    
    # Email content
    subject = Column(String(255), nullable=False)  # Can use "Re: {{previous_subject}}"
    body_html = Column(Text, nullable=False)
    body_plain = Column(Text, nullable=True)
    
    # Follow-up specific settings
    reply_to_thread = Column(Boolean, default=True, nullable=False)  # Include in same thread
    
    # Active status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="followup_templates")
    
    def __repr__(self) -> str:
        return f"<FollowUpTemplate(id={self.id}, campaign_id={self.campaign_id}, step={self.step})>"

