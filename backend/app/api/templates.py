"""
XenFlow Mailer - Templates API
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import re

from app.database import get_db
from app.models import Template, FollowUpTemplate, Campaign
from app.schemas.template import (
    TemplateCreate, TemplateUpdate, TemplateResponse,
    FollowUpTemplateCreate, FollowUpTemplateUpdate, FollowUpTemplateResponse
)
from app.utils.template_renderer import get_renderer
from app.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/", response_model=List[TemplateResponse])
def list_templates(
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all templates."""
    query = db.query(Template)
    
    if is_active is not None:
        query = query.filter(Template.is_active == is_active)
    
    if search:
        query = query.filter(
            Template.name.ilike(f"%{search}%") |
            Template.subject.ilike(f"%{search}%")
        )
    
    templates = query.order_by(Template.created_at.desc()).all()
    return [TemplateResponse.model_validate(t) for t in templates]


@router.get("/{template_id}", response_model=TemplateResponse)
def get_template(template_id: int, db: Session = Depends(get_db)):
    """Get a specific template."""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return TemplateResponse.model_validate(template)


@router.post("/", response_model=TemplateResponse)
def create_template(template_data: TemplateCreate, db: Session = Depends(get_db)):
    """Create a new template."""
    # Normalize category name: use title case (first letter uppercase, rest lowercase)
    # But first check if a category with this name (case-insensitive) already exists
    # If so, use the existing category's exact case to prevent duplicates
    existing_template = db.query(Template).filter(
        Template.category.ilike(template_data.category)
    ).first()
    
    normalized_category = existing_template.category if existing_template else template_data.category.title()
    
    # Extract placeholders
    renderer = get_renderer()
    placeholders = list(renderer.extract_placeholders(
        template_data.subject + " " + template_data.body_html
    ))
    
    template_data_dict = template_data.model_dump()
    template_data_dict['category'] = normalized_category
    
    # Ensure template_type is set correctly (default to "initial" if not provided)
    if 'template_type' not in template_data_dict or not template_data_dict['template_type']:
        template_data_dict['template_type'] = 'initial'
    elif template_data_dict['template_type'] not in ['initial', 'followup']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid template_type: {template_data_dict['template_type']}. Must be 'initial' or 'followup'"
        )
    
    template = Template(
        **template_data_dict,
        placeholders_used=placeholders
    )
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return TemplateResponse.model_validate(template)


@router.put("/{template_id}", response_model=TemplateResponse)
def update_template(
    template_id: int,
    template_data: TemplateUpdate,
    db: Session = Depends(get_db)
):
    """Update a template."""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    update_data = template_data.model_dump(exclude_unset=True)
    
    # Normalize category name if it's being updated
    if 'category' in update_data:
        existing_template = db.query(Template).filter(
            Template.category.ilike(update_data['category'])
        ).first()
        
        normalized_category = existing_template.category if existing_template else update_data['category'].title()
        update_data['category'] = normalized_category
    
    # Re-extract placeholders if content changed
    if 'subject' in update_data or 'body_html' in update_data:
        renderer = get_renderer()
        content = (update_data.get('subject', template.subject) + " " +
                  update_data.get('body_html', template.body_html))
        update_data['placeholders_used'] = list(renderer.extract_placeholders(content))
    
    for key, value in update_data.items():
        setattr(template, key, value)
    
    db.commit()
    db.refresh(template)
    
    return TemplateResponse.model_validate(template)


@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    """Delete a template."""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    # Check if used by any campaigns
    campaigns_using = db.query(Campaign).filter(
        Campaign.template_id == template_id
    ).count()
    
    if campaigns_using > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Template is used by {campaigns_using} campaign(s)"
        )
    
    db.delete(template)
    db.commit()
    
    return {"status": "deleted", "template_id": template_id}


