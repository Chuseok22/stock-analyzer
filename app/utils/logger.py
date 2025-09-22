"""
Logging configuration for the stock analyzer application.
"""
import logging
import logging.handlers
import os
from datetime import datetime

from app.config.settings import settings


def setup_logging():
  """Setup application logging configuration."""

  # Create logs directory if it doesn't exist
  logs_dir = "logs"
  os.makedirs(logs_dir, exist_ok=True)

  # Configure root logger
  logger = logging.getLogger()
  logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

  # Clear existing handlers
  logger.handlers.clear()

  # Create formatters
  detailed_formatter = logging.Formatter(
      '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
  )

  simple_formatter = logging.Formatter(
      '%(asctime)s - %(levelname)s - %(message)s'
  )

  # Console handler
  console_handler = logging.StreamHandler()
  console_handler.setLevel(logging.INFO)
  console_handler.setFormatter(simple_formatter)
  logger.addHandler(console_handler)

  # File handler with rotation
  log_filename = os.path.join(logs_dir, settings.log_file)
  file_handler = logging.handlers.RotatingFileHandler(
      log_filename,
      maxBytes=10 * 1024 * 1024,  # 10MB
      backupCount=5,
      encoding='utf-8'
  )
  file_handler.setLevel(logging.DEBUG)
  file_handler.setFormatter(detailed_formatter)
  logger.addHandler(file_handler)

  # Create daily log file
  daily_log_filename = os.path.join(
      logs_dir,
      f"stock_analyzer_{datetime.now().strftime('%Y%m%d')}.log"
  )
  daily_handler = logging.FileHandler(daily_log_filename, encoding='utf-8')
  daily_handler.setLevel(logging.INFO)
  daily_handler.setFormatter(detailed_formatter)
  logger.addHandler(daily_handler)

  # Suppress verbose loggers
  logging.getLogger('urllib3').setLevel(logging.WARNING)
  logging.getLogger('requests').setLevel(logging.WARNING)
  logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

  logger.info("Logging configuration initialized")


def get_logger(name: str) -> logging.Logger:
  """Get a logger with the specified name."""
  return logging.getLogger(name)
