"""
XenFlow Mailer - IMAP Worker
Celery tasks for reply detection
"""

import asyncio
from celery import shared_task

from app.workers.celery_app import celery_app
from app.database import get_db_context
from app.models import Sender
from app.models.sender import SenderStatus
from app.services.reply_detector import ReplyDetector
from app.utils.logger import get_logger

logger = get_logger(__name__)


@celery_app.task(
    name="app.workers.imap_worker.check_replies_task",
    bind=True,
    max_retries=2
)
def check_replies_task(self, sender_id: int, since_hours: int = 24):
    """
    Check for replies for a specific sender.
    """
    logger.info(f"Checking replies for sender {sender_id}")
    
    with get_db_context() as db:
        sender = db.query(Sender).filter(Sender.id == sender_id).first()
        
        if not sender:
            return {"status": "error", "message": "Sender not found"}
        
        if sender.status not in [SenderStatus.ACTIVE, SenderStatus.WARMING_UP]:
            return {"status": "skipped", "message": f"Sender status: {sender.status}"}
        
        if not sender.imap_host:
            return {"status": "skipped", "message": "No IMAP configured"}
        
        reply_detector = ReplyDetector(db)
        
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            replies = loop.run_until_complete(
                reply_detector.check_replies_for_sender(sender, since_hours)
            )
            
            loop.close()
            
            # Update sender last check time
            from sqlalchemy.sql import func
            sender.last_connection_check = func.now()
            sender.connection_error = None
            db.commit()
            
            return {
                "status": "complete",
                "sender_id": sender_id,
                "replies_found": len(replies),
                "details": [
                    {
                        "from": r.get("from_email"),
                        "is_unsubscribe": r.get("is_unsubscribe", False)
                    }
                    for r in replies
                ]
            }
            
        except Exception as e:
            logger.error(f"IMAP check error for sender {sender_id}: {str(e)}")
            
            # Update sender with error
            sender.connection_error = str(e)
            db.commit()
            
            raise self.retry(exc=e)


@celery_app.task(name="app.workers.imap_worker.check_all_replies_task")
def check_all_replies_task(since_hours: int = 24):
    """
    Check replies for all active senders.
    
    This is called periodically by Celery Beat.
    """
    logger.info("Checking replies for all senders")
    
    with get_db_context() as db:
        senders = db.query(Sender).filter(
            Sender.status.in_([SenderStatus.ACTIVE, SenderStatus.WARMING_UP]),
            Sender.imap_host.isnot(None)
        ).all()
        
        sender_ids = [s.id for s in senders]
    
    # Queue individual check tasks
    for sender_id in sender_ids:
        check_replies_task.delay(sender_id, since_hours)
    
    return {
        "status": "queued",
        "senders_checked": len(sender_ids)
    }


@celery_app.task(name="app.workers.imap_worker.mark_reply_task")
def mark_reply_task(lead_id: int, is_unsubscribe: bool = False):
    """
    Manually mark a lead as replied or unsubscribed.
    """
    with get_db_context() as db:
        reply_detector = ReplyDetector(db)
        success = reply_detector.mark_reply_manual(lead_id, is_unsubscribe)
        
        if success:
            return {
                "status": "marked",
                "lead_id": lead_id,
                "is_unsubscribe": is_unsubscribe
            }
        else:
            return {
                "status": "error",
                "message": "Lead not found"
            }


@celery_app.task(name="app.workers.imap_worker.test_imap_connection_task")
def test_imap_connection_task(sender_id: int):
    """
    Test IMAP connection for a sender.
    """
    with get_db_context() as db:
        sender = db.query(Sender).filter(Sender.id == sender_id).first()
        
        if not sender:
            return {"status": "error", "message": "Sender not found"}
        
        if not sender.imap_host:
            return {"status": "error", "message": "No IMAP configured"}
        
        try:
            import imaplib
            
            if sender.imap_use_ssl:
                imap = imaplib.IMAP4_SSL(
                    sender.imap_host,
                    sender.imap_port or 993
                )
            else:
                imap = imaplib.IMAP4(
                    sender.imap_host,
                    sender.imap_port or 143
                )
            
            imap.login(sender.imap_username, sender.imap_password_encrypted)
            imap.select(sender.imap_folder or "INBOX")
            
            # Check mailbox status
            status, data = imap.status(sender.imap_folder or "INBOX", "(MESSAGES)")
            
            imap.logout()
            
            from sqlalchemy.sql import func
            sender.last_connection_check = func.now()
            sender.connection_error = None
            # If SMTP is also working, ensure status is ACTIVE
            if sender.status == SenderStatus.DISCONNECTED and sender.smtp_host:
                # Check if SMTP was verified (connection_error is None means it passed)
                # We'll keep status as is for now, SMTP test will update it
                pass
            db.commit()
            
            return {
                "status": "success",
                "sender_id": sender_id,
                "mailbox_status": data[0].decode() if data else None
            }
            
        except Exception as e:
            sender.connection_error = str(e)
            db.commit()
            
            return {
                "status": "error",
                "sender_id": sender_id,
                "error": str(e)
            }

