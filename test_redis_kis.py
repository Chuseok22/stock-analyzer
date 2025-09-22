#!/usr/bin/env python3
"""
Test script for Redis connection and KIS token management.
"""
import logging
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent / "app"))

from app.config.settings import settings
from app.database.redis_client import redis_client
from app.services.kis_api import KISAPIClient

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


def test_kis_token_management():
    """Test KIS token management with Redis."""
    print("\n=== KIS Token Management Test ===")
    
    try:
        # Initialize KIS API client
        kis_client = KISAPIClient()
        print("✅ KIS API client initialized")
        
        # Test token refresh (this will actually call KIS API)
        print("🔄 Testing token refresh...")
        
        # First, clear any existing token
        redis_client.delete("kis:access_token")
        print("✅ Cleared existing token from cache")
        
        # Get token (should fetch new one)
        token = kis_client.get_access_token()
        if token:
            print(f"✅ Successfully obtained access token: {token[:20]}...")
            
            # Check if token is cached in Redis (stored as plain string)
            cached_token = redis_client.get("kis:access_token")
            if cached_token:
                print("✅ Token successfully cached in Redis")
                print(f"   Token: {cached_token[:20]}...")
                
                # Check TTL
                ttl = redis_client.get_ttl("kis:access_token")
                print(f"   TTL: {ttl} seconds")
                
                # Verify tokens match
                if cached_token == token:
                    print("✅ Cached token matches returned token")
                else:
                    print("❌ Cached token does not match returned token")
                    return False
            else:
                print("❌ Token not found in Redis cache")
                return False
                
        else:
            print("❌ Failed to obtain access token")
            return False
            
        # Test getting token again (should use cached version)
        print("🔄 Testing cached token retrieval...")
        token2 = kis_client.get_access_token()
        if token2 == token:
            print("✅ Successfully retrieved cached token")
        else:
            print("❌ Cached token mismatch")
            return False
            
        # Test daily refresh method
        print("🔄 Testing daily refresh method...")
        refresh_success = kis_client.refresh_token_daily()
        if refresh_success:
            print("✅ Daily refresh method executed successfully")
        else:
            print("❌ Daily refresh method failed")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ KIS token test failed: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Starting Redis and KIS integration tests...")
    print(f"Redis URL: {settings.redis_url}")
    
    # Test Redis connection
    redis_ok = test_redis_connection()
    
    if not redis_ok:
        print("\n❌ Redis tests failed. Cannot proceed with KIS tests.")
        return False
        
    # Test KIS token management
    kis_ok = test_kis_token_management()
    
    # Summary
    print("\n=== Test Summary ===")
    print(f"Redis Connection: {'✅ PASS' if redis_ok else '❌ FAIL'}")
    print(f"KIS Token Management: {'✅ PASS' if kis_ok else '❌ FAIL'}")
    
    if redis_ok and kis_ok:
        print("\n🎉 All tests passed! Redis-based KIS token management is ready.")
        return True
    else:
        print("\n❌ Some tests failed. Please check the configuration.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
