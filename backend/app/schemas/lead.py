"""
XenFlow Mailer - Lead Schemas
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, EmailStr, Field, validator


class LeadBase(BaseModel):
    """Base lead schema"""
    email: EmailStr
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    timezone: str = "America/New_York"
    custom_fields: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class LeadCreate(LeadBase):
    """Schema for creating a lead"""
    campaign_id: Optional[int] = None
    source: Optional[str] = "manual"


class LeadUpdate(BaseModel):
    """Schema for updating a lead"""
    name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    industry: Optional[str] = None
    title: Optional[str] = None
    phone: Optional[str] = None
    timezone: Optional[str] = None
    custom_fields: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class LeadResponse(LeadBase):
    """Schema for lead response"""
    id: int
    campaign_id: Optional[int]
    status: str
    step: int
    last_sent_at: Optional[datetime]
    next_followup_at: Optional[datetime]
    replied: bool
    replied_at: Optional[datetime]
    bounced: bool
    bounced_at: Optional[datetime]
    bounce_type: Optional[str]
    unsubscribed: bool
    unsubscribed_at: Optional[datetime]
    emails_sent: int
    emails_opened: int
    links_clicked: int
    source: Optional[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class LeadListResponse(BaseModel):
    """Schema for paginated lead list"""
    items: List[LeadResponse]
    total: int
    page: int
    page_size: int
    pages: int


class LeadImportCSV(BaseModel):
    """Schema for CSV import configuration"""
    campaign_id: Optional[int] = None
    column_mapping: Dict[str, str] = Field(
        default_factory=lambda: {
            "email": "email",
            "name": "name",
            "company": "company"
        },
        description="Map CSV columns to lead fields"
    )
    skip_duplicates: bool = True
    source: str = "csv_import"


class LeadBulkUpdate(BaseModel):
    """Schema for bulk lead updates"""
    lead_ids: List[int]
    status: Optional[str] = None
    campaign_id: Optional[int] = None
    tags_add: Optional[List[str]] = None
    tags_remove: Optional[List[str]] = None

