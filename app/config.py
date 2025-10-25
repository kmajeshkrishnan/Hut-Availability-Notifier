import os
from typing import Optional
from pydantic import field_validator
from pydantic_settings import BaseSettings
import logging

class Settings(BaseSettings):
    """Application configuration with validation."""
    
    # Database settings
    postgres_user: str = "user"
    postgres_password: str = "password"
    postgres_db: str = "db"
    db_host: str = "localhost"
    db_port: int = 5432
    
    # Scraper settings
    base_url: str = "https://www.forsthuetten-freiburg.de/de/buchen/index.php?id=3"
    check_interval_minutes: int = 30
    months_ahead: int = 3
    max_retries: int = 3
    request_timeout: int = 20
    backoff_multiplier: int = 3
    
    # Application settings
    log_level: str = "INFO"
    max_notification_age_days: int = 90
    # max_availability_age_days will be calculated from months_ahead
    
    # API settings
    max_notifications_limit: int = 100
    default_notifications_limit: int = 20

    resend_api_key: str
    
    @field_validator('log_level')
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'log_level must be one of {valid_levels}')
        return v.upper()
    
    @field_validator('resend_api_key')
    @classmethod
    def validate_resend_api_key(cls, v):
        if not v or v.strip() == "":
            raise ValueError('resend_api_key must be provided as an environment variable and cannot be empty')
        return v

    @field_validator('check_interval_minutes')
    @classmethod
    def validate_check_interval(cls, v):
        if v < 1 or v > 1440:  # 1 minute to 24 hours
            raise ValueError('check_interval_minutes must be between 1 and 1440')
        return v
    
    @field_validator('max_retries')
    @classmethod
    def validate_max_retries(cls, v):
        if v < 0 or v > 10:
            raise ValueError('max_retries must be between 0 and 10')
        return v
    
    @field_validator('months_ahead')
    @classmethod
    def validate_months_ahead(cls, v):
        if v < 1 or v > 12:
            raise ValueError('months_ahead must be between 1 and 12')
        return v
    
    @property
    def database_url(self) -> str:
        """Construct database URL from components."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.db_host}:{self.db_port}/{self.postgres_db}"
    
    @property
    def max_availability_age_days(self) -> int:
        """Calculate max availability age based on months_ahead setting."""
        # Add some buffer (30 days) to ensure we don't clean up data we're still monitoring
        return (self.months_ahead * 30) + 30
    
    class Config:
        env_file = ".env"
        case_sensitive = False

# Global settings instance
settings = Settings()

def setup_logging():
    """Configure structured logging."""
    import os
    
    # Create handlers
    handlers = [logging.StreamHandler()]
    
    # Only add file handler if we can write to the log file
    try:
        # Try to create the log file in a safe location
        log_file = os.path.join(os.getcwd(), "app.log")
        file_handler = logging.FileHandler(log_file)
        handlers.append(file_handler)
    except (OSError, IOError) as e:
        # If we can't create the file handler, just use console logging
        print(f"Warning: Could not create log file: {e}")
    
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=handlers
    )
    
    # Set specific loggers
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
