#!/usr/bin/env python3
"""
Google Cloud Run Local Testing Script
Follows official Google Cloud testing guidelines
"""

import subprocess
import sys
import time
import requests
from pathlib import Path

def test_service_locally(service_name, port):
    """Test a service locally using Google Cloud recommended approach"""
    print(f"🧪 Testing {service_name} locally...")
    
    try:
        # Start the service in background
        proc = subprocess.Popen([
            'gunicorn', '--bind', f':{port}',
            '--workers', '1',
            '--timeout', '120',
            '--worker-class', 'uvicorn.workers.UvicornWorker',
            f'helios_{service_name}.main:app'
        ], cwd=service_name, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait for service to start
        time.sleep(3)
        
        # Test health endpoint
        response = requests.get(f'http://localhost:{port}/health', timeout=10)
        
        if response.status_code == 200:
            print(f"✅ {service_name}: Health check passed")
            proc.terminate()
            return True
        else:
            print(f"❌ {service_name}: Health check failed - {response.status_code}")
            proc.terminate()
            return False
            
    except Exception as e:
        print(f"❌ {service_name}: Local test failed - {e}")
        return False

def main():
    """Run local tests following Google Cloud guidelines"""
    print("🚀 Google Cloud Run Local Testing")
    print("=" * 50)
    
    # Test orchestrator
    orchestrator_ok = test_service_locally('orchestrator', 8080)
    
    # Test agents (on different port)
    agents_ok = test_service_locally('agents', 8081)
    
    print("\n" + "=" * 50)
    print("📊 Local Test Results:")
    
    if orchestrator_ok and agents_ok:
        print("🎉 ALL LOCAL TESTS PASSED! Ready for Cloud deployment.")
        return 0
    else:
        print("❌ Some tests failed. Check service implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