@router.delete("/category/{category_name}")
def delete_category(category_name: str, db: Session = Depends(get_db)):
    """Delete all templates in a category."""
    # Find all templates in this category
    templates = db.query(Template).filter(Template.category == category_name).all()
    
    if not templates:
        raise HTTPException(status_code=404, detail="Category not found")
    
    template_ids = [t.id for t in templates]
    
    # Check if any templates in this category are used by campaigns
    campaigns_using = db.query(Campaign).filter(
        Campaign.template_id.in_(template_ids)
    ).count()
    
    if campaigns_using > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Category is used by {campaigns_using} campaign(s). Please remove templates from campaigns first."
        )
    
    # Delete all templates in the category
    deleted_count = db.query(Template).filter(Template.category == category_name).delete()
    db.commit()
    
    return {
        "status": "deleted",
        "category": category_name,
        "templates_deleted": deleted_count
    }


@router.post("/{template_id}/preview")
def preview_template(
    template_id: int,
    sample_data: dict = None,
    db: Session = Depends(get_db)
):
    """Preview a rendered template."""
    template = db.query(Template).filter(Template.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    
    renderer = get_renderer()
    
    default_data = {
        "name": "John",
        "first_name": "John",
        "last_name": "Doe",
        "company": "Acme Inc",
        "industry": "Technology",
        "title": "CEO",
        "email": "john@example.com",
    }
    
    if sample_data:
        default_data.update(sample_data)
    
    return {
        "subject": renderer.render(template.subject, default_data),
        "body_html": renderer.render(template.body_html, default_data),
        "body_plain": renderer.render(template.body_plain or "", default_data),
        "placeholders_used": template.placeholders_used
    }


@router.post("/validate")
def validate_template(content: dict):
    """Validate template syntax."""
    renderer = get_renderer()
    
    subject = content.get("subject", "")
    body = content.get("body_html", "")
    
    subject_validation = renderer.validate_template(subject)
    body_validation = renderer.validate_template(body)
    
    all_valid = subject_validation["valid"] and body_validation["valid"]
    all_placeholders = list(set(
        subject_validation["placeholders"] + body_validation["placeholders"]
    ))
    
    return {
        "valid": all_valid,
        "placeholders": all_placeholders,
        "subject_error": subject_validation.get("error"),
        "body_error": body_validation.get("error")
    }


# Follow-up Templates

@router.get("/followups/{campaign_id}", response_model=List[FollowUpTemplateResponse])
def list_followup_templates(campaign_id: int, db: Session = Depends(get_db)):
    """List follow-up templates for a campaign."""
    templates = db.query(FollowUpTemplate).filter(
        FollowUpTemplate.campaign_id == campaign_id
    ).order_by(FollowUpTemplate.step).all()
    
    return [FollowUpTemplateResponse.model_validate(t) for t in templates]


@router.post("/followups", response_model=FollowUpTemplateResponse)
def create_followup_template(
    template_data: FollowUpTemplateCreate,
    db: Session = Depends(get_db)
):
    """Create a follow-up template."""
    # Check campaign exists
    campaign = db.query(Campaign).filter(
        Campaign.id == template_data.campaign_id
    ).first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    
    # Check step doesn't already exist
    existing = db.query(FollowUpTemplate).filter(
        FollowUpTemplate.campaign_id == template_data.campaign_id,
        FollowUpTemplate.step == template_data.step
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Follow-up step {template_data.step} already exists"
        )
    
    template = FollowUpTemplate(**template_data.model_dump())
    
    db.add(template)
    db.commit()
    db.refresh(template)
    
    return FollowUpTemplateResponse.model_validate(template)


@router.put("/followups/{followup_id}", response_model=FollowUpTemplateResponse)
def update_followup_template(
    followup_id: int,
    template_data: FollowUpTemplateUpdate,
    db: Session = Depends(get_db)
):
    """Update a follow-up template."""
    template = db.query(FollowUpTemplate).filter(
        FollowUpTemplate.id == followup_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Follow-up template not found")
    
    update_data = template_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(template, key, value)
    
    db.commit()
    db.refresh(template)
    
    return FollowUpTemplateResponse.model_validate(template)


@router.delete("/followups/{followup_id}")
def delete_followup_template(followup_id: int, db: Session = Depends(get_db)):
    """Delete a follow-up template."""
    template = db.query(FollowUpTemplate).filter(
        FollowUpTemplate.id == followup_id
    ).first()
    if not template:
        raise HTTPException(status_code=404, detail="Follow-up template not found")
    
    db.delete(template)
    db.commit()
    
    return {"status": "deleted", "followup_id": followup_id}

