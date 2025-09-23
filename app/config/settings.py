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
  kis_app_key: str
  kis_app_secret: str
  kis_base_url: str

  # Alpha Vantage API settings (US stock data)
  alpha_vantage_api_key: str = ""

  # Redis settings
  redis_host: str
  redis_port: int
  redis_password: str
  redis_db: int

  # ML Model settings
  model_cache_dir: str
  feature_cache_dir: str

  # Logging settings
  log_level: str
  log_file: str

  # Scheduling settings
  default_universe_id: int
  default_region: str
  universe_size: int
  daily_recommendation_count: int
  send_admin_notifications: bool

  # Email notification settings
  smtp_enabled: bool
  smtp_host: str
  smtp_port: int
  smtp_use_tls: bool
  smtp_username: str
  smtp_password: str
  smtp_from_email: str
  notification_email: str

  # Slack notification settings
  slack_enabled: bool
  slack_token: str
  slack_channel: str

  # Discord notification settings
  discord_enabled: bool
  discord_webhook_url: str

  # Telegram notification settings
  telegram_enabled: bool
  telegram_bot_token: str
  telegram_chat_id: str

  # Application configuration
  app_name: str = "stock-analyzer"
  app_version: str = "1.0.0"
  debug: bool = False
  port: int = 8080

  # ML Model advanced settings
  ml_model_retrain_days: int = 7
  ml_prediction_threshold: float = 0.6
  ml_top_recommendations: int = 10

  # Data collection settings
  data_collection_stocks: int = 30
  data_collection_days: int = 60
  api_rate_limit_delay: float = 0.1

  # Backtest settings
  backtest_default_days: int = 30
  backtest_min_accuracy: float = 0.55

  # Real-time learning settings
  realtime_learning_enabled: bool = True
  performance_tracking_days: int = 30
  auto_model_backup: bool = True
  learning_strategy_threshold: float = 55.0

  # Timezone configuration
  tz: str = "Asia/Seoul"

  # Security settings
  secret_key: str = "your_secret_key_here"
  jwt_secret_key: str = "your_jwt_secret_key_here"
  encryption_key: str = "your_encryption_key_here"

  class Config:
    env_file = ".env"
    env_file_encoding = "utf-8"
    case_sensitive = False

  @property
  def database_url(self) -> str:
    """Generate database URL for SQLAlchemy using psycopg3."""
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
