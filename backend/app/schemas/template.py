"""
XenFlow Mailer - Template Schemas
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, validator
import re


class TemplateBase(BaseModel):
    """Base template schema"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    subject: str = Field(..., min_length=1, max_length=255)
    body_html: str = Field(..., min_length=1)
    body_plain: Optional[str] = None
    signature_html: Optional[str] = None
    signature_plain: Optional[str] = None
    is_active: bool = True
    template_type: str = Field(default="initial", pattern="^(initial|followup)$")
    
    @validator("body_html")
    def validate_body_html(cls, v):
        # Extract placeholders used
        placeholders = re.findall(r'\{\{(\w+)\}\}', v)
        return v
    
    @validator("body_plain", always=True)
    def auto_generate_plain(cls, v, values):
        if not v and "body_html" in values:
            # Simple HTML to plain text conversion
            import html
            plain = re.sub(r'<[^>]+>', '', values["body_html"])
            return html.unescape(plain)
        return v


class TemplateCreate(TemplateBase):
    """Schema for creating a template"""
    pass


class TemplateUpdate(BaseModel):
    """Schema for updating a template"""
    name: Optional[str] = None
    description: Optional[str] = None
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_plain: Optional[str] = None
    signature_html: Optional[str] = None
    signature_plain: Optional[str] = None
    is_active: Optional[bool] = None
    template_type: Optional[str] = Field(default=None, pattern="^(initial|followup)$")


class TemplateResponse(TemplateBase):
    """Schema for template response"""
    id: int
    placeholders_used: List[str]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FollowUpTemplateCreate(BaseModel):
    """Schema for creating a follow-up template"""
    campaign_id: int
    step: int = Field(..., ge=1, le=10)
    delay_days: int = Field(default=3, ge=1, le=14)
    delay_hours: int = Field(default=0, ge=0, le=23)
    subject: str = Field(..., min_length=1, max_length=255)
    body_html: str = Field(..., min_length=1)
    body_plain: Optional[str] = None
    reply_to_thread: bool = True
    is_active: bool = True


class FollowUpTemplateUpdate(BaseModel):
    """Schema for updating a follow-up template"""
    delay_days: Optional[int] = Field(default=None, ge=1, le=14)
    delay_hours: Optional[int] = Field(default=None, ge=0, le=23)
    subject: Optional[str] = None
    body_html: Optional[str] = None
    body_plain: Optional[str] = None
    reply_to_thread: Optional[bool] = None
    is_active: Optional[bool] = None


class FollowUpTemplateResponse(BaseModel):
    """Schema for follow-up template response"""
    id: int
    campaign_id: int
    step: int
    delay_days: int
    delay_hours: int
    subject: str
    body_html: str
    body_plain: Optional[str]
    reply_to_thread: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

