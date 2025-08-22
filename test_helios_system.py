#!/usr/bin/env python3
"""
Test script for Helios system after configuration
Run this after setting up your .env file
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# Add helios to path
sys.path.insert(0, str(Path(__file__).parent))

async def test_system():
    """Test the Helios system components"""
    print("=" * 60)
    print("🧪 HELIOS SYSTEM TEST")
    print("=" * 60)
    
    try:
        # Step 1: Load configuration
        print("\n1️⃣ Loading configuration...")
        from helios.config import load_config
        config = load_config()
        
        if not config.printify_api_token or not config.printify_shop_id:
            print("❌ Missing Printify credentials. Please set up your .env file first!")
            return False
        
        print(f"✅ Configuration loaded")
        print(f"   Shop ID: {config.printify_shop_id}")
        print(f"   Dry Run: {config.dry_run}")
        print(f"   Live Publishing: {config.allow_live_publishing}")
        
        # Step 2: Test Printify connection
        print("\n2️⃣ Testing Printify connection...")
        from helios.services.external_apis.printify_client import PrintifyAPIClient
        from helios.services.google_cloud.storage_client import CloudStorageClient
        
        # Create storage client (may be None if not configured)
        storage_client = None
        if config.google_cloud_project and config.assets_bucket:
            try:
                storage_client = CloudStorageClient(
                    project_id=config.google_cloud_project,
                    bucket_name=config.assets_bucket
                )
            except:
                print("⚠️  Cloud Storage not configured, using local storage")
        
        printify_client = PrintifyAPIClient(
            api_token=config.printify_api_token,
            shop_id=config.printify_shop_id,
            storage_client=storage_client
        )
        
        # Test getting shop info
        shop_info = await printify_client.get_shop_info()
        if shop_info:
            print(f"✅ Connected to Printify shop: {shop_info.get('title', 'Unknown')}")
        else:
            print("❌ Failed to connect to Printify")
            return False
        
        # Step 3: Test AI components (if configured)
        print("\n3️⃣ Testing AI components...")
        if config.google_api_key:
            print("✅ Google API key configured")
            # Could test Gemini here
        else:
            print("⚠️  No Google API key - AI features disabled")
        
        # Step 4: Test trend discovery (simplified)
        print("\n4️⃣ Testing trend discovery...")
        from helios.services.automated_trend_discovery import AutomatedTrendDiscovery
        
        trend_discovery = AutomatedTrendDiscovery(config)
        print("✅ Trend discovery service initialized")
        
        if not config.dry_run:
            print("\n⚠️  WARNING: System is NOT in dry run mode!")
            print("   Products will be created for real!")
            response = input("   Continue? (y/N): ")
            if response.lower() != 'y':
                print("   Test cancelled.")
                return False
        
        # Step 5: Run a minimal trend discovery
        print("\n5️⃣ Running minimal trend discovery test...")
        print("   This will search for trends but won't create products in test mode")
        
        # Just test the initialization
        session = await trend_discovery.start_discovery_session(
            seed_keywords=["test", "trending"]
        )
        
        if session:
            print(f"✅ Discovery session created: {session.session_id}")
        else:
            print("❌ Failed to create discovery session")
        
        print("\n" + "=" * 60)
        print("✅ SYSTEM TEST COMPLETE")
        print("\nNext steps:")
        print("1. If test passed, run full trend discovery:")
        print("   python -m helios.services.automated_trend_discovery")
        print("2. Or start the web service:")
        print("   python main.py")
        print("3. Monitor logs for activity")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run the test"""
    success = asyncio.run(test_system())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()