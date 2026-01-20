"""
XenFlow Mailer - Analytics Schemas
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class TimeSeriesData(BaseModel):
    """Time series data point"""
    date: date
    value: int


class SendingMetrics(BaseModel):
    """Sending metrics"""
    total_sent: int
    sent_today: int
    sent_this_hour: int
    scheduled: int
    failed: int
    average_per_day: float


class DeliverabilityMetrics(BaseModel):
    """Deliverability metrics"""
    delivered: int
    delivery_rate: float
    bounced: int
    bounce_rate: float
    hard_bounces: int
    soft_bounces: int
    complaints: int
    complaint_rate: float


class EngagementMetrics(BaseModel):
    """Engagement metrics"""
    opens: int
    open_rate: float
    clicks: int
    click_rate: float
    replies: int
    reply_rate: float
    unsubscribes: int
    unsubscribe_rate: float


class CampaignAnalytics(BaseModel):
    """Campaign analytics"""
    campaign_id: int
    campaign_name: str
    status: str
    sending: SendingMetrics
    deliverability: DeliverabilityMetrics
    engagement: EngagementMetrics
    leads_by_status: Dict[str, int]
    daily_sends: List[TimeSeriesData]
    daily_replies: List[TimeSeriesData]


class SenderAnalytics(BaseModel):
    """Sender analytics"""
    sender_id: int
    sender_email: str
    reputation_score: int
    warmup_day: int
    warmup_progress: float  # Percentage
    daily_limit: int
    sent_today: int
    sending: SendingMetrics
    deliverability: DeliverabilityMetrics


class DashboardStats(BaseModel):
    """Main dashboard statistics"""
    # Overview
    total_leads: int
    active_campaigns: int
    total_senders: int
    
    # Today's stats
    emails_sent_today: int
    replies_today: int
    bounces_today: int
    
    # Overall metrics
    total_emails_sent: int
    total_replies: int
    overall_reply_rate: float
    overall_bounce_rate: float
    overall_delivery_rate: float
    
    # Sender health
    senders_healthy: int
    senders_warning: int
    senders_critical: int
    
    # Recent activity
    recent_campaigns: List[Dict[str, Any]]
    recent_replies: List[Dict[str, Any]]
    
    # Charts data
    sends_last_7_days: List[TimeSeriesData]
    replies_last_7_days: List[TimeSeriesData]
    
    # Safety status
    is_safe_to_send: bool
    safety_warnings: List[str]


class ActivityLogEntry(BaseModel):
    """Activity log entry"""
    id: int
    timestamp: datetime
    action: str
    entity_type: str
    entity_id: int
    details: Dict[str, Any]
    status: str


class EmailLogResponse(BaseModel):
    """Email log response for dashboard"""
    id: int
    campaign_id: Optional[int]
    campaign_name: Optional[str]
    lead_id: Optional[int]
    to_email: str
    to_name: Optional[str]
    subject: str
    status: str
    email_type: str
    followup_step: int
    sent_at: Optional[datetime]
    opened_at: Optional[datetime]
    replied_at: Optional[datetime]
    bounced_at: Optional[datetime]
    bounce_type: Optional[str]
    error_message: Optional[str]
    
    class Config:
        from_attributes = True


class EmailLogListResponse(BaseModel):
    """Schema for paginated email log list"""
    items: List[EmailLogResponse]
    total: int
    page: int
    page_size: int
    pages: int

