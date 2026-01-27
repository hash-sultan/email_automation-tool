"""
XenFlow Mailer - Leads API
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.database import get_db
from app.models import Lead
from app.models.lead import LeadStatus
from app.schemas.lead import (
    LeadCreate, LeadUpdate, LeadResponse, LeadListResponse,
    LeadImportCSV, LeadBulkUpdate
)
from app.services.suppression import SuppressionService
from app.utils.csv_importer import CSVImporter
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=LeadListResponse)
def list_leads(
    campaign_id: Optional[int] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List leads with filtering and pagination."""
    query = db.query(Lead)
    
    if campaign_id:
        query = query.filter(Lead.campaign_id == campaign_id)
    
    if status:
        query = query.filter(Lead.status == status)
    
    if search:
        query = query.filter(
            or_(
                Lead.email.ilike(f"%{search}%"),
                Lead.name.ilike(f"%{search}%"),
                Lead.company.ilike(f"%{search}%")
            )
        )
    
    total = query.count()
    
    leads = query.order_by(Lead.created_at.desc()).offset(
        (page - 1) * page_size
    ).limit(page_size).all()
    
    return LeadListResponse(
        items=[LeadResponse.model_validate(lead) for lead in leads],
        total=total,
        page=page,
        page_size=page_size,
        pages=(total + page_size - 1) // page_size
    )


@router.get("/stats")
def get_lead_stats(
    campaign_id: Optional[int] = Query(None, description="Filter by campaign ID"),
    db: Session = Depends(get_db)
):
    """Get lead statistics."""
    query = db.query(Lead)
    
    if campaign_id:
        query = query.filter(Lead.campaign_id == campaign_id)
    
    total = query.count()
    
    # Count by status
    stats = {
        "total": total,
        "new": query.filter(Lead.status == LeadStatus.NEW).count(),
        "queued": query.filter(Lead.status == LeadStatus.QUEUED).count(),
        "contacted": query.filter(Lead.status == LeadStatus.CONTACTED).count(),
        "replied": query.filter(Lead.status == LeadStatus.REPLIED).count(),
        "bounced": query.filter(Lead.status == LeadStatus.BOUNCED).count(),
        "unsubscribed": query.filter(Lead.status == LeadStatus.UNSUBSCRIBED).count(),
        "converted": query.filter(Lead.status == LeadStatus.CONVERTED).count(),
    }
    
    return stats


@router.get("/{lead_id}", response_model=LeadResponse)
def get_lead(lead_id: int, db: Session = Depends(get_db)):
    """Get a specific lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return LeadResponse.model_validate(lead)


@router.post("/", response_model=LeadResponse)
def create_lead(lead_data: LeadCreate, db: Session = Depends(get_db)):
    """Create a new lead."""
    # Check suppression
    suppression_service = SuppressionService(db)
    if suppression_service.is_suppressed(lead_data.email):
        raise HTTPException(status_code=400, detail="Email is in suppression list")
    
    # Check for duplicate
    existing = db.query(Lead).filter(
        Lead.email == lead_data.email.lower(),
        Lead.campaign_id == lead_data.campaign_id
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Lead already exists in this campaign")
    
    # Build lead data, ensuring email is normalized and not passed twice
    lead_data_dict = lead_data.model_dump()
    lead_data_dict["email"] = lead_data.email.lower()
    
    lead = Lead(**lead_data_dict)
    
    db.add(lead)
    db.flush()  # Flush to get the lead ID, but don't commit yet
    
    # Update campaign's total_leads count if campaign_id is provided
    if lead_data.campaign_id:
        from app.models import Campaign
        campaign = db.query(Campaign).filter(Campaign.id == lead_data.campaign_id).first()
        if campaign:
            # Count all leads for this campaign (including the one we just added)
            campaign.total_leads = db.query(Lead).filter(Lead.campaign_id == lead_data.campaign_id).count()
    
    db.commit()
    db.refresh(lead)
    
    return LeadResponse.model_validate(lead)


@router.put("/{lead_id}", response_model=LeadResponse)
def update_lead(lead_id: int, lead_data: LeadUpdate, db: Session = Depends(get_db)):
    """Update a lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    update_data = lead_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(lead, key, value)
    
    db.commit()
    db.refresh(lead)
    
    return LeadResponse.model_validate(lead)


@router.delete("/{lead_id}")
def delete_lead(lead_id: int, db: Session = Depends(get_db)):
    """Delete a lead."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    campaign_id = lead.campaign_id
    
    db.delete(lead)
    
    # Update campaign's total_leads count if campaign_id exists
    if campaign_id:
        from app.models import Campaign
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if campaign:
            campaign.total_leads = db.query(Lead).filter(Lead.campaign_id == campaign_id).count() - 1
    
    db.commit()
    
    return {"status": "deleted", "lead_id": lead_id}


@router.post("/import")
async def import_leads(
    file: UploadFile = File(...),
    campaign_id: Optional[int] = Form(None),
    skip_duplicates: bool = Form(True),
    db: Session = Depends(get_db)
):
    """Import leads from CSV file."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV")
    
    content = await file.read()
    csv_content = content.decode('utf-8-sig')
    
    importer = CSVImporter(db)
    result = importer.import_from_string(
        csv_content=csv_content,
        campaign_id=campaign_id,
        skip_duplicates=skip_duplicates
    )
    
    return result


@router.post("/import/preview")
async def preview_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Preview CSV import without importing."""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be CSV")
    
    content = await file.read()
    csv_content = content.decode('utf-8-sig')
    
    importer = CSVImporter(db)
    preview = importer.preview(csv_content)
    
    return preview


@router.post("/bulk-update")
def bulk_update_leads(data: LeadBulkUpdate, db: Session = Depends(get_db)):
    """Bulk update leads."""
    leads = db.query(Lead).filter(Lead.id.in_(data.lead_ids)).all()
    
    if not leads:
        raise HTTPException(status_code=404, detail="No leads found")
    
    updated = 0
    for lead in leads:
        if data.status:
            lead.status = data.status
        if data.campaign_id is not None:
            lead.campaign_id = data.campaign_id
        if data.tags_add:
            current_tags = lead.tags or []
            lead.tags = list(set(current_tags + data.tags_add))
        if data.tags_remove:
            current_tags = lead.tags or []
            lead.tags = [t for t in current_tags if t not in data.tags_remove]
        updated += 1
    
    db.commit()
    
    return {"status": "updated", "count": updated}


@router.post("/{lead_id}/mark-replied")
def mark_lead_replied(lead_id: int, db: Session = Depends(get_db)):
    """Manually mark a lead as replied."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.mark_replied()
    db.commit()
    
    return {"status": "marked_replied", "lead_id": lead_id}


@router.post("/{lead_id}/mark-unsubscribed")
def mark_lead_unsubscribed(lead_id: int, db: Session = Depends(get_db)):
    """Manually mark a lead as unsubscribed."""
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    
    lead.mark_unsubscribed()
    db.commit()
    
    return {"status": "marked_unsubscribed", "lead_id": lead_id}
