"""
XenFlow Mailer - Global Campaign Lock
Only ONE campaign can run at a time (initial emails + follow-ups).
Uses Redis for process-wide enforcement; sync API for use in Celery workers.
"""

from typing import Optional
import redis

from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()

REDIS_KEY_RUNNING_CAMPAIGN = "xenflow:running_campaign_id"


def _get_redis() -> redis.Redis:
    """Sync Redis client for use in Celery workers (no asyncio)."""
    return redis.from_url(
        settings.CELERY_BROKER_URL or settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )


def get_running_campaign_id() -> Optional[int]:
    """
    Return the campaign id that currently holds the global lock, or None.
    Only this campaign may send initial emails or run follow-ups.
    """
    try:
        r = _get_redis()
        val = r.get(REDIS_KEY_RUNNING_CAMPAIGN)
        r.close()
        if val is None or val == "":
            return None
        return int(val)
    except Exception as e:
        logger.warning(f"Campaign lock get failed: {e}", extra={"key": REDIS_KEY_RUNNING_CAMPAIGN})
        return None


def set_running_campaign(campaign_id: int) -> bool:
    """
    Set the running campaign to this id (call when starting or resuming this campaign).
    Caller must have already paused all other campaigns.
    """
    try:
        r = _get_redis()
        r.set(REDIS_KEY_RUNNING_CAMPAIGN, str(campaign_id))
        r.close()
        logger.info(
            "Campaign lock acquired",
            extra={"campaign_id": campaign_id, "key": REDIS_KEY_RUNNING_CAMPAIGN},
        )
        return True
    except Exception as e:
        logger.warning(f"Campaign lock set failed: {e}", extra={"campaign_id": campaign_id})
        return False


def clear_running_campaign(campaign_id: Optional[int] = None) -> bool:
    """
    Clear the running campaign lock.
    If campaign_id is given, only clear if the current running campaign is this one.
    Returns True if lock was cleared.
    """
    try:
        r = _get_redis()
        current = r.get(REDIS_KEY_RUNNING_CAMPAIGN)
        if current is None or current == "":
            r.close()
            return True
        current_id = int(current)
        if campaign_id is not None and current_id != campaign_id:
            r.close()
            return False
        r.delete(REDIS_KEY_RUNNING_CAMPAIGN)
        r.close()
        logger.info(
            "Campaign lock released",
            extra={"campaign_id": campaign_id, "released_id": current_id},
        )
        return True
    except Exception as e:
        logger.warning(f"Campaign lock clear failed: {e}", extra={"campaign_id": campaign_id})
        return False


def acquire_running_campaign(campaign_id: int) -> bool:
    """
    Set this campaign as the running one only if no other is running.
    Returns True if we acquired the lock.
    """
    try:
        r = _get_redis()
        current = r.get(REDIS_KEY_RUNNING_CAMPAIGN)
        if current is not None and current != "" and int(current) != campaign_id:
            r.close()
            logger.info(
                "Campaign lock not acquired: another campaign is running",
                extra={"campaign_id": campaign_id, "running_id": int(current)},
            )
            return False
        r.set(REDIS_KEY_RUNNING_CAMPAIGN, str(campaign_id))
        r.close()
        logger.info("Campaign lock acquired", extra={"campaign_id": campaign_id})
        return True
    except Exception as e:
        logger.warning(f"Campaign lock acquire failed: {e}", extra={"campaign_id": campaign_id})
        return False
