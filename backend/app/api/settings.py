"""
XenFlow Mailer - Settings API
"""

import json
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import update

from app.database import get_db
from app.models import Campaign, EmailLog, Lead, Sender, CampaignSender, FollowUpTemplate
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()

# Settings file path (in backend directory)
SETTINGS_FILE = Path(__file__).parent.parent.parent / "settings.json"


class SystemSettings(BaseModel):
    campaign_daily_limit: int = Field(default=500, ge=1, le=1000)  # Default 500, max 1000
    sender_daily_limit: int = Field(default=200, ge=1, le=500)  # Default 200, max 500
    reply_check_interval_minutes: int = Field(default=5, ge=1, le=60)
    reply_look_back_hours: int = Field(default=24, ge=1, le=168)


def load_settings() -> Dict[str, Any]:
    """Load settings from file or return defaults"""
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load settings file: {e}, using defaults")
    
    # Return defaults
    defaults = SystemSettings().model_dump()
    save_settings(defaults)
    return defaults


def save_settings(settings: Dict[str, Any]) -> None:
    """Save settings to file"""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save settings file: {e}")


@router.get("/", response_model=SystemSettings)
def get_settings():
    """Get current system settings"""
    settings = load_settings()
    return SystemSettings(**settings)


@router.put("/", response_model=Dict[str, str])
def update_settings(settings: SystemSettings):
    """Update system settings"""
    try:
        settings_dict = settings.model_dump()
        save_settings(settings_dict)
        logger.info("System settings updated", extra=settings_dict)
        return {
            "status": "success",
            "message": "Settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Failed to update settings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


@router.post("/reset-all-data")
def reset_all_data(db: Session = Depends(get_db)):
    """
    Reset all campaign and activity data for a fresh start.
    
    This will:
    - Delete all campaigns (and their leads, email logs, follow-up templates)
    - Delete all email logs (including replies)
    - Reset all sender counters to 0
    - Keep templates and senders intact
    """
    try:
        # Count what will be deleted for reporting
        campaign_count = db.query(Campaign).count()
        email_log_count = db.query(EmailLog).count()
        lead_count = db.query(Lead).count()
        
        # Delete all email logs first (including replies)
        # This must be done before deleting campaigns to avoid foreign key issues
        deleted_email_logs = db.query(EmailLog).delete()
        
        # Delete all campaigns (cascades to leads, campaign_senders, followup_templates)
        deleted_campaigns = db.query(Campaign).delete()
        
        # Delete any orphaned leads (shouldn't happen after campaign delete, but just in case)
        deleted_leads = db.query(Lead).delete()
        
        # Delete any orphaned campaign_senders (shouldn't happen after campaign delete, but just in case)
        deleted_campaign_senders = db.query(CampaignSender).delete()
        
        # Delete any orphaned followup_templates (shouldn't happen after campaign delete, but just in case)
        deleted_followup_templates = db.query(FollowUpTemplate).delete()
        
        # Reset all sender counters to 0
        # Keep senders intact, just reset their stats
        db.execute(
            update(Sender).values(
                emails_sent_today=0,
                emails_sent_this_hour=0,
                total_emails_sent=0,
            )
        )
        
        db.commit()
        
        logger.info(
            "All campaign and activity data reset",
            extra={
                "campaigns_deleted": deleted_campaigns,
                "email_logs_deleted": deleted_email_logs,
                "leads_deleted": deleted_leads,
            }
        )
        
        return {
            "status": "success",
            "message": "All campaign and activity data has been reset",
            "deleted": {
                "campaigns": deleted_campaigns,
                "email_logs": deleted_email_logs,
                "leads": deleted_leads,
                "campaign_senders": deleted_campaign_senders,
                "followup_templates": deleted_followup_templates,
            },
            "preserved": {
                "senders": "All senders kept intact",
                "templates": "All templates kept intact",
            }
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to reset data: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to reset data: {str(e)}")
