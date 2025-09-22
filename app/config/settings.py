"""
Configuration settings for the stock analyzer application.
"""
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Database settings
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "stock_trader"
    db_user: str = "postgres"
    db_password: str = "password"
    
    # KIS API settings
    kis_app_key: Optional[str] = None
    kis_app_secret: Optional[str] = None
    kis_base_url: str = "https://openapi.koreainvestment.com:9443"
    
    # ML Model settings
    model_cache_dir: str = "models"
    feature_cache_dir: str = "features"
    
    # Logging settings
    log_level: str = "INFO"
    log_file: str = "stock_analyzer.log"
    
    # Scheduling settings
    default_universe_id: Optional[int] = 1
    default_region: str = "KR"
    universe_size: int = 200
    daily_recommendation_count: int = 20
    send_admin_notifications: bool = True
    
    # Email notification settings
    smtp_enabled: bool = False
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_use_tls: bool = True
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from_email: Optional[str] = None
    notification_email: Optional[str] = None
    
    # Slack notification settings
    slack_enabled: bool = False
    slack_token: Optional[str] = None
    slack_channel: str = "#stock-alerts"
    
    # Discord notification settings
    discord_enabled: bool = False
    discord_webhook_url: Optional[str] = None
    
    # Telegram notification settings
    telegram_enabled: bool = False
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
    
    @property
    def database_url(self) -> str:
        """Generate database URL for SQLAlchemy."""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


# Global settings instance
settings = Settings()
