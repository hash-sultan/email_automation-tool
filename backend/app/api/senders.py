"""
XenFlow Mailer - Senders API
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.database import get_db
from app.models import Sender
from app.models.sender import SenderStatus, ProviderType
from app.schemas.sender import (
    SenderCreate, SenderUpdate, SenderResponse, SenderStats
)
from app.services.warmup_engine import WarmupEngine
from app.workers.warmup_worker import start_warmup_task, skip_warmup_task, reset_warmup_task
from app.workers.imap_worker import test_imap_connection_task
from app.providers.gmail import GmailProvider
from app.providers.outlook import OutlookProvider
from app.config import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()
settings = get_settings()


@router.get("/", response_model=List[SenderResponse])
def list_senders(
    status: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all senders."""
    from datetime import datetime
    from app.models.email_log import EmailLog, EmailStatus
    
    query = db.query(Sender)
    
    if status:
        query = query.filter(Sender.status == status)
    
    senders = query.order_by(Sender.created_at.desc()).all()
    
    # Auto-fix: If warmup is disabled but current_daily_limit is still low, fix it
    fixed_count = 0
    for s in senders:
        if not s.warmup_enabled and s.current_daily_limit < s.base_daily_limit:
            s.current_daily_limit = s.base_daily_limit
            if s.status == SenderStatus.WARMING_UP:
                s.status = SenderStatus.ACTIVE
                s.warmup_start_date = None
                s.warmup_current_day = 0
            fixed_count += 1
    
    if fixed_count > 0:
        db.commit()
        logger.info(f"Auto-fixed {fixed_count} senders with warmup disabled but low daily limits")
    
    # Calculate today's date for email counting
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    responses = []
    for s in senders:
        # Calculate emails_sent_today from email_logs (more accurate than counter)
        emails_sent_today = db.query(EmailLog).filter(
            EmailLog.sender_id == s.id,
            func.coalesce(EmailLog.sent_at, EmailLog.created_at) >= today,
            EmailLog.status.in_([
                EmailStatus.SENT,
                EmailStatus.DELIVERED,
                EmailStatus.OPENED,
                EmailStatus.CLICKED,
                EmailStatus.REPLIED
            ])
        ).count()
        
        # Calculate total emails sent (all time) from email_logs
        total_emails_sent = db.query(EmailLog).filter(
            EmailLog.sender_id == s.id,
            EmailLog.status.in_([
                EmailStatus.SENT,
                EmailStatus.DELIVERED,
                EmailStatus.OPENED,
                EmailStatus.CLICKED,
                EmailStatus.REPLIED
            ])
        ).count()
        
        response = SenderResponse.model_validate(s)
        # Override emails_sent_today with calculated value from email_logs
        response.emails_sent_today = emails_sent_today
        # Override total_emails_sent with calculated value from email_logs
        response.total_emails_sent = total_emails_sent
        # Compute is_verified: True if connection_error is None and last_connection_check exists
        response.is_verified = s.connection_error is None and s.last_connection_check is not None
        # Map status to is_active for frontend compatibility
        # Frontend expects is_active boolean, backend has status enum
        response.is_active = s.status == SenderStatus.ACTIVE
        # Add warmup_day alias for frontend compatibility
        response.warmup_day = s.warmup_current_day
        responses.append(response)
    return responses


