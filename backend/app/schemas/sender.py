"""
XenFlow Mailer - Sender Schemas
"""

from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class SMTPConfig(BaseModel):
    """SMTP configuration"""
    host: str
    port: int = 587
    username: str
    password: str
    use_tls: bool = True


class IMAPConfig(BaseModel):
    """IMAP configuration for reply detection"""
    host: str
    port: int = 993
    username: str
    password: str
    use_ssl: bool = True
    folder: str = "INBOX"


class OAuthConfig(BaseModel):
    """OAuth configuration for Gmail/Outlook"""
    provider: str = Field(..., pattern="^(gmail|outlook)$")
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None


class SenderBase(BaseModel):
    """Base sender schema"""
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    reply_to: Optional[EmailStr] = None
    provider_type: str = Field(default="custom_smtp", pattern="^(gmail|outlook|custom_smtp)$")
    timezone: str = "America/New_York"
    send_window_start_hour: int = Field(default=9, ge=0, le=23)
    send_window_end_hour: int = Field(default=17, ge=0, le=23)
    send_weekdays_only: bool = True
    warmup_enabled: bool = True
    base_daily_limit: int = Field(default=100, ge=10, le=200)
    signature_html: Optional[str] = None
    signature_plain: Optional[str] = None
    
    @model_validator(mode="after")
    def validate_send_window(self):
        if self.send_window_start_hour and self.send_window_end_hour <= self.send_window_start_hour:
            raise ValueError("send_window_end_hour must be greater than send_window_start_hour")
        return self


class SenderCreate(SenderBase):
    """Schema for creating a sender"""
    smtp_config: Optional[SMTPConfig] = None
    imap_config: Optional[IMAPConfig] = None
    oauth_config: Optional[OAuthConfig] = None
    
    @model_validator(mode="after")
    def validate_config(self):
        if self.provider_type == "custom_smtp" and not self.smtp_config:
            raise ValueError("SMTP config is required for custom_smtp provider")
        return self


class SenderUpdate(BaseModel):
    """Schema for updating a sender"""
    name: Optional[str] = None
    reply_to: Optional[str] = None
    status: Optional[str] = None
    timezone: Optional[str] = None
    send_window_start_hour: Optional[int] = Field(default=None, ge=0, le=23)
    send_window_end_hour: Optional[int] = Field(default=None, ge=0, le=23)
    send_weekdays_only: Optional[bool] = None
    warmup_enabled: Optional[bool] = None
    base_daily_limit: Optional[int] = Field(default=None, ge=10, le=200)
    signature_html: Optional[str] = None
    signature_plain: Optional[str] = None
    smtp_config: Optional[SMTPConfig] = None
    imap_config: Optional[IMAPConfig] = None


class SenderStats(BaseModel):
    """Sender statistics"""
    emails_sent_today: int
    emails_sent_this_hour: int
    total_emails_sent: int
    total_bounces: int
    total_complaints: int
    bounce_rate: float
    complaint_rate: float
    reputation_score: int
    current_daily_limit: int
    warmup_day: int


class SenderResponse(SenderBase):
    """Schema for sender response"""
    id: int
    status: str
    warmup_start_date: Optional[date]
    warmup_current_day: int
    current_daily_limit: int
    emails_sent_today: int
    total_emails_sent: int
    total_bounces: int
    reputation_score: int
    last_sent_at: Optional[datetime]
    last_connection_check: Optional[datetime]
    connection_error: Optional[str]
    created_at: datetime
    updated_at: datetime
    stats: Optional[SenderStats] = None
    is_verified: bool = False  # Computed: True if connection_error is None and last_connection_check exists
    is_active: bool = False  # Computed: True if status == "active"
    
    class Config:
        from_attributes = True


class SenderListResponse(BaseModel):
    """Schema for paginated sender list"""
    items: List[SenderResponse]
    total: int
    page: int
    page_size: int
    pages: int

