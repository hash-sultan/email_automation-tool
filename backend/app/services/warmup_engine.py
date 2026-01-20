"""
XenFlow Mailer - Warmup Engine
Gradual sender warming for deliverability protection
"""

from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models import Sender
from app.models.sender import SenderStatus
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class WarmupEngine:
    """
    Sender warmup engine for gradual email volume increase.
    
    Warmup Schedule (Default):
    - Day 1-3:  10 emails/day
    - Day 4-7:  25 emails/day
    - Day 8-14: 50 emails/day
    - Day 15+:  Gradual increase up to base_daily_limit
    
    This protects sender reputation with new email addresses.
    """
    
    # Default warmup schedule
    DEFAULT_SCHEDULE = {
        (1, 3): 10,     # Days 1-3: 10 emails
        (4, 7): 25,     # Days 4-7: 25 emails
        (8, 14): 50,    # Days 8-14: 50 emails
        (15, 21): 75,   # Days 15-21: 75 emails
        (22, 28): 100,  # Days 22-28: 100 emails
        (29, float('inf')): 150,  # Day 29+: 150 emails (or base limit)
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def start_warmup(self, sender: Sender) -> Sender:
        """
        Start warmup for a sender.
        """
        if sender.warmup_enabled and not sender.warmup_start_date:
            sender.warmup_start_date = date.today()
            sender.warmup_current_day = 1
            sender.current_daily_limit = self.get_limit_for_day(1)
            sender.status = SenderStatus.WARMING_UP
            
            self.db.commit()
            
            logger.info(
                f"Started warmup for sender {sender.email}",
                extra={"sender_id": sender.id, "daily_limit": sender.current_daily_limit}
            )
        
        return sender
    
    def update_warmup_day(self, sender: Sender) -> Sender:
        """
        Update sender warmup progress for a new day.
        Should be called daily.
        """
        if not sender.warmup_enabled or not sender.warmup_start_date:
            return sender
        
        today = date.today()
        warmup_day = (today - sender.warmup_start_date).days + 1
        
        if warmup_day != sender.warmup_current_day:
            sender.warmup_current_day = warmup_day
            sender.current_daily_limit = self.get_limit_for_day(warmup_day)
            
            # Check if warmup is complete
            if warmup_day >= 29 and sender.current_daily_limit >= sender.base_daily_limit:
                sender.warmup_enabled = False
                sender.current_daily_limit = sender.base_daily_limit
                sender.status = SenderStatus.ACTIVE
                
                logger.info(f"Warmup complete for sender {sender.email}")
            
            self.db.commit()
            
            logger.debug(
                f"Updated warmup day for sender {sender.email}",
                extra={
                    "sender_id": sender.id,
                    "warmup_day": warmup_day,
                    "daily_limit": sender.current_daily_limit
                }
            )
        
        return sender
    
    def get_limit_for_day(self, day: int) -> int:
        """
        Get the email limit for a specific warmup day.
        """
        for (start, end), limit in self.DEFAULT_SCHEDULE.items():
            if start <= day <= end:
                return min(limit, settings.MAX_EMAILS_PER_DAY)
        
        return settings.WARMUP_DAY_15_PLUS_LIMIT
    
    def get_warmup_status(self, sender: Sender) -> Dict[str, Any]:
        """
        Get detailed warmup status for a sender.
        """
        if not sender.warmup_enabled:
            return {
                "enabled": False,
                "status": "completed" if sender.warmup_start_date else "not_started",
                "current_limit": sender.base_daily_limit
            }
        
        if not sender.warmup_start_date:
            return {
                "enabled": True,
                "status": "pending",
                "current_limit": self.get_limit_for_day(1)
            }
        
        today = date.today()
        warmup_day = (today - sender.warmup_start_date).days + 1
        current_limit = sender.current_daily_limit
        
        # Calculate progress
        total_warmup_days = 28
        progress_percent = min(100, (warmup_day / total_warmup_days) * 100)
        
        # Calculate days until full capacity
        days_remaining = max(0, total_warmup_days - warmup_day)
        
        return {
            "enabled": True,
            "status": "in_progress",
            "start_date": sender.warmup_start_date.isoformat(),
            "current_day": warmup_day,
            "current_limit": current_limit,
            "base_limit": sender.base_daily_limit,
            "progress_percent": round(progress_percent, 1),
            "days_remaining": days_remaining,
            "estimated_completion": (today + timedelta(days=days_remaining)).isoformat(),
            "schedule": self._get_schedule_info(warmup_day)
        }
    
    def _get_schedule_info(self, current_day: int) -> List[Dict[str, Any]]:
        """
        Get schedule info with current position highlighted.
        """
        schedule = []
        
        for (start, end), limit in self.DEFAULT_SCHEDULE.items():
            if end == float('inf'):
                end = "+"
                label = f"Day {start}+"
            else:
                label = f"Day {start}-{end}"
            
            is_current = False
            if isinstance(end, str):
                is_current = current_day >= start
            else:
                is_current = start <= current_day <= end
            
            schedule.append({
                "label": label,
                "limit": limit,
                "is_current": is_current
            })
        
        return schedule
    
    def update_all_senders(self) -> int:
        """
        Update warmup status for all active senders.
        Should be called once per day (via scheduler).
        Returns count of updated senders.
        """
        senders = self.db.query(Sender).filter(
            and_(
                Sender.warmup_enabled == True,
                Sender.warmup_start_date.isnot(None),
                Sender.status.in_([SenderStatus.WARMING_UP, SenderStatus.ACTIVE])
            )
        ).all()
        
        updated_count = 0
        for sender in senders:
            self.update_warmup_day(sender)
            updated_count += 1
        
        logger.info(f"Updated warmup status for {updated_count} senders")
        return updated_count
    
    def skip_warmup(self, sender: Sender) -> Sender:
        """
        Skip warmup for a sender (use with caution).
        Only do this for aged/warmed accounts.
        """
        sender.warmup_enabled = False
        sender.current_daily_limit = sender.base_daily_limit
        sender.status = SenderStatus.ACTIVE
        
        self.db.commit()
        
        logger.warning(
            f"Warmup skipped for sender {sender.email}",
            extra={"sender_id": sender.id}
        )
        
        return sender
    
    def reset_warmup(self, sender: Sender) -> Sender:
        """
        Reset warmup for a sender (starts fresh).
        """
        sender.warmup_enabled = True
        sender.warmup_start_date = None
        sender.warmup_current_day = 0
        sender.current_daily_limit = self.get_limit_for_day(1)
        sender.status = SenderStatus.PAUSED
        
        self.db.commit()
        
        logger.info(
            f"Warmup reset for sender {sender.email}",
            extra={"sender_id": sender.id}
        )
        
        return sender

