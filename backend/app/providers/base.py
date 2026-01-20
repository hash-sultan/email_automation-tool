"""
XenFlow Mailer - Base Email Provider
Abstract base class for all email providers
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class EmailResultStatus(str, Enum):
    """Email sending result status"""
    SUCCESS = "success"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"
    BOUNCED = "bounced"
    INVALID = "invalid"


@dataclass
class EmailMessage:
    """
    Email message data class.
    Provider-agnostic email representation.
    """
    # Required fields
    to_email: str
    subject: str
    body_html: str
    
    # Optional fields
    to_name: Optional[str] = None
    from_email: Optional[str] = None  # Will use sender's email if not set
    from_name: Optional[str] = None
    reply_to: Optional[str] = None
    
    # Content
    body_plain: Optional[str] = None  # Plain text fallback
    
    # Headers for threading
    message_id: Optional[str] = None  # Will be auto-generated
    in_reply_to: Optional[str] = None  # For follow-ups
    references: Optional[str] = None  # For follow-ups
    
    # Custom headers
    custom_headers: Dict[str, str] = field(default_factory=dict)
    
    # Attachments (not recommended for cold outreach)
    attachments: List[Dict[str, Any]] = field(default_factory=list)
    
    # Tracking
    campaign_id: Optional[int] = None
    lead_id: Optional[int] = None
    followup_step: int = 0
    
    def __post_init__(self):
        """Validate and generate required fields"""
        if not self.message_id:
            import uuid
            domain = self.from_email.split('@')[1] if self.from_email else "xenflow.local"
            self.message_id = f"<{uuid.uuid4()}@{domain}>"
        
        # Auto-generate plain text if not provided
        if not self.body_plain and self.body_html:
            import re
            import html
            self.body_plain = html.unescape(re.sub(r'<[^>]+>', '', self.body_html))


@dataclass
class EmailResult:
    """
    Result of sending an email.
    """
    status: EmailResultStatus
    message_id: Optional[str] = None
    provider_message_id: Optional[str] = None
    sent_at: Optional[datetime] = None
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    
    @property
    def is_success(self) -> bool:
        return self.status == EmailResultStatus.SUCCESS
    
    @property
    def is_bounced(self) -> bool:
        return self.status == EmailResultStatus.BOUNCED
    
    @classmethod
    def success(cls, message_id: str, provider_message_id: str = None) -> "EmailResult":
        return cls(
            status=EmailResultStatus.SUCCESS,
            message_id=message_id,
            provider_message_id=provider_message_id,
            sent_at=datetime.utcnow()
        )
    
    @classmethod
    def failed(cls, error_code: str, error_message: str) -> "EmailResult":
        return cls(
            status=EmailResultStatus.FAILED,
            error_code=error_code,
            error_message=error_message
        )
    
    @classmethod
    def rate_limited(cls, message: str = "Rate limit exceeded") -> "EmailResult":
        return cls(
            status=EmailResultStatus.RATE_LIMITED,
            error_message=message
        )


class BaseEmailProvider(ABC):
    """
    Abstract base class for email providers.
    
    All providers (Gmail, Outlook, Custom SMTP) must implement:
    - connect(): Establish connection
    - disconnect(): Close connection
    - send_email(): Send a single email
    - verify_connection(): Verify credentials work
    """
    
    def __init__(self, sender_email: str, sender_name: str = None):
        self.sender_email = sender_email
        self.sender_name = sender_name or sender_email.split('@')[0]
        self._connected = False
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Establish connection to the email provider.
        Returns True if successful.
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """
        Close connection to the email provider.
        """
        pass
    
    @abstractmethod
    async def send_email(self, message: EmailMessage) -> EmailResult:
        """
        Send a single email.
        Returns EmailResult with status and details.
        """
        pass
    
    @abstractmethod
    async def verify_connection(self) -> tuple:
        """
        Verify that credentials and connection work.
        Returns (success: bool, error_message: str or None)
        """
        pass
    
    def build_headers(self, message: EmailMessage) -> Dict[str, str]:
        """
        Build email headers with deliverability best practices.
        """
        headers = {
            "Message-ID": message.message_id,
            "From": f"{message.from_name or self.sender_name} <{message.from_email or self.sender_email}>",
            "To": f"{message.to_name or ''} <{message.to_email}>".strip(),
            "Subject": message.subject,
            "Reply-To": message.reply_to or message.from_email or self.sender_email,
            "X-Mailer": "XenFlow Mailer/1.0",
            "MIME-Version": "1.0",
        }
        
        # Threading headers for follow-ups
        if message.in_reply_to:
            headers["In-Reply-To"] = message.in_reply_to
        if message.references:
            headers["References"] = message.references
        
        # List-Unsubscribe header (critical for deliverability)
        # This should be customized per campaign
        headers["List-Unsubscribe"] = f"<mailto:unsubscribe@{self.sender_email.split('@')[1]}>"
        
        # Add custom headers
        headers.update(message.custom_headers)
        
        return headers


# V2 Extension Points (Design Only - Not Implemented)

class AIReplyGeneratorInterface(ABC):
    """
    V2: Interface for AI-powered reply generation.
    NOT IMPLEMENTED IN V1 - Design only.
    """
    
    @abstractmethod
    async def generate_reply(
        self, 
        incoming_email: str,
        lead_context: Dict[str, Any],
        campaign_context: Dict[str, Any]
    ) -> str:
        """Generate a contextual reply using LLM"""
        pass


class IntentClassifierInterface(ABC):
    """
    V2: Interface for intent detection from replies.
    NOT IMPLEMENTED IN V1 - Design only.
    """
    
    @abstractmethod
    async def classify_intent(self, email_body: str) -> Dict[str, Any]:
        """
        Classify intent of incoming email.
        Returns: {
            "intent": "interested|not_interested|question|booking|other",
            "confidence": float,
            "details": {...}
        }
        """
        pass


class CalendarIntegrationInterface(ABC):
    """
    V2: Interface for calendar integration.
    NOT IMPLEMENTED IN V1 - Design only.
    """
    
    @abstractmethod
    async def get_available_slots(
        self, 
        start_date: datetime,
        end_date: datetime,
        duration_minutes: int
    ) -> List[Dict[str, Any]]:
        """Get available calendar slots"""
        pass
    
    @abstractmethod
    async def create_booking(
        self,
        slot: Dict[str, Any],
        lead_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a calendar booking"""
        pass


class CRMConnectorInterface(ABC):
    """
    V2: Interface for CRM synchronization.
    NOT IMPLEMENTED IN V1 - Design only.
    """
    
    @abstractmethod
    async def sync_lead(self, lead_data: Dict[str, Any]) -> str:
        """Sync lead to CRM, returns CRM ID"""
        pass
    
    @abstractmethod
    async def update_status(self, crm_id: str, status: str) -> bool:
        """Update lead status in CRM"""
        pass

