#!/usr/bin/env python3
"""
Deployment debugging script to identify issues before pushing to Google Cloud
"""
import subprocess
import sys
import os
import json

def run_command(cmd, description):
    """Run a command and capture output"""
    print(f"\n🔍 {description}")
    print(f"   Command: {cmd}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(f"STDERR: {result.stderr}")
        return result.returncode == 0
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def main():
    """Run deployment debugging checks"""
    print("🚀 Helios Deployment Debugging")
    print("=" * 60)
    
    checks = [
        ("Python Version", "python3 --version"),
        ("Current Directory", "pwd"),
        ("Directory Structure", "ls -la"),
        ("Helios Package Structure", "ls -la helios/"),
        ("Check imports", "python3 test_imports.py"),
        ("Validate requirements.txt", "python3 -m pip check"),
        ("Test orchestrator startup", "timeout 5 python3 start_orchestrator.py || echo 'Timeout reached (expected)'"),
        ("Test AI agents startup", "timeout 5 python3 start_ai_agents.py || echo 'Timeout reached (expected)'"),
        ("Check for syntax errors", "python3 -m py_compile helios/server_orchestrator.py helios/server_ai_agents.py"),
        ("Verify runtime.txt", "cat runtime.txt"),
        ("Check Procfile", "cat Procfile"),
        ("Check Procfile.agents", "cat Procfile.agents"),
    ]
    
    failed_checks = []
    
    for description, cmd in checks:
        success = run_command(cmd, description)
        if not success and "timeout" not in cmd:  # Timeout is expected for server startups
            failed_checks.append(description)
    
    print("\n" + "=" * 60)
    print("📊 Summary:")
    print(f"   Total checks: {len(checks)}")
    print(f"   Failed checks: {len(failed_checks)}")
    
    if failed_checks:
        print("\n❌ Failed checks:")
        for check in failed_checks:
            print(f"   - {check}")
    else:
        print("\n✅ All checks passed!")
    
    # Additional deployment tips
    print("\n💡 Deployment Tips:")
    print("1. Ensure you're on the main branch before deploying")
    print("2. Run 'git status' to check for uncommitted changes")
    print("3. Use 'gcloud run services logs' to check deployment logs")
    print("4. Verify all environment variables are set in Cloud Run")
    print("5. Check that all secrets are properly configured in Secret Manager")
    
    return len(failed_checks) == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)