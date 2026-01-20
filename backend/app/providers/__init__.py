"""
XenFlow Mailer - Email Provider Abstraction Layer
"""

from app.providers.base import BaseEmailProvider, EmailMessage, EmailResult
from app.providers.smtp import SMTPProvider
from app.providers.gmail import GmailProvider
from app.providers.outlook import OutlookProvider

__all__ = [
    "BaseEmailProvider",
    "EmailMessage",
    "EmailResult",
    "SMTPProvider",
    "GmailProvider",
    "OutlookProvider",
]

