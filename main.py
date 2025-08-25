"""
Helios Unified Entry Point
Dynamically loads the appropriate FastAPI app based on SERVICE_TYPE environment variable.
This allows a single codebase to deploy as multiple Cloud Run services.
"""
import os
from fastapi import FastAPI

def create_app() -> FastAPI:
    """Create the appropriate FastAPI application based on environment"""
    service_type = os.getenv("SERVICE_TYPE", "orchestrator").lower()
    
    if service_type == "orchestrator":
        from helios.server_orchestrator.main import app
        print(f"🚀 Starting Helios Orchestrator Service")
        return app
    elif service_type == "ai_agents":
        from helios.server_ai_agents.main import app
        print(f"🤖 Starting Helios AI Agents Service")
        return app
    else:
        raise ValueError(f"Unknown SERVICE_TYPE: {service_type}. Use 'orchestrator' or 'ai_agents'")

# Create the application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
