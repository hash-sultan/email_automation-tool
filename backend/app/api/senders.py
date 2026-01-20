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
    query = db.query(Sender)
    
    if status:
        query = query.filter(Sender.status == status)
    
    senders = query.order_by(Sender.created_at.desc()).all()
    responses = []
    for s in senders:
        response = SenderResponse.model_validate(s)
        # Compute is_verified: True if connection_error is None and last_connection_check exists
        response.is_verified = s.connection_error is None and s.last_connection_check is not None
        # Map status to is_active for frontend compatibility
        # Frontend expects is_active boolean, backend has status enum
        response.is_active = s.status == SenderStatus.ACTIVE
        responses.append(response)
    return responses


@router.get("/{sender_id}", response_model=SenderResponse)
def get_sender(sender_id: int, db: Session = Depends(get_db)):
    """Get a specific sender with stats."""
    sender = db.query(Sender).filter(Sender.id == sender_id).first()
    if not sender:
        raise HTTPException(status_code=404, detail="Sender not found")
    
    response = SenderResponse.model_validate(sender)
    
    # Compute is_verified: True if connection_error is None and last_connection_check exists
    response.is_verified = sender.connection_error is None and sender.last_connection_check is not None
    # Map status to is_active for frontend compatibility
    response.is_active = sender.status == SenderStatus.ACTIVE
    
    # Add stats
    response.stats = SenderStats(
        emails_sent_today=sender.emails_sent_today,
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
    # Check for duplicate email
    existing = db.query(Sender).filter(
        Sender.email == sender_data.email.lower()
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Sender email already exists")
    
    sender_dict = sender_data.model_dump(exclude={'smtp_config', 'imap_config', 'oauth_config'})
    sender_dict['email'] = sender_data.email.lower()
    
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
    
    db.commit()
    db.refresh(sender)
    
    response = SenderResponse.model_validate(sender)
    response.is_verified = sender.connection_error is None and sender.last_connection_check is not None
    response.is_active = sender.status == SenderStatus.ACTIVE
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

