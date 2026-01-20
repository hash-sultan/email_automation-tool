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
    send_window_start: time = time(9, 0)
    send_window_end: time = time(17, 0)
    send_weekdays_only: bool = True
    daily_limit: int = Field(default=50, ge=1, le=200)
    hourly_limit: int = Field(default=10, ge=1, le=50)
    min_interval_seconds: int = Field(default=120, ge=60, le=600)
    max_interval_seconds: int = Field(default=300, ge=120, le=900)
    followup_enabled: bool = True
    max_followup_steps: int = Field(default=3, ge=0, le=10)
    followup_delay_days: int = Field(default=3, ge=1, le=14)
    max_bounce_rate: int = Field(default=5, ge=1, le=10)
    max_complaint_rate: int = Field(default=1, ge=1, le=5)
    stop_on_threshold: bool = True
    
    @validator("daily_limit")
    def validate_daily_limit(cls, v):
        if v > 200:
            raise ValueError("Daily limit cannot exceed 200 for safety")
        return v
    
    @validator("hourly_limit")
    def validate_hourly_limit(cls, v):
        if v > 50:
            raise ValueError("Hourly limit cannot exceed 50 for safety")
        return v


class CampaignCreate(CampaignBase):
    """Schema for creating a campaign"""
    sender_id: int
    template_id: Optional[int] = None


class CampaignUpdate(BaseModel):
    """Schema for updating a campaign"""
    name: Optional[str] = None
    description: Optional[str] = None
    template_id: Optional[int] = None
    status: Optional[str] = None
    timezone: Optional[str] = None
    send_window_start: Optional[time] = None
    send_window_end: Optional[time] = None
    send_weekdays_only: Optional[bool] = None
    daily_limit: Optional[int] = Field(default=None, ge=1, le=200)
    hourly_limit: Optional[int] = Field(default=None, ge=1, le=50)
    min_interval_seconds: Optional[int] = None
    max_interval_seconds: Optional[int] = None
    followup_enabled: Optional[bool] = None
    max_followup_steps: Optional[int] = None
    followup_delay_days: Optional[int] = None


class CampaignStats(BaseModel):
    """Campaign statistics"""
    total_leads: int
    emails_sent: int
    emails_today: int
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
    status: str
    total_leads: int
    emails_sent: int
    emails_today: int
    replies_count: int
    bounces_count: int
    unsubscribes_count: int
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
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

