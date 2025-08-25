#!/usr/bin/env python3
"""
Entry point for Helios AI Agents Service
Run with: python3 run_ai_agents.py
"""

import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from helios.server_ai_agents import app
    import uvicorn
    
    if __name__ == "__main__":
        print("🤖 Starting Helios AI Agents Service...")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8081,  # Different port to avoid conflicts
            log_level="info"
        )
        
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you're running from the project root directory")
    print("💡 Try: pip install -e .")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error starting service: {e}")
    sys.exit(1)
