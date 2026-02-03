"""
XenFlow Mailer - Generic SMTP Provider
Supports any SMTP server (SendGrid, Mailgun, custom, etc.)
"""

import asyncio
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate
from typing import Optional
import aiosmtplib
from tenacity import retry, stop_after_attempt, wait_exponential

from app.providers.base import (
    BaseEmailProvider, EmailMessage, EmailResult, EmailResultStatus
)
from app.utils.logger import get_logger

logger = get_logger(__name__)


class SMTPProvider(BaseEmailProvider):
    """
    Generic SMTP email provider.
    
    Supports:
    - TLS encryption
    - Authentication
    - Connection pooling (via keep-alive)
    - Retry logic with exponential backoff
    """
    
    def __init__(
        self,
        sender_email: str,
        sender_name: str = None,
        smtp_host: str = None,
        smtp_port: int = 587,
        smtp_username: str = None,
        smtp_password: str = None,
        use_tls: bool = True,
        timeout: int = 30
    ):
        super().__init__(sender_email, sender_name)
        
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username or sender_email
        self.smtp_password = smtp_password
        self.use_tls = use_tls
        self.timeout = timeout
        
        self._client: Optional[aiosmtplib.SMTP] = None
    
    async def connect(self) -> bool:
        """
        Establish SMTP connection.
        """
        try:
            # Create SSL context for secure connection (when TLS is enabled)
            ssl_context = ssl.create_default_context() if self.use_tls else None

            # TLS strategy:
            # - Port 465: implicit TLS (use_tls=True, no STARTTLS)
            # - Other ports (e.g. 587): connect plain, then upgrade with STARTTLS
            if self.use_tls and self.smtp_port == 465:
                use_tls = True
            else:
                # For STARTTLS and non‑TLS connections, start without TLS
                use_tls = False
            
            self._client = aiosmtplib.SMTP(
                hostname=self.smtp_host,
                port=self.smtp_port,
                timeout=self.timeout,
                use_tls=use_tls,
            )
            
            await self._client.connect()
            
            # For STARTTLS (e.g. 587): upgrade connection after connect
            if self.use_tls and self.smtp_port != 465:
                try:
                    await self._client.starttls(tls_context=ssl_context)
                except Exception as e:
                    # Some servers are already in TLS mode and will reject STARTTLS
                    if "Connection already using TLS" in str(e):
                        logger.warning(
                            "STARTTLS skipped: connection already using TLS",
                        )
                    else:
                        raise
            
            # Authenticate
            if self.smtp_username and self.smtp_password:
                await self._client.login(self.smtp_username, self.smtp_password)
            
            self._connected = True
            logger.info(f"SMTP connected: {self.smtp_host}:{self.smtp_port}")
            return True
            
        except Exception as e:
            logger.error(f"SMTP connection failed: {str(e)}")
            self._connected = False
            return False
    
    async def disconnect(self) -> None:
        """
        Close SMTP connection.
        """
        if self._client:
            try:
                await self._client.quit()
            except Exception:
                pass
            finally:
                self._client = None
                self._connected = False
                logger.info("SMTP disconnected")
    
    async def verify_connection(self) -> tuple:
        """
        Verify SMTP credentials and connection.
        """
        try:
            if not self._connected:
                success = await self.connect()
                if not success:
                    return False, "Failed to connect to SMTP server"
            
            # Send NOOP to verify connection is alive
            await self._client.noop()
            return True, None
            
        except aiosmtplib.SMTPAuthenticationError as e:
            return False, f"Authentication failed: {str(e)}"
        except aiosmtplib.SMTPConnectError as e:
            return False, f"Connection failed: {str(e)}"
        except Exception as e:
            return False, f"Error: {str(e)}"
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def send_email(self, message: EmailMessage) -> EmailResult:
        """
        Send email via SMTP with retry logic.
        """
        try:
            # Ensure connected
            if not self._connected:
                success = await self.connect()
                if not success:
                    return EmailResult.failed("CONNECTION_ERROR", "Failed to connect to SMTP")
            
            # Build MIME message
            mime_message = self._build_mime_message(message)
            
            # Send
            response = await self._client.send_message(mime_message)
            
            logger.info(
                f"Email sent via SMTP",
                extra={
                    "to": message.to_email,
                    "subject": message.subject[:50],
                    "message_id": message.message_id,
                    "response": str(response)
                }
            )
            
            return EmailResult.success(
                message_id=message.message_id,
                provider_message_id=message.message_id
            )
            
        except aiosmtplib.SMTPRecipientsRefused as e:
            # Invalid recipient - likely a bounce
            error_msg = str(e)
            logger.warning(f"Recipient refused: {message.to_email} - {error_msg}")
            return EmailResult(
                status=EmailResultStatus.BOUNCED,
                error_code="RECIPIENT_REFUSED",
                error_message=error_msg
            )
            
        except aiosmtplib.SMTPDataError as e:
            # Server rejected the message
            error_msg = str(e)
            error_code = getattr(e, 'code', None) or getattr(e, 'smtp_code', None)
            logger.error(f"SMTP data error: {error_msg}")
            
            # Check for "address not found" or "message blocked" errors - these are bounces, not Gmail limits
            error_str_lower = error_msg.lower()
            if any(keyword in error_str_lower for keyword in [
                'address not found', 'message blocked', 'user not found', 
                'mailbox not found', 'no such user', 'invalid recipient',
                'recipient address rejected', '550 5.1.1', '550 5.4.1'
            ]):
                # These are bounces, not rate limits
                logger.warning(f"Recipient error (bounce): {message.to_email} - {error_msg}")
                return EmailResult(
                    status=EmailResultStatus.BOUNCED,
                    error_code="RECIPIENT_ERROR",
                    error_message=error_msg
                )
            
            # Check for Gmail daily limit exceeded
            # Error format: (550, '5.4.5 Daily user sending limit exceeded...')
            if (error_code == 550 or "550" in error_msg) and (
                "daily user sending limit exceeded" in error_str_lower or 
                "5.4.5" in error_msg or
                "daily sending limit" in error_str_lower
            ):
                # Calculate wait time until midnight (PST/PDT)
                from datetime import datetime, timedelta
                now = datetime.utcnow()
                # Gmail resets at midnight Pacific Time (UTC-8 or UTC-7)
                # Approximate: wait until next day UTC
                tomorrow = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
                wait_seconds = int((tomorrow - now).total_seconds())
                logger.warning(f"Gmail daily limit exceeded, wait {wait_seconds}s until reset")
                return EmailResult.rate_limited(f"Gmail daily limit exceeded. Wait {wait_seconds} seconds until reset")
            
            return EmailResult.failed("DATA_ERROR", error_msg)
            
        except aiosmtplib.SMTPServerDisconnected:
            # Connection lost, try to reconnect
            self._connected = False
            logger.warning("SMTP server disconnected, will retry")
            raise  # Let retry handle it
            
        except Exception as e:
            logger.error(f"SMTP send error: {str(e)}")
            return EmailResult.failed("SEND_ERROR", str(e))
    
    def _build_mime_message(self, message: EmailMessage) -> MIMEMultipart:
        """
        Build a proper MIME message with all headers.
        """
        # Create multipart message
        mime_msg = MIMEMultipart("alternative")
        
        # Set headers
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
        
        # List-Unsubscribe (critical for deliverability)
        domain = (message.from_email or self.sender_email).split('@')[1]
        mime_msg["List-Unsubscribe"] = f"<mailto:unsubscribe@{domain}>"
        mime_msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        
        # Add custom headers
        for key, value in message.custom_headers.items():
            mime_msg[key] = value
        
        # Plain text part (MUST be first for proper fallback)
        if message.body_plain:
            plain_part = MIMEText(message.body_plain, "plain", "utf-8")
            mime_msg.attach(plain_part)
        
        # HTML part
        html_part = MIMEText(message.body_html, "html", "utf-8")
        mime_msg.attach(html_part)
        
        return mime_msg

