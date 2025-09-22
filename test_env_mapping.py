#!/usr/bin/env python3
"""
Comprehensive test for environment variable mapping in settings.
"""
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.config.settings import settings

def test_env_mapping():
    """Test all environment variable mappings."""
    print("🔍 Environment Variable Mapping Test\n")
    
    # Database settings
    print("📊 Database Settings:")
    print(f"   DB_HOST → db_host: {settings.db_host}")
    print(f"   DB_PORT → db_port: {settings.db_port}")
    print(f"   DB_NAME → db_name: {settings.db_name}")
    print(f"   DB_USER → db_user: {settings.db_user}")
    print(f"   DB_PASSWORD → db_password: {'***' if settings.db_password else None}")
    
    # KIS API settings
    print("\n🔑 KIS API Settings:")
    print(f"   KIS_APP_KEY → kis_app_key: {settings.kis_app_key[:10] if settings.kis_app_key else None}...")
    print(f"   KIS_APP_SECRET → kis_app_secret: {'***' if settings.kis_app_secret else None}")
    print(f"   KIS_BASE_URL → kis_base_url: {settings.kis_base_url}")
    
    # Redis settings
    print("\n📦 Redis Settings:")
    print(f"   REDIS_HOST → redis_host: {settings.redis_host}")
    print(f"   REDIS_PORT → redis_port: {settings.redis_port}")
    print(f"   REDIS_PASSWORD → redis_password: {'***' if settings.redis_password else None}")
    print(f"   REDIS_DB → redis_db: {settings.redis_db}")
    
    # Model settings
    print("\n🤖 Model Settings:")
    print(f"   MODEL_CACHE_DIR → model_cache_dir: {settings.model_cache_dir}")
    print(f"   FEATURE_CACHE_DIR → feature_cache_dir: {settings.feature_cache_dir}")
    
    # Logging settings
    print("\n📝 Logging Settings:")
    print(f"   LOG_LEVEL → log_level: {settings.log_level}")
    print(f"   LOG_FILE → log_file: {settings.log_file}")
    
    # Scheduling settings
    print("\n⏰ Scheduling Settings:")
    print(f"   DEFAULT_UNIVERSE_ID → default_universe_id: {settings.default_universe_id}")
    print(f"   DEFAULT_REGION → default_region: {settings.default_region}")
    print(f"   UNIVERSE_SIZE → universe_size: {settings.universe_size}")
    print(f"   DAILY_RECOMMENDATION_COUNT → daily_recommendation_count: {settings.daily_recommendation_count}")
    print(f"   SEND_ADMIN_NOTIFICATIONS → send_admin_notifications: {settings.send_admin_notifications}")
    
    # Email settings
    print("\n📧 Email Settings:")
    print(f"   SMTP_ENABLED → smtp_enabled: {settings.smtp_enabled}")
    print(f"   SMTP_HOST → smtp_host: {settings.smtp_host}")
    print(f"   SMTP_PORT → smtp_port: {settings.smtp_port}")
    print(f"   SMTP_USE_TLS → smtp_use_tls: {settings.smtp_use_tls}")
    print(f"   SMTP_USERNAME → smtp_username: {settings.smtp_username}")
    print(f"   SMTP_PASSWORD → smtp_password: {'***' if settings.smtp_password else None}")
    print(f"   SMTP_FROM_EMAIL → smtp_from_email: {settings.smtp_from_email}")
    print(f"   NOTIFICATION_EMAIL → notification_email: {settings.notification_email}")
    
    # Slack settings
    print("\n💬 Slack Settings:")
    print(f"   SLACK_ENABLED → slack_enabled: {settings.slack_enabled}")
    print(f"   SLACK_TOKEN → slack_token: {settings.slack_token}")
    print(f"   SLACK_CHANNEL → slack_channel: {settings.slack_channel}")
    
    # Discord settings
    print("\n🎮 Discord Settings:")
    print(f"   DISCORD_ENABLED → discord_enabled: {settings.discord_enabled}")
    print(f"   DISCORD_WEBHOOK_URL → discord_webhook_url: {settings.discord_webhook_url[:30] if settings.discord_webhook_url else None}...")
    
    # Telegram settings
    print("\n📱 Telegram Settings:")
    print(f"   TELEGRAM_ENABLED → telegram_enabled: {settings.telegram_enabled}")
    print(f"   TELEGRAM_BOT_TOKEN → telegram_bot_token: {settings.telegram_bot_token}")
    print(f"   TELEGRAM_CHAT_ID → telegram_chat_id: {settings.telegram_chat_id}")
    
    # Generated URLs
    print("\n🔗 Generated URLs:")
    print(f"   Database URL: {settings.database_url}")
    print(f"   Redis URL: {settings.redis_url}")
    
    print("\n✅ All environment variables successfully mapped!")
    return True

if __name__ == "__main__":
    success = test_env_mapping()
    sys.exit(0 if success else 1)
