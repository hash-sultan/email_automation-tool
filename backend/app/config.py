"""
XenFlow Mailer - Configuration Management
Centralized configuration with environment variable support
"""

from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Application
    APP_NAME: str = "XenFlow Mailer"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    SECRET_KEY: str = Field(..., description="Secret key for JWT signing")
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Database
    DATABASE_URL: str = Field(..., description="PostgreSQL connection URL")
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    
    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")
    REDIS_PASSWORD: Optional[str] = None
    
    # Celery
    CELERY_BROKER_URL: str = Field(default="redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = Field(default="redis://localhost:6379/1")
    
    # Email Safety Thresholds (NON-NEGOTIABLE)
    MAX_EMAILS_PER_DAY: int = 200
    MAX_EMAILS_PER_HOUR: int = 20
    MAX_BOUNCE_RATE: float = 0.05  # 5%
    MAX_COMPLAINT_RATE: float = 0.001  # 0.1%
    MIN_SEND_INTERVAL_SECONDS: int = 60  # Minimum seconds between emails
    MAX_SEND_INTERVAL_SECONDS: int = 300  # Maximum seconds between emails
    
    # Warmup Configuration
    WARMUP_ENABLED: bool = True
    WARMUP_DAY_1_3_LIMIT: int = 10
    WARMUP_DAY_4_7_LIMIT: int = 25
    WARMUP_DAY_8_14_LIMIT: int = 50
    WARMUP_DAY_15_PLUS_LIMIT: int = 100
    
    # Follow-up Configuration
    FOLLOWUP_MIN_DELAY_HOURS: int = 24  # Minimum hours between follow-ups
    FOLLOWUP_MAX_STEPS: int = 10  # Maximum follow-up steps allowed
    
    # Send Window (Timezone-aware)
    SEND_WINDOW_START_HOUR: int = 9  # 9 AM
    SEND_WINDOW_END_HOUR: int = 17  # 5 PM
    SEND_WEEKDAYS_ONLY: bool = True
    DEFAULT_TIMEZONE: str = "America/New_York"
    
    # IMAP Configuration
    IMAP_CHECK_INTERVAL_MINUTES: int = 5
    
    # Gmail OAuth (Optional)
    GMAIL_CLIENT_ID: Optional[str] = None
    GMAIL_CLIENT_SECRET: Optional[str] = None
    GMAIL_REDIRECT_URI: str = "http://localhost:8000/api/v1/auth/google/callback"
    
    # Suppression
    SOFT_BOUNCE_THRESHOLD: int = 3  # Auto-suppress after X soft bounces
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Sentry (Optional)
    SENTRY_DSN: Optional[str] = None

    @validator("DATABASE_URL", pre=True)
    def validate_database_url(cls, v):
        if not v:
            raise ValueError("DATABASE_URL must be set")
        return v
    
    @validator("MAX_BOUNCE_RATE")
    def validate_bounce_rate(cls, v):
        if v > 0.10:  # Never allow more than 10% bounce rate
            raise ValueError("MAX_BOUNCE_RATE cannot exceed 10% for safety")
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Safety constants - NEVER modify these in runtime
class SafetyLimits:
    """Hard-coded safety limits that cannot be overridden"""
    
    ABSOLUTE_MAX_EMAILS_PER_DAY = 500  # Hard cap
    ABSOLUTE_MAX_EMAILS_PER_HOUR = 50  # Hard cap
    ABSOLUTE_MAX_BOUNCE_RATE = 0.10  # 10% - system stops
    ABSOLUTE_MAX_COMPLAINT_RATE = 0.005  # 0.5% - system stops
    MIN_EMAIL_INTERVAL_SECONDS = 30  # Never send faster than this
    
    @classmethod
    def is_safe_to_send(cls, daily_sent: int, hourly_sent: int, 
                        bounce_rate: float, complaint_rate: float) -> tuple[bool, str]:
        """
        Check if it's safe to send more emails.
        Returns (is_safe, reason)
        """
        if daily_sent >= cls.ABSOLUTE_MAX_EMAILS_PER_DAY:
            return False, f"Daily limit reached ({cls.ABSOLUTE_MAX_EMAILS_PER_DAY})"
        
        if hourly_sent >= cls.ABSOLUTE_MAX_EMAILS_PER_HOUR:
            return False, f"Hourly limit reached ({cls.ABSOLUTE_MAX_EMAILS_PER_HOUR})"
        
        if bounce_rate >= cls.ABSOLUTE_MAX_BOUNCE_RATE:
            return False, f"Bounce rate too high ({bounce_rate:.1%})"
        
        if complaint_rate >= cls.ABSOLUTE_MAX_COMPLAINT_RATE:
            return False, f"Complaint rate too high ({complaint_rate:.2%})"
        
        return True, "Safe to send"

