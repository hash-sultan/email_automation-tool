"""
XenFlow Mailer - Tracking API

Implements basic click tracking by redirecting through the backend and
marking the associated EmailLog as CLICKED.
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from urllib.parse import unquote

from app.database import get_db
from app.models import EmailLog
from app.models.email_log import EmailStatus
from app.utils.logger import get_logger


logger = get_logger(__name__)
router = APIRouter()


@router.get("/click/{log_id}")
def track_click(log_id: int, u: str, db: Session = Depends(get_db)):
    """
    Track a click for an email log and redirect to the final URL.

    Args:
        log_id: ID of the EmailLog row.
        u: URL-encoded destination URL.
    """
    # Decode the target URL
    if not u:
        raise HTTPException(status_code=400, detail="Missing destination URL")

    target_url = unquote(u)

    email_log = db.query(EmailLog).filter(EmailLog.id == log_id).first()
    if not email_log:
        logger.warning("Click tracking: email_log not found", extra={"log_id": log_id})
        # Redirect anyway to avoid breaking the user experience
        return RedirectResponse(url=target_url, status_code=302)

    # Only update if not already marked as clicked / replied
    if email_log.status not in [EmailStatus.CLICKED, EmailStatus.REPLIED]:
        email_log.status = EmailStatus.CLICKED
        db.commit()

        logger.info(
            "Tracked click",
            extra={
                "log_id": email_log.id,
                "campaign_id": email_log.campaign_id,
                "lead_id": email_log.lead_id,
                "to": email_log.to_email,
            },
        )

    return RedirectResponse(url=target_url, status_code=302)

