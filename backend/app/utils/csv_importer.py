"""
XenFlow Mailer - CSV Lead Importer
Import leads from CSV files with validation
"""

import csv
import io
from typing import Dict, Any, List, Optional, Tuple
from email_validator import validate_email, EmailNotValidError
from sqlalchemy.orm import Session

from app.models import Lead, Suppression
from app.models.lead import LeadStatus
from app.services.suppression import SuppressionService
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CSVImporter:
    """
    CSV lead importer with validation and duplicate handling.
    
    Features:
    - Flexible column mapping
    - Email validation
    - Duplicate detection (within file and database)
    - Suppression list checking
    - Custom field support
    """
    
    # Standard column aliases
    COLUMN_ALIASES = {
        'email': ['email', 'email_address', 'e-mail', 'mail', 'email address'],
        'name': ['name', 'full_name', 'fullname', 'full name', 'contact'],
        'first_name': ['first_name', 'firstname', 'first', 'given_name', 'first name'],
        'last_name': ['last_name', 'lastname', 'last', 'surname', 'family_name', 'last name'],
        'company': ['company', 'company_name', 'organization', 'org', 'company name'],
        'industry': ['industry', 'sector', 'vertical'],
        'title': ['title', 'job_title', 'position', 'role', 'job title'],
        'phone': ['phone', 'phone_number', 'telephone', 'mobile', 'phone number'],
    }
    
    def __init__(self, db: Session):
        self.db = db
        self.suppression_service = SuppressionService(db)
    
    def import_from_string(
        self,
        csv_content: str,
        campaign_id: int = None,
        column_mapping: Dict[str, str] = None,
        skip_duplicates: bool = True,
        check_suppression: bool = True,
        source: str = "csv_import"
    ) -> Dict[str, Any]:
        """
        Import leads from CSV string.
        
        Returns:
            {
                "success": int,
                "failed": int,
                "duplicates": int,
                "suppressed": int,
                "errors": List[Dict]
            }
        """
        return self._import(
            csv.DictReader(io.StringIO(csv_content)),
            campaign_id=campaign_id,
            column_mapping=column_mapping,
            skip_duplicates=skip_duplicates,
            check_suppression=check_suppression,
            source=source
        )
    
    def import_from_file(
        self,
        file_path: str,
        campaign_id: int = None,
        column_mapping: Dict[str, str] = None,
        skip_duplicates: bool = True,
        check_suppression: bool = True,
        source: str = "csv_import"
    ) -> Dict[str, Any]:
        """
        Import leads from CSV file.
        """
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            return self._import(
                csv.DictReader(f),
                campaign_id=campaign_id,
                column_mapping=column_mapping,
                skip_duplicates=skip_duplicates,
                check_suppression=check_suppression,
                source=source
            )
    
    def _import(
        self,
        reader: csv.DictReader,
        campaign_id: int = None,
        column_mapping: Dict[str, str] = None,
        skip_duplicates: bool = True,
        check_suppression: bool = True,
        source: str = "csv_import"
    ) -> Dict[str, Any]:
        """
        Internal import method.
        """
        result = {
            "success": 0,
            "failed": 0,
            "duplicates": 0,
            "suppressed": 0,
            "errors": []
        }
        
        # Build column mapping
        mapping = self._build_column_mapping(reader.fieldnames, column_mapping)
        
        if 'email' not in mapping:
            result["errors"].append({
                "row": 0,
                "error": "No email column found in CSV"
            })
            return result
        
        # Track emails in this import batch
        seen_emails = set()
        
        for row_num, row in enumerate(reader, start=2):  # Start at 2 (1 is header)
            try:
                lead_data = self._process_row(row, mapping, row_num)
                
                if not lead_data:
                    result["failed"] += 1
                    continue
                
                email = lead_data['email'].lower()
                
                # Check for duplicate in batch
                if email in seen_emails:
                    if skip_duplicates:
                        result["duplicates"] += 1
                        continue
                
                seen_emails.add(email)
                
                # Check for duplicate in database
                if skip_duplicates:
                    existing = self.db.query(Lead).filter(
                        Lead.email == email,
                        Lead.campaign_id == campaign_id
                    ).first()
                    
                    if existing:
                        result["duplicates"] += 1
                        continue
                
                # Check suppression list
                if check_suppression:
                    if self.suppression_service.is_suppressed(email):
                        result["suppressed"] += 1
                        continue
                
                # Create lead
                lead = Lead(
                    email=email,
                    name=lead_data.get('name'),
                    first_name=lead_data.get('first_name'),
                    last_name=lead_data.get('last_name'),
                    company=lead_data.get('company'),
                    industry=lead_data.get('industry'),
                    title=lead_data.get('title'),
                    phone=lead_data.get('phone'),
                    campaign_id=campaign_id,
                    status=LeadStatus.NEW,
                    source=source,
                    custom_fields=lead_data.get('custom_fields', {})
                )
                
                self.db.add(lead)
                result["success"] += 1
                
            except Exception as e:
                result["failed"] += 1
                result["errors"].append({
                    "row": row_num,
                    "error": str(e)
                })
        
        # Commit all leads
        try:
            self.db.commit()
            
            # Update campaign's total_leads count if campaign_id was provided
            if campaign_id and result["success"] > 0:
                from app.models import Campaign
                campaign = self.db.query(Campaign).filter(Campaign.id == campaign_id).first()
                if campaign:
                    campaign.total_leads = self.db.query(Lead).filter(Lead.campaign_id == campaign_id).count()
                    self.db.commit()
                    
        except Exception as e:
            self.db.rollback()
            result["success"] = 0
            result["errors"].append({
                "row": 0,
                "error": f"Database error: {str(e)}"
            })
        
        logger.info(
            f"CSV import complete",
            extra={
                "success": result["success"],
                "failed": result["failed"],
                "duplicates": result["duplicates"],
                "suppressed": result["suppressed"],
                "campaign_id": campaign_id
            }
        )
        
        return result
    
    def _build_column_mapping(
        self,
        headers: List[str],
        custom_mapping: Dict[str, str] = None
    ) -> Dict[str, str]:
        """
        Build column mapping from CSV headers.
        """
        mapping = {}
        headers_lower = {h.lower().strip(): h for h in headers if h}
        
        # Apply custom mapping first
        if custom_mapping:
            for field, column in custom_mapping.items():
                if column.lower() in headers_lower:
                    mapping[field] = headers_lower[column.lower()]
        
        # Auto-detect remaining fields
        for field, aliases in self.COLUMN_ALIASES.items():
            if field not in mapping:
                for alias in aliases:
                    if alias.lower() in headers_lower:
                        mapping[field] = headers_lower[alias.lower()]
                        break
        
        # Store unmapped columns for custom fields
        mapped_columns = set(mapping.values())
        mapping['_custom_columns'] = [
            h for h in headers 
            if h and h not in mapped_columns
        ]
        
        return mapping
    
    def _process_row(
        self,
        row: Dict[str, str],
        mapping: Dict[str, str],
        row_num: int
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single CSV row.
        """
        # Get email
        email_column = mapping.get('email')
        if not email_column:
            return None
        
        email = row.get(email_column, '').strip()
        if not email:
            return None
        
        # Validate email
        try:
            valid = validate_email(email, check_deliverability=False)
            email = valid.email
        except EmailNotValidError as e:
            logger.debug(f"Invalid email at row {row_num}: {email} - {str(e)}")
            return None
        
        # Build lead data
        data = {'email': email}
        
        for field in ['name', 'first_name', 'last_name', 'company', 'industry', 'title', 'phone']:
            column = mapping.get(field)
            if column and row.get(column):
                data[field] = row[column].strip()
        
        # Handle name splitting
        if not data.get('first_name') and data.get('name'):
            parts = data['name'].split(' ', 1)
            data['first_name'] = parts[0]
            if len(parts) > 1:
                data['last_name'] = parts[1]
        
        # Process custom fields
        custom_fields = {}
        for column in mapping.get('_custom_columns', []):
            if row.get(column):
                # Convert column name to snake_case
                key = column.lower().replace(' ', '_').replace('-', '_')
                custom_fields[key] = row[column].strip()
        
        if custom_fields:
            data['custom_fields'] = custom_fields
        
        return data
    
    def preview(
        self,
        csv_content: str,
        column_mapping: Dict[str, str] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Preview CSV import without actually importing.
        """
        reader = csv.DictReader(io.StringIO(csv_content))
        
        headers = reader.fieldnames or []
        mapping = self._build_column_mapping(headers, column_mapping)
        
        preview_rows = []
        for i, row in enumerate(reader):
            if i >= limit:
                break
            
            lead_data = self._process_row(row, mapping, i + 2)
            if lead_data:
                preview_rows.append(lead_data)
        
        return {
            "headers": headers,
            "detected_mapping": {k: v for k, v in mapping.items() if not k.startswith('_')},
            "custom_columns": mapping.get('_custom_columns', []),
            "preview_rows": preview_rows,
            "total_rows": sum(1 for _ in csv.DictReader(io.StringIO(csv_content)))
        }

