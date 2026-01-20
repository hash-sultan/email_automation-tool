"""
XenFlow Mailer - Gmail Provider
Gmail OAuth 2.0 integration with Gmail API
"""

import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.providers.base import (
    BaseEmailProvider, EmailMessage, EmailResult, EmailResultStatus
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class GmailProvider(BaseEmailProvider):
    """
    Gmail provider using OAuth 2.0 and Gmail API.
    
    Benefits over SMTP:
    - Better deliverability (native Gmail)
    - OAuth tokens (more secure than passwords)
    - Access to Gmail features (labels, threads)
    
    Requirements:
    - Google Cloud Console project
    - OAuth 2.0 credentials
    - Gmail API enabled
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.readonly',  # For reply detection
    ]
    
    def __init__(
        self,
        sender_email: str,
        sender_name: str = None,
        access_token: str = None,
        refresh_token: str = None,
        client_id: str = None,
        client_secret: str = None,
        token_expiry: datetime = None
    ):
        super().__init__(sender_email, sender_name)
        
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_expiry = token_expiry
        
        self._credentials: Optional[Credentials] = None
        self._service = None
    
    async def connect(self) -> bool:
        """
        Initialize Gmail API service with OAuth credentials.
        """
        try:
            # Build credentials
            self._credentials = Credentials(
                token=self.access_token,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.SCOPES
            )
            
            # Refresh if expired
            if self._credentials.expired and self._credentials.refresh_token:
                self._credentials.refresh(Request())
                # Update stored tokens
                self.access_token = self._credentials.token
                self.token_expiry = self._credentials.expiry
            
            # Build Gmail service
            self._service = build('gmail', 'v1', credentials=self._credentials)
            
            self._connected = True
            logger.info(f"Gmail API connected for {self.sender_email}")
            return True
            
        except Exception as e:
            logger.error(f"Gmail connection failed: {str(e)}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """
        Close Gmail API service.
        """
        self._service = None
        self._credentials = None
        self._connected = False
        logger.info("Gmail API disconnected")
    
    async def verify_connection(self) -> tuple:
        """
        Verify Gmail OAuth credentials.
        """
        try:
            if not self._connected:
                success = await self.connect()
                if not success:
                    return False, "Failed to connect to Gmail API"
            
            # Try to get profile to verify credentials
            profile = self._service.users().getProfile(userId='me').execute()
            
            if profile.get('emailAddress', '').lower() != self.sender_email.lower():
                return False, f"Token email mismatch: expected {self.sender_email}"
            
            return True, None
            
        except HttpError as e:
            error_content = json.loads(e.content.decode())
            error_msg = error_content.get('error', {}).get('message', str(e))
            return False, f"Gmail API error: {error_msg}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    async def send_email(self, message: EmailMessage) -> EmailResult:
        """
        Send email via Gmail API.
        """
        try:
            if not self._connected:
                success = await self.connect()
                if not success:
                    return EmailResult.failed("CONNECTION_ERROR", "Failed to connect to Gmail API")
            
            # Build MIME message
            mime_message = self._build_mime_message(message)
            
            # Encode for Gmail API
            raw_message = base64.urlsafe_b64encode(
                mime_message.as_bytes()
            ).decode('utf-8')
            
            # Send via Gmail API
            body = {'raw': raw_message}
            
            # If replying to a thread, include threadId
            if message.in_reply_to:
                # Try to find thread ID from in_reply_to message
                # This would require storing thread IDs with email logs
                pass
            
            sent_message = self._service.users().messages().send(
                userId='me',
                body=body
            ).execute()
            
            gmail_message_id = sent_message.get('id')
            
            logger.info(
                f"Email sent via Gmail API",
                extra={
                    "to": message.to_email,
                    "subject": message.subject[:50],
                    "message_id": message.message_id,
                    "gmail_id": gmail_message_id
                }
            )
            
            return EmailResult.success(
                message_id=message.message_id,
                provider_message_id=gmail_message_id
            )
            
        except HttpError as e:
            error_content = json.loads(e.content.decode()) if e.content else {}
            error_msg = error_content.get('error', {}).get('message', str(e))
            error_code = str(e.resp.status)
            
            # Check for specific error types
            if e.resp.status == 400:
                # Bad request - possibly invalid recipient
                if 'Invalid To header' in error_msg or 'invalid' in error_msg.lower():
                    return EmailResult(
                        status=EmailResultStatus.BOUNCED,
                        error_code="INVALID_RECIPIENT",
                        error_message=error_msg
                    )
            elif e.resp.status == 429:
                # Rate limited
                return EmailResult.rate_limited(error_msg)
            
            logger.error(f"Gmail API error: {error_msg}")
            return EmailResult.failed(error_code, error_msg)
            
        except Exception as e:
            logger.error(f"Gmail send error: {str(e)}")
            return EmailResult.failed("SEND_ERROR", str(e))
    
    def _build_mime_message(self, message: EmailMessage) -> MIMEMultipart:
        """
        Build MIME message for Gmail API.
        """
        mime_msg = MIMEMultipart("alternative")
        
        # Headers
        mime_msg["From"] = formataddr((
            message.from_name or self.sender_name,
            message.from_email or self.sender_email
        ))
        mime_msg["To"] = formataddr((message.to_name or "", message.to_email))
        mime_msg["Subject"] = message.subject
        mime_msg["Reply-To"] = message.reply_to or message.from_email or self.sender_email
        mime_msg["Message-ID"] = message.message_id
        mime_msg["Date"] = formatdate(localtime=True)
        
        # Threading headers
        if message.in_reply_to:
            mime_msg["In-Reply-To"] = message.in_reply_to
        if message.references:
            mime_msg["References"] = message.references
        
        # List-Unsubscribe
        domain = (message.from_email or self.sender_email).split('@')[1]
        mime_msg["List-Unsubscribe"] = f"<mailto:unsubscribe@{domain}>"
        
        # Custom headers
        for key, value in message.custom_headers.items():
            mime_msg[key] = value
        
        # Content
        if message.body_plain:
            mime_msg.attach(MIMEText(message.body_plain, "plain", "utf-8"))
        mime_msg.attach(MIMEText(message.body_html, "html", "utf-8"))
        
        return mime_msg
    
    def get_updated_tokens(self) -> Dict[str, Any]:
        """
        Get updated OAuth tokens (after refresh).
        """
        if self._credentials:
            return {
                "access_token": self._credentials.token,
                "refresh_token": self._credentials.refresh_token,
                "expiry": self._credentials.expiry.isoformat() if self._credentials.expiry else None
            }
        return {}
    
    @staticmethod
    def get_authorization_url(client_id: str, redirect_uri: str, state: str = None) -> str:
        """
        Generate OAuth authorization URL for user consent.
        """
        from google_auth_oauthlib.flow import Flow
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": "",  # Not needed for auth URL
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=GmailProvider.SCOPES
        )
        flow.redirect_uri = redirect_uri
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=state
        )
        
        return auth_url
    
    @staticmethod
    def exchange_code_for_tokens(
        code: str, 
        client_id: str, 
        client_secret: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for OAuth tokens.
        """
        from google_auth_oauthlib.flow import Flow
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=GmailProvider.SCOPES
        )
        flow.redirect_uri = redirect_uri
        
        flow.fetch_token(code=code)
        credentials = flow.credentials
        
        return {
            "access_token": credentials.token,
            "refresh_token": credentials.refresh_token,
            "expiry": credentials.expiry.isoformat() if credentials.expiry else None,
            "scopes": list(credentials.scopes)
        }

