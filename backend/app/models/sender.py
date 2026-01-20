"""
XenFlow Mailer - Sender Model
Email sender accounts with provider configuration
"""

from datetime import datetime, date
from typing import Optional
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    JSON, Date, Enum as SQLEnum
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.ext.hybrid import hybrid_property
import enum

from app.database import Base


class ProviderType(str, enum.Enum):
    """Supported email provider types"""
    GMAIL = "gmail"
    OUTLOOK = "outlook"
    CUSTOM_SMTP = "custom_smtp"


class SenderStatus(str, enum.Enum):
    """Sender account status"""
    ACTIVE = "active"
    PAUSED = "paused"
    WARMING_UP = "warming_up"
    SUSPENDED = "suspended"  # Due to deliverability issues
    DISCONNECTED = "disconnected"  # OAuth expired or credentials invalid


class Sender(Base):
    """
    Sender account model.
    
    Supports multiple provider types:
    - Gmail (OAuth)
    - Outlook (OAuth)
    - Custom SMTP
    
    Includes warmup tracking and daily limits.
    """
    
    __tablename__ = "senders"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Basic info
    name = Column(String(255), nullable=False)  # Display name
    email = Column(String(255), nullable=False, unique=True, index=True)
    reply_to = Column(String(255), nullable=True)  # Reply-to address if different
    
    # Provider configuration
    provider_type = Column(
        SQLEnum(ProviderType),
        default=ProviderType.CUSTOM_SMTP,
        nullable=False
    )
    
    # SMTP configuration (for custom SMTP)
    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, default=587, nullable=True)
    smtp_username = Column(String(255), nullable=True)
    smtp_password_encrypted = Column(Text, nullable=True)  # Encrypted
    smtp_use_tls = Column(Boolean, default=True, nullable=True)
    
    # IMAP configuration (for reply detection)
    imap_host = Column(String(255), nullable=True)
    imap_port = Column(Integer, default=993, nullable=True)
    imap_username = Column(String(255), nullable=True)
    imap_password_encrypted = Column(Text, nullable=True)  # Encrypted
    imap_use_ssl = Column(Boolean, default=True, nullable=True)
    imap_folder = Column(String(100), default="INBOX", nullable=True)
    
    # OAuth tokens (for Gmail/Outlook)
    oauth_access_token = Column(Text, nullable=True)  # Encrypted
    oauth_refresh_token = Column(Text, nullable=True)  # Encrypted
    oauth_token_expiry = Column(DateTime(timezone=True), nullable=True)
    oauth_scope = Column(Text, nullable=True)
    
    # Status
    status = Column(
        SQLEnum(SenderStatus),
        default=SenderStatus.ACTIVE,
        nullable=False,
        index=True
    )
    
    # Warmup configuration
    warmup_enabled = Column(Boolean, default=True, nullable=False)
    warmup_start_date = Column(Date, nullable=True)
    warmup_current_day = Column(Integer, default=0, nullable=False)
    
    # Daily limits (respects warmup if enabled)
    base_daily_limit = Column(Integer, default=100, nullable=False)
    current_daily_limit = Column(Integer, default=10, nullable=False)  # Adjusted by warmup
    
    # Sending stats
    emails_sent_today = Column(Integer, default=0, nullable=False)
    emails_sent_this_hour = Column(Integer, default=0, nullable=False)
    total_emails_sent = Column(Integer, default=0, nullable=False)
    last_sent_at = Column(DateTime(timezone=True), nullable=True)
    last_hour_reset = Column(DateTime(timezone=True), nullable=True)
    last_day_reset = Column(Date, nullable=True)
    
    # Deliverability tracking
    total_bounces = Column(Integer, default=0, nullable=False)
    total_complaints = Column(Integer, default=0, nullable=False)
    reputation_score = Column(Integer, default=100, nullable=False)  # 0-100
    
    # Timezone
    timezone = Column(String(50), default="America/New_York", nullable=False)
    
    # Send window
    send_window_start_hour = Column(Integer, default=9, nullable=False)  # 9 AM
    send_window_end_hour = Column(Integer, default=17, nullable=False)  # 5 PM
    send_weekdays_only = Column(Boolean, default=True, nullable=False)
    
    # Signature
    signature_html = Column(Text, nullable=True)
    signature_plain = Column(Text, nullable=True)
    
    # Last connection check
    last_connection_check = Column(DateTime(timezone=True), nullable=True)
    connection_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    campaigns = relationship("Campaign", back_populates="sender")
    email_logs = relationship("EmailLog", back_populates="sender")
    
    @property
    def bounce_rate(self) -> float:
        """Calculate bounce rate"""
        if self.total_emails_sent == 0:
            return 0.0
        return (self.total_bounces / self.total_emails_sent) * 100
    
    @property
    def complaint_rate(self) -> float:
        """Calculate complaint rate"""
        if self.total_emails_sent == 0:
            return 0.0
        return (self.total_complaints / self.total_emails_sent) * 100
    
    @property
    def can_send(self) -> tuple:
        """Check if sender can send emails"""
        if self.status != SenderStatus.ACTIVE and self.status != SenderStatus.WARMING_UP:
            return False, f"Sender status is {self.status}"
        
        if self.emails_sent_today >= self.current_daily_limit:
            return False, "Daily limit reached"
        
        if self.bounce_rate >= 10:  # Hard limit
            return False, f"Bounce rate too high: {self.bounce_rate:.1f}%"
        
        return True, "OK"
    
    def get_warmup_limit(self, day: int) -> int:
        """
        Get daily limit based on warmup day.
        
        Warmup schedule:
        - Day 1-3: 10 emails/day
        - Day 4-7: 25 emails/day
        - Day 8-14: 50 emails/day
        - Day 15+: base_daily_limit (up to 100-200)
        """
        if not self.warmup_enabled:
            return self.base_daily_limit
        
        if day <= 3:
            return 10
        elif day <= 7:
            return 25
        elif day <= 14:
            return 50
        else:
            return min(self.base_daily_limit, 100 + ((day - 14) * 10))
    
    def reset_daily_stats(self) -> None:
        """Reset daily stats and update warmup"""
        today = date.today()
        
        if self.last_day_reset != today:
            self.emails_sent_today = 0
            self.last_day_reset = today
            
            # Update warmup day
            if self.warmup_enabled and self.warmup_start_date:
                self.warmup_current_day = (today - self.warmup_start_date).days + 1
                self.current_daily_limit = self.get_warmup_limit(self.warmup_current_day)
    
    def reset_hourly_stats(self) -> None:
        """Reset hourly stats"""
        self.emails_sent_this_hour = 0
        self.last_hour_reset = datetime.utcnow()
    
    def increment_sent(self) -> None:
        """Increment sent counters"""
        self.emails_sent_today += 1
        self.emails_sent_this_hour += 1
        self.total_emails_sent += 1
        self.last_sent_at = datetime.utcnow()
    
    def __repr__(self) -> str:
        return f"<Sender(id={self.id}, email='{self.email}', provider='{self.provider_type}')>"

