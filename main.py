#!/usr/bin/env python3
"""
Unified entry point for Helios services.
Dynamically creates the appropriate FastAPI application based on SERVICE_TYPE environment variable.
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def create_app() -> FastAPI:
    """Create the FastAPI application with the appropriate components."""
    service_type = os.getenv('SERVICE_TYPE', 'orchestrator')
    
    # Create the base FastAPI app
    app = FastAPI(
        title=f"Helios {service_type.replace('_', ' ').title()}",
        description=f"Helios AI Automation System - {service_type.replace('_', ' ').title()} Service",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Import and include the appropriate routers based on service type
    if service_type == 'orchestrator':
        from helios.server_orchestrator import app as orchestrator_app
        # Copy all routes from the orchestrator app
        for route in orchestrator_app.routes:
            app.router.routes.append(route)
            
    elif service_type == 'ai_agents':
        from helios.server_ai_agents import app as agents_app
        # Copy all routes from the agents app
        for route in agents_app.routes:
            app.router.routes.append(route)
            
    else:
        # Fallback: create a basic health check endpoint
        @app.get("/")
        async def root():
            return {"message": f"Helios {service_type} service is running", "status": "unknown_service_type"}
        
        @app.get("/health")
        async def health_check():
            return {"status": "healthy", "service_type": service_type}
    
    return app

# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8080))
    uvicorn.run(app, host='0.0.0.0', port=port)
