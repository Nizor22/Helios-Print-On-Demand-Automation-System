#!/usr/bin/env python3
"""
Test script to verify all imports work correctly
"""
import sys
import os
import traceback

# Add workspace to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test all critical imports"""
    failed_imports = []
    successful_imports = []
    
    imports_to_test = [
        ("FastAPI", "from fastapi import FastAPI"),
        ("Uvicorn", "import uvicorn"),
        ("Pydantic", "from pydantic import BaseModel"),
        ("Orchestrator App", "from helios.server_orchestrator import app as orchestrator_app"),
        ("AI Agents App", "from helios.server_ai_agents import app as agents_app"),
        ("Main Entry", "from main import main"),
        ("Config", "from helios.config import HeliosConfig"),
        ("Google Cloud Firestore", "from google.cloud import firestore"),
        ("Google Cloud Storage", "from google.cloud import storage"),
        ("Vertex AI", "from google.cloud import aiplatform"),
        ("Loguru", "from loguru import logger"),
        ("Dotenv", "from dotenv import load_dotenv"),
    ]
    
    print("Testing imports...")
    print("=" * 60)
    
    for name, import_statement in imports_to_test:
        try:
            exec(import_statement)
            successful_imports.append(name)
            print(f"✅ {name}: SUCCESS")
        except Exception as e:
            failed_imports.append((name, str(e)))
            print(f"❌ {name}: FAILED - {type(e).__name__}: {str(e)}")
    
    print("=" * 60)
    print(f"\nSummary:")
    print(f"✅ Successful: {len(successful_imports)}")
    print(f"❌ Failed: {len(failed_imports)}")
    
    if failed_imports:
        print("\nFailed imports details:")
        for name, error in failed_imports:
            print(f"  - {name}: {error}")
    
    return len(failed_imports) == 0

if __name__ == "__main__":
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Python path: {sys.path}\n")
    
    success = test_imports()
    sys.exit(0 if success else 1)