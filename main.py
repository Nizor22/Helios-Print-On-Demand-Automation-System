#!/usr/bin/env python3
"""
Helios Main Entry Point - Routes to appropriate service based on SERVICE_TYPE
"""

import os
import uvicorn
from helios.server_orchestrator import app as orchestrator_app
from helios.server_ai_agents import app as agents_app

def main():
    """Main entry point that routes to the appropriate service"""
    service_type = os.environ.get("SERVICE_TYPE", "orchestrator")
    
    if service_type == "ai_agents":
        print("🚀 Starting Helios AI Agents Service...")
        app = agents_app
    else:
        print("🎯 Starting Helios AI Orchestrator Service...")
        app = orchestrator_app
    
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")

if __name__ == "__main__":
    main()
