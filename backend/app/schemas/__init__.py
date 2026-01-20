"""
XenFlow Mailer - Pydantic Schemas
"""

from app.schemas.lead import (
    LeadBase, LeadCreate, LeadUpdate, LeadResponse, LeadListResponse,
    LeadImportCSV, LeadBulkUpdate
)
from app.schemas.campaign import (
    CampaignBase, CampaignCreate, CampaignUpdate, CampaignResponse,
    CampaignStats, CampaignListResponse
)
from app.schemas.template import (
    TemplateBase, TemplateCreate, TemplateUpdate, TemplateResponse,
    FollowUpTemplateCreate, FollowUpTemplateResponse
)
from app.schemas.sender import (
    SenderBase, SenderCreate, SenderUpdate, SenderResponse,
    SenderStats, SMTPConfig, OAuthConfig
)
from app.schemas.analytics import (
    DashboardStats, CampaignAnalytics, SendingMetrics, 
    DeliverabilityMetrics, TimeSeriesData
)

__all__ = [
    # Lead
    "LeadBase", "LeadCreate", "LeadUpdate", "LeadResponse", 
    "LeadListResponse", "LeadImportCSV", "LeadBulkUpdate",
    # Campaign
    "CampaignBase", "CampaignCreate", "CampaignUpdate", "CampaignResponse",
    "CampaignStats", "CampaignListResponse",
    # Template
    "TemplateBase", "TemplateCreate", "TemplateUpdate", "TemplateResponse",
    "FollowUpTemplateCreate", "FollowUpTemplateResponse",
    # Sender
    "SenderBase", "SenderCreate", "SenderUpdate", "SenderResponse",
    "SenderStats", "SMTPConfig", "OAuthConfig",
    # Analytics
    "DashboardStats", "CampaignAnalytics", "SendingMetrics",
    "DeliverabilityMetrics", "TimeSeriesData",
]

