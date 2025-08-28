"""
Helios Unified Entry Point
Dynamically loads the appropriate FastAPI app based on SERVICE_TYPE environment variable.
This allows a single codebase to deploy as multiple Cloud Run services.
"""
import os
import logging
from fastapi import FastAPI

# Initialize logging early
try:
    from helios.logging_config import setup_logging
    logger = setup_logging("helios-main", "INFO")
except ImportError:
    # Fallback logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("helios-main")

def create_app() -> FastAPI:
    """Create the appropriate FastAPI application based on environment"""
    service_type = os.getenv("SERVICE_TYPE", "orchestrator").lower()
    
    logger.info(f"Initializing Helios application with SERVICE_TYPE: {service_type}")
    
    if service_type == "orchestrator":
        from helios.server_orchestrator.main import app
        logger.info("🚀 Starting Helios Orchestrator Service")
        return app
    elif service_type == "ai_agents":
        from helios.server_ai_agents.main import app
        logger.info("🤖 Starting Helios AI Agents Service")
        return app
    else:
        error_msg = f"Unknown SERVICE_TYPE: {service_type}. Use 'orchestrator' or 'ai_agents'"
        logger.error(error_msg)
        raise ValueError(error_msg)

# Create the application instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    logger.info(f"Starting Helios service on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
