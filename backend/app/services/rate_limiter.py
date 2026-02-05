"""
XenFlow Mailer - Rate Limiter
Redis-based rate limiting for email sending
"""

import asyncio
import random
from datetime import datetime, timedelta
from typing import Tuple, Optional
import redis.asyncio as redis

from app.config import get_settings, SafetyLimits
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class RateLimiter:
    """
    Redis-based rate limiter for email sending.
    
    Implements:
    - Per-sender daily limits (max 500/day)
    - Per-campaign daily limits
    - Adaptive delays based on sender rotation:
      * 1 sender: 10s delay, 50 emails → 10min pause
      * 2 senders: 7s delay, 75 emails → 7min pause
      * 3+ senders: 5s delay, 100 emails → 5min pause
    - Per-sender batch pause (if one sender pauses, others continue)
    """
    
    # Redis key prefixes
    PREFIX_SENDER_DAILY = "ratelimit:sender:daily"
    PREFIX_CAMPAIGN_DAILY = "ratelimit:campaign:daily"
    PREFIX_LAST_SEND = "ratelimit:lastsend"
    PREFIX_BATCH_COUNT = "ratelimit:batch:count"  # Count emails in current batch
    PREFIX_BATCH_PAUSE = "ratelimit:batch:pause"  # When batch pause ends
    
    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or settings.REDIS_URL
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis
    
    async def check_rate_limit(
        self,
        sender_id: int,
        campaign_id: int,
        num_rotation_senders: int = 1,
        sender_hourly_limit: int = None,
        sender_daily_limit: int = None,
        campaign_hourly_limit: int = None,
        campaign_daily_limit: int = None
    ) -> Tuple[bool, int]:
        """
        Check if we can send an email now.
        
        Adaptive rate limiting based on sender rotation:
        - 1 sender: 10s delay, 50 emails → 10min pause
        - 2 senders: 7s delay, 75 emails → 7min pause
        - 3+ senders: 5s delay, 100 emails → 5min pause
        
        Batch pause is per-sender (if one sender pauses, others continue).
        
        Returns:
            (allowed: bool, wait_seconds: int)
            - If allowed is True, wait_seconds is 0
            - If allowed is False, wait_seconds is how long to wait
        """
        r = await self._get_redis()
        
        # Adaptive settings based on rotation count
        if num_rotation_senders >= 3:
            min_interval = 5  # 5 seconds with 3+ senders
        elif num_rotation_senders == 2:
            min_interval = 7  # 7 seconds with 2 senders
        else:
            min_interval = 10  # 10 seconds with 1 sender
        
        # Load system settings for global caps (sender-level only; campaign caps disabled)
        try:
            from app.api.settings import load_settings
            system_settings = load_settings()
            max_sender_limit = system_settings.get('sender_daily_limit', 200)
        except Exception:
            # Fallback to defaults if settings can't be loaded
            max_sender_limit = 200
        
        # Use defaults if not provided, but cap at settings limits (sender-level only)
        sender_daily_limit = sender_daily_limit or settings.MAX_EMAILS_PER_DAY
        # Cap sender limit at settings value (settings take precedence)
        sender_daily_limit = min(sender_daily_limit, max_sender_limit)
        
        # Keys
        sender_daily_key = f"{self.PREFIX_SENDER_DAILY}:{sender_id}"
        campaign_daily_key = f"{self.PREFIX_CAMPAIGN_DAILY}:{campaign_id}"
        last_send_key = f"{self.PREFIX_LAST_SEND}:{sender_id}"
        
        # Get current counts and timestamps
        pipeline = r.pipeline()
        pipeline.get(sender_daily_key)
        pipeline.get(campaign_daily_key)
        pipeline.get(last_send_key)
        
        results = await pipeline.execute()
        
        sender_daily_count = int(results[0] or 0)
        campaign_daily_count = int(results[1] or 0)
        last_send_time = float(results[2] or 0)
        
        now = datetime.utcnow()
        now_timestamp = now.timestamp()
        
        # Batch pause disabled - removed per user request
        
        # Check sender daily limit (max 500/day, global hard cap)
        max_daily = min(sender_daily_limit, SafetyLimits.ABSOLUTE_MAX_EMAILS_PER_DAY)
        if sender_daily_count >= max_daily:
            # Calculate wait time until midnight
            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            wait_seconds = int((tomorrow - now).total_seconds())
            logger.debug(f"Sender daily limit reached: {sender_daily_count}/{max_daily}")
            return False, wait_seconds
        
        # Campaign-level daily limits are disabled per user request; campaign_daily_limit is ignored.
        
        # Check adaptive minimum interval between emails (per sender)
        if last_send_time > 0:
            elapsed = now_timestamp - last_send_time
            if elapsed < min_interval:
                wait_seconds = int(min_interval - elapsed)
                logger.debug(f"Min interval not reached: wait {wait_seconds}s (rotation: {num_rotation_senders} senders, interval: {min_interval}s)")
                return False, wait_seconds
        
        return True, 0
    
    async def record_send(
        self, 
        sender_id: int, 
        campaign_id: int,
        num_rotation_senders: int = 1
    ) -> None:
        """
        Record that an email was sent.
        Updates counters and handles adaptive batch pause logic (per-sender).
        
        Batch pause is per-sender, so if one sender pauses, others in rotation continue.
        """
        r = await self._get_redis()
        
        # Batch pause disabled - removed per user request
        # No delays after batch completion
        
        now = datetime.utcnow()
        now_timestamp = now.timestamp()
        
        # Calculate expiry times
        seconds_until_midnight = (
            (24 - now.hour - 1) * 3600 + 
            (60 - now.minute - 1) * 60 + 
            (60 - now.second)
        )
        
        # Keys
        sender_daily_key = f"{self.PREFIX_SENDER_DAILY}:{sender_id}"
        campaign_daily_key = f"{self.PREFIX_CAMPAIGN_DAILY}:{campaign_id}"
        last_send_key = f"{self.PREFIX_LAST_SEND}:{sender_id}"
        
        # Increment counters with expiry
        pipeline = r.pipeline()
        
        # Sender daily
        pipeline.incr(sender_daily_key)
        pipeline.expire(sender_daily_key, seconds_until_midnight)
        
        # Campaign daily
        pipeline.incr(campaign_daily_key)
        pipeline.expire(campaign_daily_key, seconds_until_midnight)
        
        # Last send time
        pipeline.set(last_send_key, now_timestamp)
        pipeline.expire(last_send_key, 60)  # 1 minute expiry (just for 10s check)
        
        await pipeline.execute()
        
        logger.debug(
            f"Recorded send for sender {sender_id}, campaign {campaign_id} "
            f"(rotation: {num_rotation_senders} senders)"
        )
    
    async def get_random_delay(
        self,
        min_seconds: int = None,
        max_seconds: int = None
    ) -> int:
        """
        Get a randomized delay for human-like send patterns.
        """
        min_seconds = min_seconds or settings.MIN_SEND_INTERVAL_SECONDS
        max_seconds = max_seconds or settings.MAX_SEND_INTERVAL_SECONDS
        
        # Ensure minimum is respected
        min_seconds = max(min_seconds, SafetyLimits.MIN_EMAIL_INTERVAL_SECONDS)
        
        return random.randint(min_seconds, max_seconds)
    
    async def get_stats(self, sender_id: int = None, campaign_id: int = None) -> dict:
        """
        Get current rate limit statistics.
        """
        r = await self._get_redis()
        stats = {}
        
        if sender_id:
            sender_daily = await r.get(f"{self.PREFIX_SENDER_DAILY}:{sender_id}")
            stats["sender_daily_count"] = int(sender_daily or 0)
            # Batch pause disabled - removed per user request
        
        if campaign_id:
            campaign_daily = await r.get(f"{self.PREFIX_CAMPAIGN_DAILY}:{campaign_id}")
            stats["campaign_daily_count"] = int(campaign_daily or 0)
        
        return stats
    
    async def reset_counters(self, sender_id: int = None, campaign_id: int = None) -> None:
        """
        Reset rate limit counters (use with caution).
        """
        r = await self._get_redis()
        
        keys_to_delete = []
        
        if sender_id:
            keys_to_delete.extend([
                f"{self.PREFIX_SENDER_DAILY}:{sender_id}",
                f"{self.PREFIX_LAST_SEND}:{sender_id}",
                f"{self.PREFIX_BATCH_COUNT}:{sender_id}",
                f"{self.PREFIX_BATCH_PAUSE}:{sender_id}"
            ])
        
        if campaign_id:
            keys_to_delete.extend([
                f"{self.PREFIX_CAMPAIGN_DAILY}:{campaign_id}"
            ])
        
        if keys_to_delete:
            await r.delete(*keys_to_delete)
            logger.info(f"Reset rate limit counters: {keys_to_delete}")
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None

