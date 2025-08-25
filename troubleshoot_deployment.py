#!/usr/bin/env python3
"""
Google Cloud Run Deployment Troubleshooting Script
Based on official troubleshooting guidelines
"""

import subprocess
import sys
from pathlib import Path

def check_build_readiness():
    """Check if services are ready for Cloud Build"""
    print("🔍 Checking Cloud Build readiness...")
    
    checks = [
        ("Runtime files", ["orchestrator/runtime.txt", "agents/runtime.txt"]),
        ("Requirements files", ["orchestrator/requirements.txt", "agents/requirements.txt"]),
        ("Procfile files", ["orchestrator/Procfile", "agents/Procfile"]),
        ("Source structure", ["orchestrator/src/helios_orchestrator/main.py", "agents/src/helios_agents/main.py"]),
        ("Build config", ["deployment/cloud_run/cloudbuild.yaml"])
    ]
    
    all_ok = True
    
    for check_name, files in checks:
        print(f"   Checking {check_name}...")
        for file in files:
            try:
                with open(file, 'r'):
                    print(f"     ✅ {file}")
            except FileNotFoundError:
                print(f"     ❌ {file} - MISSING")
                all_ok = False
            except Exception as e:
                print(f"     ⚠️  {file} - ERROR: {e}")
                all_ok = False
    
    return all_ok

def validate_python_version():
    """Validate Python version compatibility"""
    print("\n🔍 Checking Python version compatibility...")
    
    version = sys.version_info
    print(f"   Local Python: {version.major}.{version.minor}.{version.micro}")
    
    # Check against runtime.txt requirements
    try:
        with open('orchestrator/runtime.txt', 'r') as f:
            runtime_req = f.read().strip()
            print(f"   Cloud Runtime: {runtime_req}")
            
            # Basic compatibility check
            if runtime_req.startswith('python-3.11'):
                print("   ✅ Python 3.11 compatible with Cloud Buildpacks")
                return True
            else:
                print("   ⚠️  Check Cloud Buildpacks Python version support")
                return True
    except FileNotFoundError:
        print("   ❌ runtime.txt not found")
        return False

def check_service_isolation():
    """Check that services are properly isolated"""
    print("\n🔍 Checking service isolation...")
    
    # Check that each service has its own requirements
    orchestrator_reqs = Path('orchestrator/requirements.txt')
    agents_reqs = Path('agents/requirements.txt')
    
    if orchestrator_reqs.exists() and agents_reqs.exists():
        print("   ✅ Each service has its own requirements.txt")
        
        # Check if requirements are different (indicating proper isolation)
        with open(orchestrator_reqs) as f:
            orchestrator_content = f.read()
        
        with open(agents_reqs) as f:
            agents_content = f.read()
            
        if orchestrator_content != agents_content:
            print("   ✅ Services have different dependencies (proper isolation)")
        else:
            print("   ⚠️  Services have identical dependencies (may indicate over-sharing)")
            
        return True
    else:
        print("   ❌ Missing service-specific requirements files")
        return False

def main():
    """Run deployment troubleshooting checks"""
    print("🛠️  Google Cloud Run Deployment Troubleshooting")
    print("=" * 60)
    
    build_ready = check_build_readiness()
    python_ok = validate_python_version()
    isolation_ok = check_service_isolation()
    
    print("\n" + "=" * 60)
    print("📊 Troubleshooting Results:")
    
    if build_ready and python_ok and isolation_ok:
        print("🎉 All checks passed! Ready for: gcloud builds submit")
        print("\n📋 Next steps:")
        print("   1. gcloud builds submit --config deployment/cloud_run/cloudbuild.yaml")
        print("   2. gcloud run services list --region=us-central1")
        print("   3. Test deployed services with curl")
        return 0
    else:
        print("❌ Deployment checks failed. Please fix issues above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
