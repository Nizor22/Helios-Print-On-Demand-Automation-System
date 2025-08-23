#!/usr/bin/env python3
"""
Dynamic startup script for Helios services.
Determines which service to run based on SERVICE_TYPE environment variable.
"""

import os
import sys

def main():
    """Main entry point that determines which service to start."""
    service_type = os.getenv('SERVICE_TYPE', 'orchestrator')
    
    if service_type == 'orchestrator':
        from helios.server_orchestrator import app
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=int(os.getenv('PORT', 8080)))
    elif service_type == 'ai_agents':
        from helios.server_ai_agents import app
        import uvicorn
        uvicorn.run(app, host="0.0.0.0", port=int(os.getenv('PORT', 8080)))
    else:
        print(f"Unknown SERVICE_TYPE: {service_type}")
        sys.exit(1)

if __name__ == "__main__":
    main()
