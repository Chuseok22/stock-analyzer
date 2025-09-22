#!/usr/bin/env python3
"""
Mock test script for Redis connection and KIS token management (without real API calls).
"""
import logging
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.config.settings import settings
from app.database.redis_client import redis_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_redis_connection():
    """Test Redis connection."""
    print("\n=== Redis Connection Test ===")
    
    try:
        # Test basic connection
        result = redis_client.ping()
        if result:
            print("✅ Redis connection successful")
        else:
            print("❌ Redis ping failed")
            return False
            
        # Test set/get operations
        test_key = "test:redis:connection"
        test_value = {"timestamp": "2024-01-15T10:00:00", "test": True}
        
        # Set value with TTL
        redis_client.set_json(test_key, test_value, ttl=300)  # 5 minutes
        print(f"✅ Set test value with TTL: {test_key}")
        
        # Get value back
        retrieved = redis_client.get_json(test_key)
        if retrieved == test_value:
            print("✅ Retrieved value matches")
        else:
            print(f"❌ Retrieved value mismatch: {retrieved} != {test_value}")
            return False
            
        # Check TTL
        ttl = redis_client.get_ttl(test_key)
        print(f"✅ TTL remaining: {ttl} seconds")
        
        # Clean up
        redis_client.delete(test_key)
        print("✅ Test cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Redis test failed: {e}")
        return False


def test_kis_token_caching_mock():
    """Test KIS token caching functionality with mock data."""
    print("\n=== Mock KIS Token Caching Test ===")
    
    try:
        # Mock token data
        mock_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.mock_token_data"
        token_key = "kis:access_token"
        token_ttl = 86100  # ~24 hours - 5 minutes
        
        # Clear any existing token
        redis_client.delete(token_key)
        print("✅ Cleared existing token from cache")
        
        # Set mock token with TTL
        success = redis_client.set(token_key, mock_token, ttl=token_ttl)
        if success:
            print(f"✅ Successfully cached mock token: {mock_token[:20]}...")
        else:
            print("❌ Failed to cache mock token")
            return False
        
        # Retrieve token
        cached_token = redis_client.get(token_key)
        if cached_token == mock_token:
            print("✅ Retrieved token matches cached token")
        else:
            print(f"❌ Token mismatch: {cached_token} != {mock_token}")
            return False
        
        # Check TTL
        ttl = redis_client.get_ttl(token_key)
        print(f"✅ Token TTL: {ttl} seconds")
        
        if ttl > 0 and ttl <= token_ttl:
            print("✅ TTL is correctly set")
        else:
            print(f"❌ Unexpected TTL value: {ttl}")
            return False
        
        # Test token refresh simulation
        print("🔄 Simulating token refresh...")
        
        # Delete old token
        redis_client.delete(token_key)
        
        # Set new token
        new_mock_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzUxMiJ9.new_mock_token_data"
        redis_client.set(token_key, new_mock_token, ttl=token_ttl)
        
        # Verify new token
        refreshed_token = redis_client.get(token_key)
        if refreshed_token == new_mock_token:
            print("✅ Token refresh simulation successful")
        else:
            print("❌ Token refresh simulation failed")
            return False
        
        # Clean up
        redis_client.delete(token_key)
        print("✅ Mock test cleanup completed")
        
        return True
        
    except Exception as e:
        print(f"❌ Mock KIS token test failed: {e}")
        return False


def test_scheduler_integration():
    """Test scheduler integration with Redis."""
    print("\n=== Scheduler Integration Test ===")
    
    try:
        # Test that we can import scheduler components
        from app.services.scheduler import SchedulingService
        print("✅ Scheduler service imported successfully")
        
        # Create scheduler instance (but don't start it)
        scheduler = SchedulingService()
        print("✅ Scheduler instance created")
        
        # Test that KIS API client is accessible
        if hasattr(scheduler, 'kis_api'):
            print("✅ KIS API client is available in scheduler")
        else:
            print("❌ KIS API client not found in scheduler")
            return False
        
        # Stop scheduler to avoid running background tasks
        scheduler.stop_scheduler()
        print("✅ Scheduler stopped cleanly")
        
        return True
        
    except Exception as e:
        print(f"❌ Scheduler integration test failed: {e}")
        return False


def main():
    """Run all mock tests."""
    print("🚀 Starting Redis and KIS integration mock tests...")
    print(f"Redis URL: {settings.redis_url}")
    
    # Test Redis connection
    redis_ok = test_redis_connection()
    
    if not redis_ok:
        print("\n❌ Redis tests failed.")
        return False
        
    # Test KIS token caching with mock data
    kis_mock_ok = test_kis_token_caching_mock()
    
    # Test scheduler integration
    scheduler_ok = test_scheduler_integration()
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Redis Connection: {'✅ PASS' if redis_ok else '❌ FAIL'}")
    print(f"KIS Token Caching (Mock): {'✅ PASS' if kis_mock_ok else '❌ FAIL'}")
    print(f"Scheduler Integration: {'✅ PASS' if scheduler_ok else '❌ FAIL'}")
    
    if redis_ok and kis_mock_ok and scheduler_ok:
        print("\n🎉 All mock tests passed! Redis-based KIS token management framework is ready.")
        print("\n📝 Next Steps:")
        print("   1. Verify KIS API credentials are valid for your account")
        print("   2. Test with real KIS API when ready")
        print("   3. Start scheduler with daily token refresh at midnight")
        return True
    else:
        print("\n❌ Some tests failed. Please check the configuration.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
