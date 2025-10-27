#!/usr/bin/env python3
"""
Diagnostic script to check Helios system status and identify issues
"""

import os
import sys
from pathlib import Path
import json
from datetime import datetime, timezone

# Add helios to path
sys.path.insert(0, str(Path(__file__).parent))

from helios.config import load_config
from loguru import logger

def check_configuration():
    """Check if all required configuration is present"""
    print("\n🔍 CHECKING CONFIGURATION...")
    
    try:
        config = load_config()
        
        # Check critical environment variables
        issues = []
        
        # Printify credentials
        if not config.printify_api_token:
            issues.append("❌ PRINTIFY_API_TOKEN is not set")
        else:
            print("✅ Printify API token found")
            
        if not config.printify_shop_id:
            issues.append("❌ PRINTIFY_SHOP_ID is not set")
        else:
            print(f"✅ Printify Shop ID: {config.printify_shop_id}")
        
        # Google Cloud credentials
        if not config.google_cloud_project:
            issues.append("❌ GOOGLE_CLOUD_PROJECT is not set")
        else:
            print(f"✅ Google Cloud Project: {config.google_cloud_project}")
            
        if not config.google_api_key:
            issues.append("❌ GOOGLE_API_KEY (for Gemini) is not set")
        else:
            print("✅ Google API key found")
            
        # MCP Configuration
        if not config.google_mcp_url:
            issues.append("⚠️  GOOGLE_MCP_URL is not set (using default)")
        else:
            print(f"✅ Google MCP URL: {config.google_mcp_url}")
        
        # Check important flags
        print(f"\n📊 SYSTEM SETTINGS:")
        print(f"   Dry Run Mode: {'ON' if config.dry_run else 'OFF'}")
        print(f"   Live Publishing: {'ENABLED' if config.allow_live_publishing else 'DISABLED'}")
        print(f"   AI Orchestration: ENABLED")
        print(f"   Early Trend Detection: {'ENABLED' if config.enable_early_trend_detection else 'DISABLED'}")
        
        # Show thresholds
        print(f"\n📈 THRESHOLDS:")
        print(f"   Min Opportunity Score: {config.min_opportunity_score}")
        print(f"   Min Audience Confidence: {config.min_audience_confidence}")
        print(f"   Min Profit Margin: {config.min_profit_margin}")
        
        if issues:
            print(f"\n⚠️  CONFIGURATION ISSUES FOUND:")
            for issue in issues:
                print(f"   {issue}")
        else:
            print("\n✅ All critical configuration present")
            
        return len(issues) == 0, config
        
    except Exception as e:
        print(f"\n❌ Error loading configuration: {e}")
        return False, None


def check_printify_connection(config):
    """Test Printify API connection"""
    print("\n🔍 CHECKING PRINTIFY CONNECTION...")
    
    if not config.printify_api_token or not config.printify_shop_id:
        print("❌ Cannot test Printify - missing credentials")
        return False
        
    try:
        import httpx
        import asyncio
        
        async def test_connection():
            headers = {
                "Authorization": f"Bearer {config.printify_api_token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                # Test getting shop info
                url = f"https://api.printify.com/v1/shops/{config.printify_shop_id}.json"
                response = await client.get(url, headers=headers)
                
                if response.status_code == 200:
                    shop_data = response.json()
                    print(f"✅ Connected to Printify shop: {shop_data.get('title', 'Unknown')}")
                    
                    # Check for products
                    products_url = f"https://api.printify.com/v1/shops/{config.printify_shop_id}/products.json"
                    products_response = await client.get(products_url, headers=headers)
                    
                    if products_response.status_code == 200:
                        products = products_response.json()
                        print(f"✅ Found {len(products.get('data', []))} products in store")
                    
                    return True
                else:
                    print(f"❌ Printify API error: {response.status_code} - {response.text}")
                    return False
        
        return asyncio.run(test_connection())
        
    except Exception as e:
        print(f"❌ Error testing Printify connection: {e}")
        return False


def check_recent_activity():
    """Check for recent system activity"""
    print("\n🔍 CHECKING RECENT ACTIVITY...")
    
    # Check for output files
    output_dir = Path("/workspace/output")
    if output_dir.exists():
        files = list(output_dir.glob("**/*"))
        if files:
            print(f"✅ Found {len(files)} files in output directory")
            # Show recent files
            recent_files = sorted(files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]
            print("   Recent files:")
            for f in recent_files:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                print(f"   - {f.name} (modified: {mtime})")
        else:
            print("❌ No files found in output directory")
    else:
        print("❌ Output directory does not exist")
    
    # Check for log files
    log_dir = Path("/workspace/logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        if log_files:
            print(f"\n✅ Found {len(log_files)} log files")
            # Check recent logs
            for log_file in sorted(log_files, key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
                print(f"   - {log_file.name}")
                # Show last few lines
                try:
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        if lines:
                            print(f"     Last entry: {lines[-1].strip()}")
                except:
                    pass
    else:
        print("❌ No logs directory found")


def check_automation_status():
    """Check if automation is properly configured"""
    print("\n🔍 CHECKING AUTOMATION STATUS...")
    
    # Check for Cloud Scheduler jobs (would need gcloud access)
    print("⚠️  Cannot check Cloud Scheduler jobs without gcloud CLI access")
    
    # Check for cron configuration
    cron_file = Path("/workspace/crontab")
    if cron_file.exists():
        print("✅ Found crontab file")
        with open(cron_file, 'r') as f:
            print(f"   Contents:\n{f.read()}")
    else:
        print("❌ No local crontab file found")
    
    # Check for systemd service
    service_file = Path("/etc/systemd/system/helios.service")
    if service_file.exists():
        print("✅ Found systemd service file")
    else:
        print("❌ No systemd service found")


def main():
    """Run all diagnostic checks"""
    print("=" * 60)
    print("🏥 HELIOS SYSTEM DIAGNOSTICS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    # Check configuration
    config_ok, config = check_configuration()
    
    if config_ok and config:
        # Test Printify connection
        printify_ok = check_printify_connection(config)
        
        # Check recent activity
        check_recent_activity()
        
        # Check automation
        check_automation_status()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 DIAGNOSIS SUMMARY:")
        
        if config.dry_run:
            print("\n⚠️  SYSTEM IS IN DRY RUN MODE - No actual products will be published!")
            print("   To enable live publishing, set:")
            print("   - DRY_RUN=false")
            print("   - ALLOW_LIVE_PUBLISHING=true")
        
        if not config.allow_live_publishing:
            print("\n⚠️  LIVE PUBLISHING IS DISABLED - Products will be created as drafts only!")
            print("   To enable live publishing, set ALLOW_LIVE_PUBLISHING=true")
        
        if not printify_ok:
            print("\n❌ PRINTIFY CONNECTION FAILED - Check your API credentials")
        
        print("\n🔧 NEXT STEPS:")
        print("1. Ensure all environment variables are set")
        print("2. Verify Google Cloud services are deployed and running")
        print("3. Check Cloud Scheduler jobs are created and enabled")
        print("4. Monitor Cloud Run logs for any errors")
        print("5. Ensure dry_run mode is disabled for production")
        
    else:
        print("\n❌ CRITICAL: Configuration issues prevent system from running")
        print("   Please set up required environment variables")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()