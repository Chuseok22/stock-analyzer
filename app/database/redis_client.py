"""
Redis client configuration and management.
"""
import json
import logging
from typing import Optional, Any

import redis

from app.config.settings import settings

logger = logging.getLogger(__name__)


class RedisClient:
  """Redis client for caching and session management."""

  def __init__(self):
    """Initialize Redis client."""
    try:
      self.client = redis.Redis.from_url(
          settings.redis_url,
          decode_responses=True,
          socket_connect_timeout=5,
          socket_timeout=5,
          retry_on_timeout=True,
          health_check_interval=30
      )

      # Test connection
      self.client.ping()
      logger.info("Redis connection established successfully")

    except Exception as e:
      logger.error(f"Failed to connect to Redis: {e}")
      raise

  def get(self, key: str) -> Optional[str]:
    """Get value from Redis."""
    try:
      return self.client.get(key)
    except Exception as e:
      logger.error(f"Redis GET failed for key {key}: {e}")
      return None

  def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
    """Set value in Redis with optional TTL."""
    try:
      if ttl:
        return self.client.setex(key, ttl, value)
      else:
        return self.client.set(key, value)
    except Exception as e:
      logger.error(f"Redis SET failed for key {key}: {e}")
      return False

  def get_json(self, key: str) -> Optional[Any]:
    """Get JSON value from Redis."""
    try:
      value = self.client.get(key)
      if value:
        return json.loads(value)
      return None
    except Exception as e:
      logger.error(f"Redis GET JSON failed for key {key}: {e}")
      return None

  def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set JSON value in Redis with optional TTL."""
    try:
      json_value = json.dumps(value, ensure_ascii=False)
      if ttl:
        return self.client.setex(key, ttl, json_value)
      else:
        return self.client.set(key, json_value)
    except Exception as e:
      logger.error(f"Redis SET JSON failed for key {key}: {e}")
      return False

  def delete(self, key: str) -> bool:
    """Delete key from Redis."""
    try:
      return bool(self.client.delete(key))
    except Exception as e:
      logger.error(f"Redis DELETE failed for key {key}: {e}")
      return False

  def exists(self, key: str) -> bool:
    """Check if key exists in Redis."""
    try:
      return bool(self.client.exists(key))
    except Exception as e:
      logger.error(f"Redis EXISTS failed for key {key}: {e}")
      return False

  def ttl(self, key: str) -> int:
    """Get TTL of key in Redis."""
    try:
      return self.client.ttl(key)
    except Exception as e:
      logger.error(f"Redis TTL failed for key {key}: {e}")
      return -1

  def get_ttl(self, key: str) -> int:
    """Get TTL of key in Redis (alias for ttl)."""
    return self.ttl(key)

  def ping(self) -> bool:
    """Ping Redis server to check connection."""
    try:
      return self.client.ping()
    except Exception as e:
      logger.error(f"Redis PING failed: {e}")
      return False

  def close(self):
    """Close Redis connection."""
    try:
      self.client.close()
      logger.info("Redis connection closed")
    except Exception as e:
      logger.error(f"Failed to close Redis connection: {e}")


# Global Redis client instance
redis_client = RedisClient()