@router.get("/{sender_id}/stats-by-date")
def get_sender_stats_by_date(
    sender_id: int,
    days: int = Query(30, ge=1, le=365, description="Number of days to show"),
    db: Session = Depends(get_db)
):
    """Get email stats by date for a sender."""
    from datetime import datetime, timedelta
    from app.models.email_log import EmailLog, EmailStatus
    
    sender = db.query(Sender).filter(Sender.id == sender_id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")
    
    # Calculate date range
    end_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    start_date = end_date - timedelta(days=days-1)
    
    # Query emails grouped by date
    stats_by_date = db.query(
        func.date(func.coalesce(EmailLog.sent_at, EmailLog.created_at)).label('date'),
        func.count(EmailLog.id).label('count')
    ).filter(
        EmailLog.sender_id == sender_id,
        func.coalesce(EmailLog.sent_at, EmailLog.created_at) >= start_date,
        EmailLog.status.in_([
            EmailStatus.SENT,
            EmailStatus.DELIVERED,
            EmailStatus.OPENED,
            EmailStatus.CLICKED,
            EmailStatus.REPLIED
        ])
    ).group_by(
        func.date(func.coalesce(EmailLog.sent_at, EmailLog.created_at))
    ).order_by(
        func.date(func.coalesce(EmailLog.sent_at, EmailLog.created_at)).desc()
    ).all()
    
    # Convert to dictionary format
    result = {}
    for stat in stats_by_date:
        date_str = stat.date.isoformat() if hasattr(stat.date, 'isoformat') else str(stat.date)
        result[date_str] = stat.count
    
    return {
        "sender_id": sender_id,
        "days": days,
        "stats_by_date": result
    }


@router.get("/{sender_id}", response_model=SenderResponse)
def get_sender(sender_id: int, db: Session = Depends(get_db)):
    """Get a specific sender with stats."""
    from datetime import datetime
    from app.models.email_log import EmailLog, EmailStatus
    
    sender = db.query(Sender).filter(Sender.id == sender_id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")
    
    # Calculate emails_sent_today from email_logs (more accurate than counter)
    today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    emails_sent_today = db.query(EmailLog).filter(
        EmailLog.sender_id == sender.id,
        func.coalesce(EmailLog.sent_at, EmailLog.created_at) >= today,
        EmailLog.status.in_([
            EmailStatus.SENT,
            EmailStatus.DELIVERED,
            EmailStatus.OPENED,
            EmailStatus.CLICKED,
            EmailStatus.REPLIED
        ])
    ).count()
    
    # Calculate total emails sent (all time) from email_logs
    total_emails_sent = db.query(EmailLog).filter(
        EmailLog.sender_id == sender.id,
        EmailLog.status.in_([
            EmailStatus.SENT,
            EmailStatus.DELIVERED,
            EmailStatus.OPENED,
            EmailStatus.CLICKED,
            EmailStatus.REPLIED
        ])
    ).count()
    
    response = SenderResponse.model_validate(sender)
    # Override emails_sent_today with calculated value from email_logs
    response.emails_sent_today = emails_sent_today
    # Override total_emails_sent with calculated value from email_logs
    response.total_emails_sent = total_emails_sent
    
    # Compute is_verified: True if connection_error is None and last_connection_check exists
    response.is_verified = sender.connection_error is None and sender.last_connection_check is not None
    # Map status to is_active for frontend compatibility
    response.is_active = sender.status == SenderStatus.ACTIVE
    # Add warmup_day alias for frontend compatibility
    response.warmup_day = sender.warmup_current_day
    
    # Add stats
    response.stats = SenderStats(
        emails_sent_today=emails_sent_today,  # Use calculated value
        emails_sent_this_hour=sender.emails_sent_this_hour,
        total_emails_sent=sender.total_emails_sent,
        total_bounces=sender.total_bounces,
        total_complaints=sender.total_complaints,
        bounce_rate=sender.bounce_rate,
        complaint_rate=sender.complaint_rate,
        reputation_score=sender.reputation_score,
        current_daily_limit=sender.current_daily_limit,
        warmup_day=sender.warmup_current_day
    )
    
    return response


@router.post("/", response_model=SenderResponse)
def create_sender(sender_data: SenderCreate, db: Session = Depends(get_db)):
    """Create a new sender with immediate SMTP validation."""
    from app.api.settings import load_settings
    
    # Check for duplicate email
    existing = db.query(Sender).filter(
        Sender.email == sender_data.email.lower()
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Sender email already exists")
    
    sender_dict = sender_data.model_dump(exclude={'smtp_config', 'imap_config', 'oauth_config'})
    sender_dict['email'] = sender_data.email.lower()
    
    # Use settings default for base_daily_limit if not explicitly provided
    if 'base_daily_limit' not in sender_dict or sender_dict.get('base_daily_limit') is None:
        settings = load_settings()
        sender_dict['base_daily_limit'] = settings.get('sender_daily_limit', 200)
    
    # Handle SMTP config
    if sender_data.smtp_config:
        sender_dict['smtp_host'] = sender_data.smtp_config.host
        sender_dict['smtp_port'] = sender_data.smtp_config.port
        sender_dict['smtp_username'] = sender_data.smtp_config.username
        sender_dict['smtp_password_encrypted'] = sender_data.smtp_config.password  # Should encrypt
        sender_dict['smtp_use_tls'] = sender_data.smtp_config.use_tls
    
    # Handle IMAP config
    if sender_data.imap_config:
        sender_dict['imap_host'] = sender_data.imap_config.host
        sender_dict['imap_port'] = sender_data.imap_config.port
        sender_dict['imap_username'] = sender_data.imap_config.username
        sender_dict['imap_password_encrypted'] = sender_data.imap_config.password
        sender_dict['imap_use_ssl'] = sender_data.imap_config.use_ssl
        sender_dict['imap_folder'] = sender_data.imap_config.folder
    
    sender = Sender(**sender_dict)
    
    # If warmup is disabled, set current_daily_limit to base_daily_limit
    if not sender.warmup_enabled:
        sender.current_daily_limit = sender.base_daily_limit
    
    # Test SMTP connection immediately before saving
    if sender_data.smtp_config:
        from app.providers.smtp import SMTPProvider
        import asyncio
        
        smtp_provider = SMTPProvider(
            sender_email=sender_data.email,
            sender_name=sender_dict.get('name', sender_data.email),
            smtp_host=sender_data.smtp_config.host,
            smtp_port=sender_data.smtp_config.port,
            smtp_username=sender_data.smtp_config.username or sender_data.email,
            smtp_password=sender_data.smtp_config.password,
            use_tls=sender_data.smtp_config.use_tls
        )
        
        # Test connection synchronously
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            success, error_msg = loop.run_until_complete(smtp_provider.verify_connection())
            loop.close()
            
            if success:
                sender.status = SenderStatus.ACTIVE
                sender.last_connection_check = func.now()
                sender.connection_error = None
                logger.info(f"SMTP connection verified for {sender_data.email}")
            else:
                sender.status = SenderStatus.DISCONNECTED
                sender.connection_error = error_msg or "SMTP connection test failed"
                logger.warning(f"SMTP connection failed for {sender_data.email}: {error_msg}")
        except Exception as e:
            sender.status = SenderStatus.DISCONNECTED
            sender.connection_error = f"Connection test error: {str(e)}"
            logger.error(f"SMTP connection test exception for {sender_data.email}: {str(e)}")
    else:
        # No SMTP config - set as disconnected
        sender.status = SenderStatus.DISCONNECTED
        sender.connection_error = "No SMTP configuration provided"
    
    db.add(sender)
    db.commit()
    db.refresh(sender)
    
    # Start warmup if enabled and connection is good
    if sender.warmup_enabled and sender.status == SenderStatus.ACTIVE:
        start_warmup_task.delay(sender.id)
    
    response = SenderResponse.model_validate(sender)
    response.is_verified = sender.status == SenderStatus.ACTIVE and sender.connection_error is None
    response.is_active = sender.status == SenderStatus.ACTIVE
    response.warmup_day = sender.warmup_current_day
    return response


@router.put("/{sender_id}", response_model=SenderResponse)
def update_sender(
    sender_id: int,
    sender_data: SenderUpdate,
    db: Session = Depends(get_db)
):
    """Update a sender."""
    sender = db.query(Sender).filter(Sender.id == sender_id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")
    
    update_data = sender_data.model_dump(exclude_unset=True, exclude={'smtp_config', 'imap_config'})
    
    # Handle SMTP config
    if sender_data.smtp_config:
        update_data['smtp_host'] = sender_data.smtp_config.host
        update_data['smtp_port'] = sender_data.smtp_config.port
        update_data['smtp_username'] = sender_data.smtp_config.username
        update_data['smtp_password_encrypted'] = sender_data.smtp_config.password
        update_data['smtp_use_tls'] = sender_data.smtp_config.use_tls
    
    # Handle IMAP config
    if sender_data.imap_config:
        update_data['imap_host'] = sender_data.imap_config.host
        update_data['imap_port'] = sender_data.imap_config.port
        update_data['imap_username'] = sender_data.imap_config.username
        update_data['imap_password_encrypted'] = sender_data.imap_config.password
        update_data['imap_use_ssl'] = sender_data.imap_config.use_ssl
        update_data['imap_folder'] = sender_data.imap_config.folder
    
    for key, value in update_data.items():
        setattr(sender, key, value)
    
    # If warmup is disabled, set current_daily_limit to base_daily_limit
    if 'warmup_enabled' in update_data and not update_data['warmup_enabled']:
        sender.current_daily_limit = sender.base_daily_limit
        # If sender was in warmup, mark as active
        if sender.status == SenderStatus.WARMING_UP:
            sender.status = SenderStatus.ACTIVE
            sender.warmup_start_date = None
            sender.warmup_current_day = 0
    # Also fix if warmup is already disabled but current_daily_limit is still low
    elif not sender.warmup_enabled and sender.current_daily_limit < sender.base_daily_limit:
        sender.current_daily_limit = sender.base_daily_limit
        if sender.status == SenderStatus.WARMING_UP:
            sender.status = SenderStatus.ACTIVE
            sender.warmup_start_date = None
            sender.warmup_current_day = 0
    
    db.commit()
    db.refresh(sender)
    
    response = SenderResponse.model_validate(sender)
    response.is_verified = sender.connection_error is None and sender.last_connection_check is not None
    response.is_active = sender.status == SenderStatus.ACTIVE
    response.warmup_day = sender.warmup_current_day
    return response


@router.delete("/{sender_id}")
def delete_sender(sender_id: int, db: Session = Depends(get_db)):
    """Delete a sender."""
    sender = db.query(Sender).filter(Sender.id == sender_id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")
    
    if sender.status == SenderStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Cannot delete active sender")
    
    db.delete(sender)
    db.commit()
    
    return {"status": "deleted", "sender_id": sender_id}


@router.get("/{sender_id}/warmup-status")
def get_warmup_status(sender_id: int, db: Session = Depends(get_db)):
    """Get warmup status for a sender."""
    sender = db.query(Sender).filter(Sender.id == sender_id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")
    
    warmup_engine = WarmupEngine(db)
    return warmup_engine.get_warmup_status(sender)


@router.post("/{sender_id}/start-warmup")
def start_warmup(sender_id: int, db: Session = Depends(get_db)):
    """Start warmup for a sender."""
    sender = db.query(Sender).filter(Sender.id == sender_id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")
    
    start_warmup_task.delay(sender_id)
    
    return {"status": "starting", "sender_id": sender_id}


@router.post("/{sender_id}/skip-warmup")
def skip_warmup(sender_id: int, db: Session = Depends(get_db)):
    """Skip warmup for a sender (use with caution)."""
    sender = db.query(Sender).filter(Sender.id == sender_id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")
    
    skip_warmup_task.delay(sender_id)
    
    return {"status": "skipping", "sender_id": sender_id}


@router.post("/fix-warmup-limits")
def fix_warmup_limits(db: Session = Depends(get_db)):
    """
    Bulk fix: Update all senders with warmup disabled to use their full base_daily_limit.
    This fixes existing senders that were created with warmup disabled but still have low daily limits.
    """
    senders = db.query(Sender).filter(
        Sender.warmup_enabled == False,
        Sender.current_daily_limit < Sender.base_daily_limit
    ).all()
    
    fixed_count = 0
    for sender in senders:
        sender.current_daily_limit = sender.base_daily_limit
        if sender.status == SenderStatus.WARMING_UP:
            sender.status = SenderStatus.ACTIVE
            sender.warmup_start_date = None
            sender.warmup_current_day = 0
        fixed_count += 1
    
    db.commit()
    
    logger.info(f"Fixed {fixed_count} senders with warmup disabled but low daily limits")
    
    return {
        "status": "success",
        "message": f"Fixed {fixed_count} senders",
        "fixed_count": fixed_count
    }


@router.post("/{sender_id}/test-connection")
def test_connection(sender_id: int, db: Session = Depends(get_db)):
    """Test IMAP connection for a sender."""
    sender = db.query(Sender).filter(Sender.id == sender_id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")
    
    test_imap_connection_task.delay(sender_id)
    
    return {"status": "testing", "sender_id": sender_id}


@router.post("/{sender_id}/verify")
def verify_sender(sender_id: int, db: Session = Depends(get_db)):
    """
    Verify sender by testing both SMTP and IMAP connections.
    Updates sender status based on test results.
    """
    sender = db.query(Sender).filter(Sender.id == sender_id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")
    
    # Test SMTP connection immediately (synchronous)
    smtp_success = False
    smtp_error = None
    
    if sender.smtp_host:
        from app.providers.smtp import SMTPProvider
        import asyncio
        
        smtp_provider = SMTPProvider(
            sender_email=sender.email,
            sender_name=sender.name,
            smtp_host=sender.smtp_host,
            smtp_port=sender.smtp_port or 587,
            smtp_username=sender.smtp_username or sender.email,
            smtp_password=sender.smtp_password_encrypted,
            use_tls=sender.smtp_use_tls
        )
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            smtp_success, smtp_error = loop.run_until_complete(smtp_provider.verify_connection())
            loop.close()
        except Exception as e:
            smtp_error = f"SMTP test error: {str(e)}"
            logger.error(f"SMTP verification error for sender {sender_id}: {str(e)}")
    
    # Update sender status based on SMTP test
    if smtp_success:
        sender.status = SenderStatus.ACTIVE
        sender.last_connection_check = func.now()
        sender.connection_error = None
        logger.info(f"SMTP verified for sender {sender_id}")
    else:
        sender.status = SenderStatus.DISCONNECTED
        sender.connection_error = smtp_error or "SMTP connection test failed"
        logger.warning(f"SMTP verification failed for sender {sender_id}: {smtp_error}")
    
    db.commit()
    
    # Also test IMAP in background (non-blocking)
    if sender.imap_host:
        test_imap_connection_task.delay(sender_id)
    
    return {
        "status": "verified" if smtp_success else "failed",
        "sender_id": sender_id,
        "smtp_verified": smtp_success,
        "error": smtp_error if not smtp_success else None
    }


# OAuth Endpoints

@router.get("/oauth/gmail/authorize")
def get_gmail_auth_url(redirect_uri: Optional[str] = None):
    """Get Gmail OAuth authorization URL."""
    if not settings.GMAIL_CLIENT_ID:
        raise HTTPException(status_code=400, detail="Gmail OAuth not configured")
    
    auth_url = GmailProvider.get_authorization_url(
        client_id=settings.GMAIL_CLIENT_ID,
        redirect_uri=redirect_uri or settings.GMAIL_REDIRECT_URI
    )
    
    return {"auth_url": auth_url}


@router.post("/oauth/gmail/callback")
def gmail_oauth_callback(
    code: str,
    redirect_uri: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Handle Gmail OAuth callback and create/update sender."""
    if not settings.GMAIL_CLIENT_ID or not settings.GMAIL_CLIENT_SECRET:
        raise HTTPException(status_code=400, detail="Gmail OAuth not configured")
    
    try:
        tokens = GmailProvider.exchange_code_for_tokens(
            code=code,
            client_id=settings.GMAIL_CLIENT_ID,
            client_secret=settings.GMAIL_CLIENT_SECRET,
            redirect_uri=redirect_uri or settings.GMAIL_REDIRECT_URI
        )
        
        return {
            "status": "success",
            "tokens": {
                "access_token": tokens["access_token"][:20] + "...",
                "has_refresh_token": bool(tokens.get("refresh_token")),
                "expiry": tokens.get("expiry")
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/oauth/outlook/authorize")
def get_outlook_auth_url(redirect_uri: Optional[str] = None):
    """Get Outlook OAuth authorization URL."""
    # Would need separate Outlook credentials
    raise HTTPException(status_code=501, detail="Outlook OAuth not yet implemented")

