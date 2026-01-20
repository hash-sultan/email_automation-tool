"""
XenFlow Mailer - Suppression Model
Auto-suppression list for bounces, unsubscribes, and complaints
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, DateTime, Text,
    Enum as SQLEnum, Index
)
from sqlalchemy.sql import func
import enum

from app.database import Base


class SuppressionReason(str, enum.Enum):
    """Reason for suppression"""
    HARD_BOUNCE = "hard_bounce"
    SOFT_BOUNCE_LIMIT = "soft_bounce_limit"  # Too many soft bounces
    COMPLAINT = "complaint"  # Marked as spam
    UNSUBSCRIBE = "unsubscribe"  # User unsubscribed
    MANUAL = "manual"  # Manually added
    INVALID_EMAIL = "invalid_email"  # Invalid email format
    ROLE_BASED = "role_based"  # Role-based email (info@, support@)


class Suppression(Base):
    """
    Global suppression list.
    
    Emails in this list will NEVER receive emails.
    This is critical for:
    - Legal compliance (CAN-SPAM, GDPR)
    - Sender reputation
    - Deliverability
    """
    
    __tablename__ = "suppressions"
    
    # Primary key
    id = Column(Integer, primary_key=True, index=True)
    
    # Suppressed email
    email = Column(String(255), nullable=False, unique=True, index=True)
    
    # Suppression reason
    reason = Column(
        SQLEnum(SuppressionReason),
        nullable=False,
        index=True
    )
    
    # Source information
    source = Column(String(255), nullable=True)  # Where this came from
    campaign_id = Column(Integer, nullable=True)  # If from a campaign
    
    # Error details
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Bounce tracking (for soft bounces)
    bounce_count = Column(Integer, default=1, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Notes
    notes = Column(Text, nullable=True)
    
    # Indexes
    __table_args__ = (
        Index("ix_suppressions_email_reason", "email", "reason"),
    )
    
    @classmethod
    def is_suppressed(cls, session, email: str) -> bool:
        """Check if email is in suppression list"""
        return session.query(cls).filter(cls.email == email.lower()).first() is not None
    
    @classmethod
    def add_suppression(cls, session, email: str, reason: SuppressionReason, 
                       source: str = None, campaign_id: int = None,
                       error_code: str = None, error_message: str = None) -> "Suppression":
        """Add email to suppression list"""
        # Check if already exists
        existing = session.query(cls).filter(cls.email == email.lower()).first()
        
        if existing:
            # Update existing suppression
            existing.bounce_count += 1
            existing.updated_at = datetime.utcnow()
            return existing
        
        # Create new suppression
        suppression = cls(
            email=email.lower(),
            reason=reason,
            source=source,
            campaign_id=campaign_id,
            error_code=error_code,
            error_message=error_message
        )
        session.add(suppression)
        return suppression
    
    def __repr__(self) -> str:
        return f"<Suppression(email='{self.email}', reason='{self.reason}')>"

