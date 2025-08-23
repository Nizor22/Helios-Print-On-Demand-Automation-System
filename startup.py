#!/usr/bin/env python3
"""
Dynamic startup script for Helios services
Determines which service to run based on SERVICE_TYPE environment variable
"""

import os
import sys
from pathlib import Path

def main():
    """Main entry point that determines which service to start"""
    # Add the current directory to Python path to ensure helios package is found
    current_dir = Path(__file__).parent
    sys.path.insert(0, str(current_dir))
    
    service_type = os.getenv('SERVICE_TYPE', 'orchestrator').lower()
    
    if service_type == 'orchestrator':
        # Import and run the orchestrator service
        from helios.server_orchestrator import app
        import uvicorn
        
        port = int(os.getenv('PORT', 8080))
        uvicorn.run(app, host='0.0.0.0', port=port)
        
    elif service_type == 'ai_agents':
        # Import and run the AI agents service
        from helios.server_ai_agents import app
        import uvicorn
        
        port = int(os.getenv('PORT', 8080))
        uvicorn.run(app, host='0.0.0.0', port=port)
        
    else:
        print(f"Unknown service type: {service_type}")
        print("Supported types: orchestrator, ai_agents")
        sys.exit(1)

if __name__ == "__main__":
    main()
