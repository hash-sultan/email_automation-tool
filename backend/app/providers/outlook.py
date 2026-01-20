"""
XenFlow Mailer - Outlook/Microsoft 365 Provider
Microsoft Graph API integration
"""

import base64
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import httpx

from app.providers.base import (
    BaseEmailProvider, EmailMessage, EmailResult, EmailResultStatus
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OutlookProvider(BaseEmailProvider):
    """
    Outlook/Microsoft 365 provider using Microsoft Graph API.
    
    Requirements:
    - Azure AD App Registration
    - Mail.Send permission
    - OAuth 2.0 credentials
    """
    
    GRAPH_API_URL = "https://graph.microsoft.com/v1.0"
    TOKEN_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
    AUTH_URL = "https://login.microsoftonline.com/common/oauth2/v2.0/authorize"
    
    SCOPES = [
        "https://graph.microsoft.com/Mail.Send",
        "https://graph.microsoft.com/Mail.Read",
        "offline_access",
        "openid",
        "profile",
        "email"
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
        
        self._client: Optional[httpx.AsyncClient] = None
    
    async def connect(self) -> bool:
        """
        Initialize Microsoft Graph API client.
        """
        try:
            # Check if token needs refresh
            if self._should_refresh_token():
                await self._refresh_access_token()
            
            # Create HTTP client with auth headers
            self._client = httpx.AsyncClient(
                base_url=self.GRAPH_API_URL,
                headers={
                    "Authorization": f"Bearer {self.access_token}",
                    "Content-Type": "application/json"
                },
                timeout=30.0
            )
            
            self._connected = True
            logger.info(f"Outlook Graph API connected for {self.sender_email}")
            return True
            
        except Exception as e:
            logger.error(f"Outlook connection failed: {str(e)}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """
        Close HTTP client.
        """
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
        logger.info("Outlook Graph API disconnected")
    
    async def verify_connection(self) -> tuple:
        """
        Verify Outlook OAuth credentials.
        """
        try:
            if not self._connected:
                success = await self.connect()
                if not success:
                    return False, "Failed to connect to Microsoft Graph API"
            
            # Try to get user profile
            response = await self._client.get("/me")
            
            if response.status_code == 200:
                profile = response.json()
                user_email = profile.get('mail') or profile.get('userPrincipalName', '')
                
                if user_email.lower() != self.sender_email.lower():
                    return False, f"Token email mismatch: expected {self.sender_email}"
                
                return True, None
            else:
                error_msg = response.json().get('error', {}).get('message', response.text)
                return False, f"Graph API error: {error_msg}"
            
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    async def send_email(self, message: EmailMessage) -> EmailResult:
        """
        Send email via Microsoft Graph API.
        """
        try:
            if not self._connected:
                success = await self.connect()
                if not success:
                    return EmailResult.failed("CONNECTION_ERROR", "Failed to connect to Graph API")
            
            # Build Graph API message payload
            payload = self._build_graph_message(message)
            
            # Send via Graph API
            response = await self._client.post(
                "/me/sendMail",
                json=payload
            )
            
            if response.status_code == 202:  # Accepted
                logger.info(
                    f"Email sent via Outlook Graph API",
                    extra={
                        "to": message.to_email,
                        "subject": message.subject[:50],
                        "message_id": message.message_id
                    }
                )
                
                return EmailResult.success(
                    message_id=message.message_id,
                    provider_message_id=message.message_id
                )
            
            elif response.status_code == 429:
                # Rate limited
                return EmailResult.rate_limited("Microsoft Graph rate limit exceeded")
            
            else:
                error_data = response.json().get('error', {})
                error_msg = error_data.get('message', response.text)
                error_code = error_data.get('code', str(response.status_code))
                
                # Check for specific errors
                if 'InvalidRecipients' in error_code or 'invalid' in error_msg.lower():
                    return EmailResult(
                        status=EmailResultStatus.BOUNCED,
                        error_code="INVALID_RECIPIENT",
                        error_message=error_msg
                    )
                
                logger.error(f"Graph API error: {error_msg}")
                return EmailResult.failed(error_code, error_msg)
            
        except Exception as e:
            logger.error(f"Outlook send error: {str(e)}")
            return EmailResult.failed("SEND_ERROR", str(e))
    
    def _build_graph_message(self, message: EmailMessage) -> Dict[str, Any]:
        """
        Build Microsoft Graph API message payload.
        """
        payload = {
            "message": {
                "subject": message.subject,
                "body": {
                    "contentType": "HTML",
                    "content": message.body_html
                },
                "toRecipients": [
                    {
                        "emailAddress": {
                            "address": message.to_email,
                            "name": message.to_name or ""
                        }
                    }
                ],
                "from": {
                    "emailAddress": {
                        "address": message.from_email or self.sender_email,
                        "name": message.from_name or self.sender_name
                    }
                },
                "replyTo": [
                    {
                        "emailAddress": {
                            "address": message.reply_to or message.from_email or self.sender_email
                        }
                    }
                ],
                "internetMessageHeaders": [
                    {"name": "X-Message-ID", "value": message.message_id},
                    {"name": "X-Mailer", "value": "XenFlow Mailer/1.0"},
                ]
            },
            "saveToSentItems": True
        }
        
        # Add threading headers
        if message.in_reply_to:
            payload["message"]["internetMessageHeaders"].append(
                {"name": "In-Reply-To", "value": message.in_reply_to}
            )
        if message.references:
            payload["message"]["internetMessageHeaders"].append(
                {"name": "References", "value": message.references}
            )
        
        # Add List-Unsubscribe
        domain = (message.from_email or self.sender_email).split('@')[1]
        payload["message"]["internetMessageHeaders"].append(
            {"name": "List-Unsubscribe", "value": f"<mailto:unsubscribe@{domain}>"}
        )
        
        return payload
    
    def _should_refresh_token(self) -> bool:
        """Check if token should be refreshed."""
        if not self.token_expiry:
            return True
        if isinstance(self.token_expiry, str):
            self.token_expiry = datetime.fromisoformat(self.token_expiry)
        return datetime.utcnow() >= self.token_expiry - timedelta(minutes=5)
    
    async def _refresh_access_token(self) -> None:
        """
        Refresh the OAuth access token.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.TOKEN_URL,
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                    "scope": " ".join(self.SCOPES)
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.access_token = data["access_token"]
                self.refresh_token = data.get("refresh_token", self.refresh_token)
                
                # Calculate expiry
                expires_in = data.get("expires_in", 3600)
                self.token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)
                
                logger.info("Outlook OAuth token refreshed")
            else:
                raise Exception(f"Token refresh failed: {response.text}")
    
    def get_updated_tokens(self) -> Dict[str, Any]:
        """
        Get updated OAuth tokens (after refresh).
        """
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expiry": self.token_expiry.isoformat() if self.token_expiry else None
        }
    
    @staticmethod
    def get_authorization_url(client_id: str, redirect_uri: str, state: str = None) -> str:
        """
        Generate OAuth authorization URL for user consent.
        """
        import urllib.parse
        
        params = {
            "client_id": client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "response_mode": "query",
            "scope": " ".join(OutlookProvider.SCOPES),
            "state": state or ""
        }
        
        return f"{OutlookProvider.AUTH_URL}?{urllib.parse.urlencode(params)}"
    
    @staticmethod
    async def exchange_code_for_tokens(
        code: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for OAuth tokens.
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OutlookProvider.TOKEN_URL,
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                expires_in = data.get("expires_in", 3600)
                
                return {
                    "access_token": data["access_token"],
                    "refresh_token": data.get("refresh_token"),
                    "expiry": (datetime.utcnow() + timedelta(seconds=expires_in)).isoformat(),
                    "scope": data.get("scope", "")
                }
            else:
                raise Exception(f"Token exchange failed: {response.text}")

