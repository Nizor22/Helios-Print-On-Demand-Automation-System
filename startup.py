#!/usr/bin/env python3
"""
Unified startup script for Helios services
Routes to the appropriate service based on SERVICE_TYPE environment variable
"""

import os
import sys
from pathlib import Path

# Add the current directory to Python path to ensure helios package is accessible
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Main entry point that routes to the appropriate service"""
    service_type = os.getenv('SERVICE_TYPE', 'orchestrator').lower()
    
    if service_type == 'orchestrator':
        from helios.server_orchestrator import app
        return app
    elif service_type == 'ai_agents':
        from helios.server_ai_agents import app
        return app
    else:
        raise ValueError(f"Unknown SERVICE_TYPE: {service_type}")

# Create the app instance
app = main()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8080))
    uvicorn.run(app, host='0.0.0.0', port=port)
