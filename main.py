#!/usr/bin/env python3
"""
Unified entry point for Helios services.
Dynamically creates the appropriate FastAPI application based on SERVICE_TYPE environment variable.
"""

import os
import time
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# Google Cloud Error Reporting
try:
    from google.cloud import error_reporting
    error_client = error_reporting.Client()
    ERROR_REPORTING_AVAILABLE = True
except ImportError:
    error_client = None
    ERROR_REPORTING_AVAILABLE = False

def get_error_context(request: Request, exc: Exception, additional_context: dict = None) -> dict:
    """Generate comprehensive error context for reporting and logging"""
    context = {
        "service": f"helios-{os.getenv('SERVICE_TYPE', 'unknown')}",
        "endpoint": str(request.url),
        "method": request.method,
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "trace_id": request.headers.get("x-request-id"),
        "error_type": type(exc).__name__,
        "error_message": str(exc),
        "timestamp": time.time(),
    }
    
    if additional_context:
        context.update(additional_context)
    
    return context

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
    
    # Global exception handler for unhandled errors
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Global exception handler that reports errors to Google Cloud Error Reporting"""
        error_context = get_error_context(request, exc)
        
        # Report to Google Cloud Error Reporting if available
        if ERROR_REPORTING_AVAILABLE and error_client:
            try:
                error_client.report_exception(
                    exc,
                    user=error_context.get("client_ip"),
                    context={
                        "endpoint": error_context["endpoint"],
                        "method": error_context["method"],
                        "service": error_context["service"],
                        "trace_id": error_context["trace_id"],
                        "error_type": error_context["error_type"],
                        "timestamp": error_context["timestamp"]
                    }
                )
            except Exception as report_error:
                # Log the reporting failure but don't fail the error handler
                print(f"Failed to report error to Google Cloud Error Reporting: {report_error}")
        
        # Return structured error response
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal server error",
                "error_type": error_context["error_type"],
                "trace_id": error_context["trace_id"],
                "timestamp": error_context["timestamp"]
            }
        )
    
    # Import and mount the appropriate service based on SERVICE_TYPE
    if service_type == 'orchestrator':
        from helios.server_orchestrator import app as orchestrator_app
        app.mount("/", orchestrator_app)
        
    elif service_type == 'ai_agents':
        from helios.server_ai_agents import app as agents_app
        app.mount("/", agents_app)
        
    else:
        # This fallback is only for an unrecognized service type
        @app.get("/health")
        async def health_check():
            return {"status": "healthy", "service_type": "invalid"}

    return app

# Create the app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8080))
    uvicorn.run(app, host='0.0.0.0', port=port)
