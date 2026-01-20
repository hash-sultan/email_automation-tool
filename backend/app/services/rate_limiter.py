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
    - Per-sender hourly limits
    - Per-sender daily limits
    - Per-campaign limits
    - Minimum send intervals
    - Randomized delays for human-like behavior
    """
    
    # Redis key prefixes
    PREFIX_SENDER_HOURLY = "ratelimit:sender:hourly"
    PREFIX_SENDER_DAILY = "ratelimit:sender:daily"
    PREFIX_CAMPAIGN_HOURLY = "ratelimit:campaign:hourly"
    PREFIX_CAMPAIGN_DAILY = "ratelimit:campaign:daily"
    PREFIX_LAST_SEND = "ratelimit:lastsend"
    
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
        sender_hourly_limit: int = None,
        sender_daily_limit: int = None,
        campaign_hourly_limit: int = None,
        campaign_daily_limit: int = None
    ) -> Tuple[bool, int]:
        """
        Check if we can send an email now.
        
        Returns:
            (allowed: bool, wait_seconds: int)
            - If allowed is True, wait_seconds is 0
            - If allowed is False, wait_seconds is how long to wait
        """
        r = await self._get_redis()
        
        # Use defaults if not provided
        sender_hourly_limit = sender_hourly_limit or settings.MAX_EMAILS_PER_HOUR
        sender_daily_limit = sender_daily_limit or settings.MAX_EMAILS_PER_DAY
        campaign_hourly_limit = campaign_hourly_limit or 20
        campaign_daily_limit = campaign_daily_limit or 100
        
        # Check global safety limits
        sender_hourly_key = f"{self.PREFIX_SENDER_HOURLY}:{sender_id}"
        sender_daily_key = f"{self.PREFIX_SENDER_DAILY}:{sender_id}"
        campaign_hourly_key = f"{self.PREFIX_CAMPAIGN_HOURLY}:{campaign_id}"
        campaign_daily_key = f"{self.PREFIX_CAMPAIGN_DAILY}:{campaign_id}"
        last_send_key = f"{self.PREFIX_LAST_SEND}:{sender_id}"
        
        # Get current counts
        pipeline = r.pipeline()
        pipeline.get(sender_hourly_key)
        pipeline.get(sender_daily_key)
        pipeline.get(campaign_hourly_key)
        pipeline.get(campaign_daily_key)
        pipeline.get(last_send_key)
        
        results = await pipeline.execute()
        
        sender_hourly_count = int(results[0] or 0)
        sender_daily_count = int(results[1] or 0)
        campaign_hourly_count = int(results[2] or 0)
        campaign_daily_count = int(results[3] or 0)
        last_send_time = float(results[4] or 0)
        
        # Check sender hourly limit
        if sender_hourly_count >= min(sender_hourly_limit, SafetyLimits.ABSOLUTE_MAX_EMAILS_PER_HOUR):
            # Calculate wait time until next hour
            now = datetime.utcnow()
            next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            wait_seconds = int((next_hour - now).total_seconds())
            logger.debug(f"Sender hourly limit reached: {sender_hourly_count}/{sender_hourly_limit}")
            return False, wait_seconds
        
        # Check sender daily limit
        if sender_daily_count >= min(sender_daily_limit, SafetyLimits.ABSOLUTE_MAX_EMAILS_PER_DAY):
            # Calculate wait time until midnight
            now = datetime.utcnow()
            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            wait_seconds = int((tomorrow - now).total_seconds())
            logger.debug(f"Sender daily limit reached: {sender_daily_count}/{sender_daily_limit}")
            return False, wait_seconds
        
        # Check campaign hourly limit
        if campaign_hourly_count >= campaign_hourly_limit:
            now = datetime.utcnow()
            next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            wait_seconds = int((next_hour - now).total_seconds())
            logger.debug(f"Campaign hourly limit reached: {campaign_hourly_count}/{campaign_hourly_limit}")
            return False, wait_seconds
        
        # Check campaign daily limit
        if campaign_daily_count >= campaign_daily_limit:
            now = datetime.utcnow()
            tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            wait_seconds = int((tomorrow - now).total_seconds())
            logger.debug(f"Campaign daily limit reached: {campaign_daily_count}/{campaign_daily_limit}")
            return False, wait_seconds
        
        # Check minimum send interval
        if last_send_time > 0:
            elapsed = datetime.utcnow().timestamp() - last_send_time
            min_interval = SafetyLimits.MIN_EMAIL_INTERVAL_SECONDS
            
            if elapsed < min_interval:
                wait_seconds = int(min_interval - elapsed)
                logger.debug(f"Min interval not reached: wait {wait_seconds}s")
                return False, wait_seconds
        
        return True, 0
    
    async def record_send(self, sender_id: int, campaign_id: int) -> None:
        """
        Record that an email was sent.
        Updates all relevant counters with proper expiry.
        """
        r = await self._get_redis()
        
        now = datetime.utcnow()
        
        # Calculate expiry times
        seconds_until_next_hour = 3600 - (now.minute * 60 + now.second)
        seconds_until_midnight = (
            (24 - now.hour - 1) * 3600 + 
            (60 - now.minute - 1) * 60 + 
            (60 - now.second)
        )
        
        # Keys
        sender_hourly_key = f"{self.PREFIX_SENDER_HOURLY}:{sender_id}"
        sender_daily_key = f"{self.PREFIX_SENDER_DAILY}:{sender_id}"
        campaign_hourly_key = f"{self.PREFIX_CAMPAIGN_HOURLY}:{campaign_id}"
        campaign_daily_key = f"{self.PREFIX_CAMPAIGN_DAILY}:{campaign_id}"
        last_send_key = f"{self.PREFIX_LAST_SEND}:{sender_id}"
        
        # Increment counters with expiry
        pipeline = r.pipeline()
        
        # Sender hourly
        pipeline.incr(sender_hourly_key)
        pipeline.expire(sender_hourly_key, seconds_until_next_hour)
        
        # Sender daily
        pipeline.incr(sender_daily_key)
        pipeline.expire(sender_daily_key, seconds_until_midnight)
        
        # Campaign hourly
        pipeline.incr(campaign_hourly_key)
        pipeline.expire(campaign_hourly_key, seconds_until_next_hour)
        
        # Campaign daily
        pipeline.incr(campaign_daily_key)
        pipeline.expire(campaign_daily_key, seconds_until_midnight)
        
        # Last send time
        pipeline.set(last_send_key, now.timestamp())
        pipeline.expire(last_send_key, 3600)  # 1 hour expiry
        
        await pipeline.execute()
        
        logger.debug(f"Recorded send for sender {sender_id}, campaign {campaign_id}")
    
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
            sender_hourly = await r.get(f"{self.PREFIX_SENDER_HOURLY}:{sender_id}")
            sender_daily = await r.get(f"{self.PREFIX_SENDER_DAILY}:{sender_id}")
            stats["sender_hourly_count"] = int(sender_hourly or 0)
            stats["sender_daily_count"] = int(sender_daily or 0)
        
        if campaign_id:
            campaign_hourly = await r.get(f"{self.PREFIX_CAMPAIGN_HOURLY}:{campaign_id}")
            campaign_daily = await r.get(f"{self.PREFIX_CAMPAIGN_DAILY}:{campaign_id}")
            stats["campaign_hourly_count"] = int(campaign_hourly or 0)
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
                f"{self.PREFIX_SENDER_HOURLY}:{sender_id}",
                f"{self.PREFIX_SENDER_DAILY}:{sender_id}",
                f"{self.PREFIX_LAST_SEND}:{sender_id}"
            ])
        
        if campaign_id:
            keys_to_delete.extend([
                f"{self.PREFIX_CAMPAIGN_HOURLY}:{campaign_id}",
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

