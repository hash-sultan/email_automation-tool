"""
XenFlow Mailer - Suppression Service
Global suppression list management
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func

from app.models import Suppression
from app.models.suppression import SuppressionReason
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SuppressionService:
    """
    Global suppression list management.
    
    Emails in suppression list will NEVER receive emails.
    
    Suppression reasons:
    - Hard bounces
    - Soft bounce limit exceeded
    - Spam complaints
    - Unsubscribes
    - Manual additions
    - Invalid emails
    - Role-based emails (info@, support@, etc.)
    """
    
    # Role-based email prefixes to auto-suppress
    ROLE_BASED_PREFIXES = [
        'info@', 'support@', 'help@', 'sales@', 'admin@',
        'contact@', 'team@', 'hello@', 'noreply@', 'no-reply@',
        'abuse@', 'postmaster@', 'webmaster@', 'hostmaster@',
        'marketing@', 'press@', 'media@', 'legal@', 'privacy@',
        'feedback@', 'billing@', 'accounts@', 'subscribe@',
        'unsubscribe@', 'security@', 'compliance@', 'hr@',
    ]
    
    def __init__(self, db: Session):
        self.db = db
    
    def is_suppressed(self, email: str) -> bool:
        """Check if email is in suppression list."""
        return self.db.query(Suppression).filter(
            Suppression.email == email.lower()
        ).first() is not None
    
    def is_role_based(self, email: str) -> bool:
        """Check if email is a role-based address."""
        email_lower = email.lower()
        return any(email_lower.startswith(prefix) for prefix in self.ROLE_BASED_PREFIXES)
    
    def should_suppress(self, email: str) -> tuple:
        """
        Check if email should be suppressed.
        Returns (should_suppress: bool, reason: str or None)
        """
        email_lower = email.lower()
        
        # Check suppression list
        existing = self.db.query(Suppression).filter(
            Suppression.email == email_lower
        ).first()
        
        if existing:
            return True, f"In suppression list: {existing.reason.value}"
        
        # Check if role-based
        if self.is_role_based(email_lower):
            return True, "Role-based email address"
        
        return False, None
    
    def add_suppression(
        self,
        email: str,
        reason: SuppressionReason,
        source: str = None,
        campaign_id: int = None,
        error_code: str = None,
        error_message: str = None,
        notes: str = None
    ) -> Suppression:
        """Add email to suppression list."""
        email_lower = email.lower()
        
        # Check if already exists
        existing = self.db.query(Suppression).filter(
            Suppression.email == email_lower
        ).first()
        
        if existing:
            existing.bounce_count += 1
            existing.updated_at = datetime.utcnow()
            if notes:
                existing.notes = (existing.notes or "") + f"\n{notes}"
            self.db.commit()
            return existing
        
        suppression = Suppression(
            email=email_lower,
            reason=reason,
            source=source,
            campaign_id=campaign_id,
            error_code=error_code,
            error_message=error_message,
            notes=notes
        )
        
        self.db.add(suppression)
        self.db.commit()
        
        logger.info(
            f"Added to suppression list: {email_lower}",
            extra={
                "reason": reason.value,
                "source": source
            }
        )
        
        return suppression
    
    def remove_suppression(self, email: str) -> bool:
        """
        Remove email from suppression list.
        Use with caution - should rarely be needed.
        """
        result = self.db.query(Suppression).filter(
            Suppression.email == email.lower()
        ).delete()
        
        self.db.commit()
        
        if result > 0:
            logger.warning(
                f"Removed from suppression list: {email}",
                extra={"action": "manual_removal"}
            )
            return True
        
        return False
    
    def bulk_add_suppressions(
        self,
        emails: List[str],
        reason: SuppressionReason,
        source: str = "bulk_import"
    ) -> Dict[str, int]:
        """
        Bulk add emails to suppression list.
        Returns counts of added and skipped.
        """
        added = 0
        skipped = 0
        
        for email in emails:
            email_lower = email.lower().strip()
            
            if not email_lower or '@' not in email_lower:
                skipped += 1
                continue
            
            existing = self.db.query(Suppression).filter(
                Suppression.email == email_lower
            ).first()
            
            if existing:
                skipped += 1
                continue
            
            suppression = Suppression(
                email=email_lower,
                reason=reason,
                source=source
            )
            self.db.add(suppression)
            added += 1
        
        self.db.commit()
        
        logger.info(
            f"Bulk suppression import complete",
            extra={"added": added, "skipped": skipped}
        )
        
        return {"added": added, "skipped": skipped}
    
    def get_suppressions(
        self,
        reason: SuppressionReason = None,
        campaign_id: int = None,
        page: int = 1,
        page_size: int = 50
    ) -> Dict[str, Any]:
        """Get paginated suppression list."""
        query = self.db.query(Suppression)
        
        if reason:
            query = query.filter(Suppression.reason == reason)
        
        if campaign_id:
            query = query.filter(Suppression.campaign_id == campaign_id)
        
        total = query.count()
        
        items = query.order_by(Suppression.created_at.desc()).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": (total + page_size - 1) // page_size
        }
    
    def get_suppression_stats(self) -> Dict[str, Any]:
        """Get suppression statistics."""
        total = self.db.query(Suppression).count()
        
        # Count by reason
        reason_counts = self.db.query(
            Suppression.reason,
            func.count(Suppression.id)
        ).group_by(Suppression.reason).all()
        
        by_reason = {
            reason.value: count 
            for reason, count in reason_counts
        }
        
        # Recent additions (last 24 hours)
        yesterday = datetime.utcnow().replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        recent = self.db.query(Suppression).filter(
            Suppression.created_at >= yesterday
        ).count()
        
        return {
            "total": total,
            "by_reason": by_reason,
            "added_today": recent
        }
    
    def export_suppressions(
        self,
        reason: SuppressionReason = None
    ) -> List[str]:
        """
        Export all suppressed emails as list.
        """
        query = self.db.query(Suppression.email)
        
        if reason:
            query = query.filter(Suppression.reason == reason)
        
        return [email for (email,) in query.all()]
    
    def cleanup_duplicates(self) -> int:
        """
        Remove duplicate suppressions (keep oldest).
        Returns count of removed duplicates.
        """
        # Find duplicates
        duplicates = self.db.query(
            Suppression.email,
            func.count(Suppression.id).label('count')
        ).group_by(Suppression.email).having(
            func.count(Suppression.id) > 1
        ).all()
        
        removed = 0
        
        for email, count in duplicates:
            # Keep the oldest, delete the rest
            entries = self.db.query(Suppression).filter(
                Suppression.email == email
            ).order_by(Suppression.created_at.asc()).all()
            
            # Delete all except first
            for entry in entries[1:]:
                self.db.delete(entry)
                removed += 1
        
        self.db.commit()
        
        if removed > 0:
            logger.info(f"Cleaned up {removed} duplicate suppressions")
        
        return removed

