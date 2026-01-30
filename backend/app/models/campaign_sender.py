"""
XenFlow Mailer - CampaignSender association model

Links campaigns to one or more sender accounts for rotation.
"""

from sqlalchemy import Column, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database import Base


class CampaignSender(Base):
    """
    Join table linking campaigns to multiple senders.

    When sender rotation is enabled on a campaign, the email service
    will choose among these associated senders when sending.
    """

    __tablename__ = "campaign_senders"

    id = Column(Integer, primary_key=True, index=True)
    campaign_id = Column(
        Integer,
        ForeignKey("campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id = Column(
        Integer,
        ForeignKey("senders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional deterministic ordering (e.g. for UI display)
    position = Column(Integer, nullable=True)

    # Ensure we don't store duplicate campaign/sender pairs
    __table_args__ = (
        UniqueConstraint(
            "campaign_id",
            "sender_id",
            name="uq_campaign_senders_campaign_sender",
        ),
    )

    # Relationships
    campaign = relationship("Campaign", back_populates="campaign_senders")
    sender = relationship("Sender")


