#!/usr/bin/env python3
"""
Test script to verify PostgreSQL cache integration works correctly.
"""

import os
import sys

def test_database_connection():
    """Test basic database connection."""
    print("🧪 Testing PostgreSQL cache integration...")
    print("=" * 50)
    
    try:
        # Test database connection
        from database import test_database_connection
        print("📋 1. Testing database connection...")
        
        if test_database_connection():
            print("   ✅ Database connection successful")
        else:
            print("   ❌ Database connection failed")
            return False
            
    except ImportError as e:
        print(f"   ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Connection error: {e}")
        return False
    
    try:
        # Test table creation
        print("📋 2. Testing table creation...")
        from database import create_tables
        create_tables()
        print("   ✅ Tables created successfully")
        
    except Exception as e:
        print(f"   ❌ Table creation error: {e}")
        return False
    
    try:
        # Test cache service
        print("📋 3. Testing cache service...")
        from cache_service import cache_service
        
        # Test cache miss (should return None)
        result = cache_service.get_cached_result(
            "test_image_data", 
            [{"x": 1, "y": 1}] * 478, 
            "test_segmentation"
        )
        
        if result is None:
            print("   ✅ Cache miss test successful")
        else:
            print("   ❌ Unexpected cache hit")
            return False
            
    except Exception as e:
        print(f"   ❌ Cache service error: {e}")
        return False
    
    try:
        # Test database setup functions
        print("📋 4. Testing database setup...")
        from database_setup import create_database_views_and_functions
        create_database_views_and_functions()
        print("   ✅ Database views and functions created")
        
    except Exception as e:
        print(f"   ❌ Database setup error: {e}")
        return False
    
    try:
        # Test database stats
        print("📋 5. Testing database statistics...")
        from database_setup import get_database_stats
        stats = get_database_stats()
        
        if "total_tasks" in stats:
            print(f"   ✅ Statistics retrieved: {stats['total_tasks']} tasks")
        else:
            print(f"   ⚠️ Statistics partial: {stats}")
        
    except Exception as e:
        print(f"   ❌ Statistics error: {e}")
        return False
    
    print("\n🎉 All tests passed!")
    print("PostgreSQL cache integration is working correctly!")
    return True

def show_environment_info():
    """Show environment information for debugging."""
    print("\n🔧 Environment Information:")
    print(f"DATABASE_URL: {os.getenv('DATABASE_URL', 'Not set')}")
    print(f"REDIS_URL: {os.getenv('REDIS_URL', 'Not set')}")
    print(f"LOG_LEVEL: {os.getenv('LOG_LEVEL', 'Not set')}")

if __name__ == "__main__":
    # Show environment info
    show_environment_info()
    
    # Run tests
    try:
        success = test_database_connection()
        if success:
            print("\n✅ Ready for Docker deployment!")
            sys.exit(0)
        else:
            print("\n❌ Tests failed - check configuration")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n⚠️ Test interrupted by user")
        sys.exit(1)