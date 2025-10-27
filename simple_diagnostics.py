#!/usr/bin/env python3
"""
Simple diagnostic script to check Helios system status
"""

import os
import json
from datetime import datetime, timezone
from pathlib import Path

def main():
    print("=" * 60)
    print("🏥 HELIOS SYSTEM DIAGNOSTICS (SIMPLE)")
    print("=" * 60)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    
    print("\n🔍 CHECKING ENVIRONMENT VARIABLES...")
    
    # Check critical environment variables
    env_vars = {
        "PRINTIFY_API_TOKEN": "❌ NOT SET" if not os.getenv("PRINTIFY_API_TOKEN") else "✅ SET",
        "PRINTIFY_SHOP_ID": "❌ NOT SET" if not os.getenv("PRINTIFY_SHOP_ID") else f"✅ {os.getenv('PRINTIFY_SHOP_ID')}",
        "GOOGLE_CLOUD_PROJECT": "❌ NOT SET" if not os.getenv("GOOGLE_CLOUD_PROJECT") else f"✅ {os.getenv('GOOGLE_CLOUD_PROJECT')}",
        "GOOGLE_API_KEY": "❌ NOT SET" if not os.getenv("GOOGLE_API_KEY") else "✅ SET",
        "DRY_RUN": os.getenv("DRY_RUN", "true"),
        "ALLOW_LIVE_PUBLISHING": os.getenv("ALLOW_LIVE_PUBLISHING", "false"),
    }
    
    for var, value in env_vars.items():
        print(f"   {var}: {value}")
    
    print("\n🔍 CHECKING FILE SYSTEM...")
    
    # Check for .env file
    env_file = Path("/workspace/.env")
    if env_file.exists():
        print("✅ .env file exists")
        print(f"   Size: {env_file.stat().st_size} bytes")
    else:
        print("❌ No .env file found")
    
    # Check for output directory
    output_dir = Path("/workspace/output")
    if output_dir.exists():
        files = list(output_dir.glob("**/*"))
        print(f"✅ Output directory exists with {len(files)} files")
        if files:
            recent = sorted(files, key=lambda x: x.stat().st_mtime if x.is_file() else 0, reverse=True)[:3]
            print("   Recent files:")
            for f in recent:
                if f.is_file():
                    mtime = datetime.fromtimestamp(f.stat().st_mtime)
                    print(f"   - {f.name} ({mtime.strftime('%Y-%m-%d %H:%M')})")
    else:
        print("❌ No output directory found")
    
    # Check for logs
    log_dir = Path("/workspace/logs")
    if log_dir.exists():
        log_files = list(log_dir.glob("*.log"))
        print(f"✅ Logs directory exists with {len(log_files)} log files")
    else:
        print("❌ No logs directory found")
    
    # Check deployment files
    print("\n🔍 CHECKING DEPLOYMENT FILES...")
    deployment_files = [
        "/workspace/Procfile",
        "/workspace/runtime.txt",
        "/workspace/requirements.txt",
        "/workspace/deployment/cloud_run/cloudbuild.yaml"
    ]
    
    for file_path in deployment_files:
        if Path(file_path).exists():
            print(f"✅ {Path(file_path).name} exists")
        else:
            print(f"❌ {Path(file_path).name} not found")
    
    print("\n" + "=" * 60)
    print("📋 DIAGNOSIS SUMMARY:")
    print("\n⚠️  CRITICAL ISSUES:")
    
    if not os.getenv("PRINTIFY_API_TOKEN"):
        print("1. PRINTIFY_API_TOKEN is not set - System cannot connect to Printify")
    if not os.getenv("PRINTIFY_SHOP_ID"):
        print("2. PRINTIFY_SHOP_ID is not set - System doesn't know which shop to use")
    if not os.getenv("GOOGLE_API_KEY"):
        print("3. GOOGLE_API_KEY is not set - AI features will not work")
    
    if os.getenv("DRY_RUN", "true").lower() == "true":
        print("4. System is in DRY RUN mode - No products will be published")
    if os.getenv("ALLOW_LIVE_PUBLISHING", "false").lower() == "false":
        print("5. Live publishing is DISABLED - Products will only be saved as drafts")
    
    print("\n🔧 TO FIX:")
    print("1. Create a .env file with your credentials:")
    print("   PRINTIFY_API_TOKEN=your_token_here")
    print("   PRINTIFY_SHOP_ID=your_shop_id_here")
    print("   GOOGLE_API_KEY=your_gemini_api_key")
    print("   GOOGLE_CLOUD_PROJECT=your_project_id")
    print("   DRY_RUN=false")
    print("   ALLOW_LIVE_PUBLISHING=true")
    print("\n2. Deploy to Google Cloud Run:")
    print("   gcloud builds submit --config deployment/cloud_run/cloudbuild.yaml")
    print("\n3. Set up Cloud Scheduler jobs:")
    print("   - Trend discovery every 6 hours")
    print("   - Product generation every 4 hours")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()