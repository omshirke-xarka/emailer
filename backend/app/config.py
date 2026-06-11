import os
from typing import Optional
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Server Configuration
    port: int = 3001
    node_env: str = "development"
    
    # Azure Configuration
    azure_tenant_id: Optional[str] = None
    azure_client_id: Optional[str] = None
    azure_client_secret: Optional[str] = None
    
    # Email Configuration
    sender_email: str = "noreply@emailer.dev"
    app_url: str = "http://localhost:3001"
    email_provider: str = "aws"
    
    # Email Rate Limiting
    email_rate_limit_interval_ms: int = 1000
    email_rate_limit_max_per_minute: int = 60
    email_rate_limit_max_per_hour: int = 3600
    
    # AWS SES Configuration
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    aws_default_region: str = "ap-south-1"
    aws_ses_from_email: Optional[str] = None
    ses_sender_name: Optional[str] = None

    # Resend Configuration
    resend_api_key: Optional[str] = None
    resend_from_email: str = "LawgicHub <noreply@lawgichub.com>"
    
    # Redis Configuration
    redis_url: str = "redis://localhost:6379"
    kv_url: Optional[str] = None
    kv_rest_api_url: Optional[str] = None
    kv_rest_api_token: Optional[str] = None
    kv_rest_api_read_only_token: Optional[str] = None
    
    # Tracking Configuration
    tracking_base_url: Optional[str] = None
    
    # Blob Configuration
    blob_read_write_token: Optional[str] = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def email_rate_limit(self):
        return {
            "interval_ms": self.email_rate_limit_interval_ms,
            "max_per_minute": self.email_rate_limit_max_per_minute,
            "max_per_hour": self.email_rate_limit_max_per_hour,
        }
    
    @property
    def ses(self):
        return {
            "access_key_id": self.aws_access_key_id,
            "secret_access_key": self.aws_secret_access_key,
            "region": self.aws_default_region,
            "source_email": self.aws_ses_from_email,
            "sender_name": self.ses_sender_name,
        }


@lru_cache()
def get_settings() -> Settings:
    return Settings()


# Global settings instance
settings = get_settings()
