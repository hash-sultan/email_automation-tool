"""
XenFlow Mailer - Campaign Schemas
"""

from datetime import datetime, time
from typing import Optional, List
from pydantic import BaseModel, Field, validator


class CampaignBase(BaseModel):
    """Base campaign schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    timezone: str = "America/New_York"
    send_window_start: time = time(0, 0)  # 12 AM (24/7)
    send_window_end: time = time(23, 59)  # 11:59 PM (24/7)
    send_weekdays_only: bool = False  # Allow weekends
    daily_limit: int = Field(default=500, ge=1, le=1000)  # Allow up to 1000/day
    hourly_limit: int = Field(default=50, ge=1, le=100)  # Allow up to 100/hour
    min_interval_seconds: int = Field(default=10, ge=10, le=600)
    max_interval_seconds: int = Field(default=10, ge=10, le=900)
    followup_enabled: bool = True
    max_followup_steps: int = Field(default=3, ge=0, le=10)
    followup_delay_days: int = Field(default=3, ge=1, le=14)
    max_bounce_rate: int = Field(default=5, ge=1, le=10)
    max_complaint_rate: int = Field(default=1, ge=1, le=5)
    stop_on_threshold: bool = True
    
    @validator("daily_limit")
    def validate_daily_limit(cls, v):
        if v > 1000:
            raise ValueError("Daily limit cannot exceed 1000")
        return v
    
    @validator("hourly_limit")
    def validate_hourly_limit(cls, v):
        if v > 100:
            raise ValueError("Hourly limit cannot exceed 100 for safety")
        return v


class CampaignCreate(CampaignBase):
    """Schema for creating a campaign"""
    sender_id: int
    # Single-template mode (backwards compatible)
    template_id: Optional[int] = None
    # Category-based rotation mode (new)
    template_category: Optional[str] = Field(
        default=None,
        description="Template category to use for rotating initial/follow-up templates",
        min_length=1,
        max_length=100,
    )
    followup_template_ids: Optional[List[int]] = Field(default=None, description="List of template IDs to use as follow-ups")
    # Sender rotation
    sender_rotation_enabled: bool = Field(
        default=False,
        description="If true, use multiple senders in rotation instead of a single sender",
    )
    sender_ids: Optional[List[int]] = Field(
        default=None,
        description="List of sender IDs to rotate between when rotation is enabled",
    )
    max_senders: Optional[int] = Field(
        default=None,
        description="Optional cap on how many of the selected senders to use",
    )


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign"""
    name: Optional[str] = None
    description: Optional[str] = None
    template_id: Optional[int] = None
    template_category: Optional[str] = Field(
        default=None,
        description="Template category to use for rotating initial/follow-up templates",
        min_length=1,
        max_length=100,
    )
    status: Optional[str] = None
    timezone: Optional[str] = None
    send_window_start: Optional[time] = None
    send_window_end: Optional[time] = None
    send_weekdays_only: Optional[bool] = None
    daily_limit: Optional[int] = Field(default=None, ge=1, le=1000)
    hourly_limit: Optional[int] = Field(default=None, ge=1, le=50)
    min_interval_seconds: Optional[int] = None
    max_interval_seconds: Optional[int] = None
    followup_enabled: Optional[bool] = None
    max_followup_steps: Optional[int] = None
    followup_delay_days: Optional[int] = None
    # Sender / rotation updates
    sender_id: Optional[int] = None
    sender_rotation_enabled: Optional[bool] = None
    sender_ids: Optional[List[int]] = None
    max_senders: Optional[int] = None


class CampaignStats(BaseModel):
    """Campaign statistics"""
    total_leads: int
    # Total number of emails sent (may be > unique leads if duplicates / retries)
    emails_sent: int
    followups_sent: int = 0  # Count of follow-up emails sent
    emails_today: int
    # Number of unique leads that have received at least one email
    leads_contacted: int = 0
    replies_count: int
    bounces_count: int
    unsubscribes_count: int
    reply_rate: float
    bounce_rate: float
    open_rate: float = 0.0
    click_rate: float = 0.0


class CampaignResponse(CampaignBase):
    """Schema for campaign response"""
    id: int
    sender_id: int
    template_id: Optional[int]
    template_category: Optional[str] = None
    status: str
    total_leads: int
    # Total number of emails sent (may be > unique leads if duplicates / retries)
    emails_sent: int
    followups_sent: int = 0  # Count of follow-up emails sent
    emails_today: int
    # Number of unique leads that have received at least one email
    leads_contacted: int = 0
    replies_count: int
    bounces_count: int
    unsubscribes_count: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    # Rotation metadata
    sender_rotation_enabled: bool = False
    sender_ids: Optional[List[int]] = None
    max_senders: Optional[int] = None
    stats: Optional[CampaignStats] = None
    
    class Config:
        from_attributes = True


class CampaignListResponse(BaseModel):
    """Schema for paginated campaign list"""
    items: List[CampaignResponse]
    total: int
    page: int
    page_size: int
    pages: int

