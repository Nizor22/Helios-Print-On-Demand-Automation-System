#!/usr/bin/env python3
"""
Unified Helios application that serves both orchestrator and AI agents services
based on the SERVICE_TYPE environment variable
"""

import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

# Import both services
from helios.server_orchestrator import app as orchestrator_app
from helios.server_ai_agents import app as agents_app

# Create the main app
app = FastAPI(title="Helios Unified Service", version="1.0.0")

# Get service type from environment
SERVICE_TYPE = os.getenv('SERVICE_TYPE', 'orchestrator').lower()

# Mount the appropriate service based on SERVICE_TYPE
if SERVICE_TYPE == 'orchestrator':
    app.mount("/", orchestrator_app)
elif SERVICE_TYPE == 'ai_agents':
    app.mount("/", agents_app)
else:
    @app.get("/")
    async def root():
        return {"error": f"Unknown service type: {SERVICE_TYPE}. Supported types: orchestrator, ai_agents"}

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service_type": SERVICE_TYPE,
        "message": f"Helios {SERVICE_TYPE} service is running"
    }

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    uvicorn.run(app, host='0.0.0.0', port=port)
