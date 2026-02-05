"""
XenFlow Mailer - Campaign Model
Manages email campaigns with safety controls
"""

from datetime import datetime, time
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, JSON, Time, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class CampaignStatus(str, enum.Enum):
    """Campaign status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    STOPPED = "stopped"  # Stopped due to safety threshold


class Campaign(Base):
    """
    Campaign model for managing email outreach campaigns.
    
    Each campaign has:
    - Associated sender account
    - Templates (initial + follow-ups)
    - Send schedule and limits
    - Safety thresholds
    """
    
    __tablename__ = "campaigns"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # Sender association (single-sender mode, backward compatible)
    sender_id = Column(Integer, ForeignKey("senders.id"), nullable=False, index=True)

    # Multi-sender rotation settings
    sender_rotation_enabled = Column(Boolean, default=False, nullable=False)
    max_senders = Column(Integer, nullable=True)
    
    # Initial template (single-template mode)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)

    # Template category (multi-template rotation mode)
    # When set, all active templates in this category are eligible for sending.
    template_category = Column(String(100), nullable=True, index=True)
    
    # Status
    status = Column(
        SQLEnum(CampaignStatus),
        default=CampaignStatus.DRAFT,
        nullable=False,
        index=True
    )
    
    # Schedule settings
    timezone = Column(String(50), default="America/New_York", nullable=False)
    send_window_start = Column(Time, default=time(0, 0), nullable=False)  # 12 AM (24/7)
    send_window_end = Column(Time, default=time(23, 59), nullable=False)  # 11:59 PM (24/7)
    send_weekdays_only = Column(Boolean, default=False, nullable=False)  # Allow weekends
    
    # Rate limits (per campaign, within global limits)
    daily_limit = Column(Integer, default=500, nullable=False)  # Default 500/day, max 1000/day
    hourly_limit = Column(Integer, default=50, nullable=False)  # 50/hour allows 200/day in 4 hours
    min_interval_seconds = Column(Integer, default=10, nullable=False)  # 10 seconds
    max_interval_seconds = Column(Integer, default=10, nullable=False)  # 10 seconds
    
    # Follow-up settings
    followup_enabled = Column(Boolean, default=True, nullable=False)
    max_followup_steps = Column(Integer, default=3, nullable=False)
    followup_delay_days = Column(Integer, default=3, nullable=False)  # Days between follow-ups
    
    # Safety thresholds (campaign-level)
    max_bounce_rate = Column(Integer, default=5, nullable=False)  # 5%
    max_complaint_rate = Column(Integer, default=1, nullable=False)  # 0.1% stored as 1 = 0.1%
    stop_on_threshold = Column(Boolean, default=True, nullable=False)
    
    # Tracking stats
    total_leads = Column(Integer, default=0, nullable=False)
    emails_sent = Column(Integer, default=0, nullable=False)
    followups_sent = Column(Integer, default=0, nullable=False)  # Count of follow-up emails sent
    emails_today = Column(Integer, default=0, nullable=False)
    emails_this_hour = Column(Integer, default=0, nullable=False)
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    last_hour_reset = Column(DateTime(timezone=True), nullable=True)
    
    # Engagement stats
    replies_count = Column(Integer, default=0, nullable=False)
    bounces_count = Column(Integer, default=0, nullable=False)
    unsubscribes_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    sender = relationship("Sender", back_populates="campaigns")
    # When rotation is enabled, use this association instead of sender_id
    campaign_senders = relationship(
        "CampaignSender",
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="CampaignSender.position",
    )
    leads = relationship("Lead", back_populates="campaign", cascade="all, delete-orphan")
    template = relationship("Template", back_populates="campaigns")
    followup_templates = relationship(
        "FollowUpTemplate", 
        back_populates="campaign",
        cascade="all, delete-orphan",
        order_by="FollowUpTemplate.step"
    )
    email_logs = relationship("EmailLog", back_populates="campaign", cascade="all, delete-orphan")
    
    @property
    def bounce_rate(self) -> float:
        """Calculate current bounce rate"""
        if self.emails_sent == 0:
            return 0.0
        return (self.bounces_count / self.emails_sent) * 100
    
    @property
    def reply_rate(self) -> float:
        """Calculate reply rate (capped at 100%)"""
        if self.emails_sent == 0:
            return 0.0
        rate = (self.replies_count / self.emails_sent) * 100
        # Cap at 100% (can't have more replies than emails sent)
        return min(rate, 100.0)
    
    @property
    def is_safe_to_send(self) -> tuple:
        """Check if campaign is within safety thresholds"""
        if self.bounce_rate >= self.max_bounce_rate:
            return False, f"Bounce rate {self.bounce_rate:.1f}% exceeds limit {self.max_bounce_rate}%"
        
        # Complaint rate check removed - campaigns can resume regardless of unsubscribe rate
        
        return True, "Safe"
    
    @property
    def can_send_now(self) -> tuple:
        """Check if we can send right now (rate limits)"""
        # Campaign-level daily limit disabled per user request.
        # Sending is now controlled only by sender-level limits and global safety checks.
        return True, "OK"
    
    def increment_sent(self) -> None:
        """Increment sent counters"""
        self.emails_sent += 1
        self.emails_today += 1
        # Hourly counter removed per user request
        # self.emails_this_hour += 1
        self.last_sent_at = datetime.utcnow()
    
    def reset_daily_counters(self) -> None:
        """Reset daily counters (call at midnight)"""
        self.emails_today = 0
    
    def reset_hourly_counters(self) -> None:
        """Reset hourly counters"""
        self.emails_this_hour = 0
        self.last_hour_reset = datetime.utcnow()
    
    def __repr__(self) -> str:
        return f"<Campaign(id={self.id}, name='{self.name}', status='{self.status}')>"

