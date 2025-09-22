"""
Configuration settings for the stock analyzer application.
"""
from typing import Optional

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
  """Application settings with environment variable support."""

  # Database settings
  db_host: str
  db_port: int
  db_name: str
  db_user: str
  db_password: str

  # KIS API settings
  kis_app_key: Optional[str]
  kis_app_secret: Optional[str]
  kis_base_url: str

  # Redis settings
  redis_host: str
  redis_port: int
  redis_password: Optional[str]
  redis_db: int

  # ML Model settings
  model_cache_dir: str
  feature_cache_dir: str

  # Logging settings
  log_level: str
  log_file: str

  # Scheduling settings
  default_universe_id: Optional[int]
  default_region: str
  universe_size: int
  daily_recommendation_count: int
  send_admin_notifications: bool

  # Email notification settings
  smtp_enabled: bool
  smtp_host: str
  smtp_port: int
  smtp_use_tls: bool
  smtp_username: Optional[str]
  smtp_password: Optional[str]
  smtp_from_email: Optional[str]
  notification_email: Optional[str]

  # Slack notification settings
  slack_enabled: bool
  slack_token: Optional[str]
  slack_channel: str

  # Discord notification settings
  discord_enabled: bool
  discord_webhook_url: Optional[str]

  # Telegram notification settings
  telegram_enabled: bool
  telegram_bot_token: Optional[str]
  telegram_chat_id: Optional[str]

  class Config:
    env_file = ".env"
    env_file_encoding = "utf-8"
    case_sensitive = False

  @property
  def database_url(self) -> str:
    """Generate database URL for SQLAlchemy using psycopg (asyncpg-style)."""
    return f"postgresql+psycopg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

  @property
  def redis_url(self) -> str:
    """Generate Redis URL."""
    if self.redis_password:
      return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
    else:
      return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


# Global settings instance
settings = Settings()
