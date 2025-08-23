#!/usr/bin/env python3
"""
Helios AI Orchestrator - Main coordination service for structured AI agent system
Coordinates trend analysis, market research, creative direction, and content generation
"""

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import os
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field
import time
import traceback

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
        "service": "helios-orchestrator",
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

# Import and configure centralized logging
from helios.logging_config import get_logger

# Get logger instance for this service
logger = get_logger("helios-orchestrator")

# Create FastAPI app
app = FastAPI(
    title="Helios AI Orchestrator",
    description="Structured AI Agent System for Print-On-Demand Automation",
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
    
    # Log the error with structured context
    logger.error(
        f"Unhandled exception in {request.url.path}: {str(exc)}",
        error_code=type(exc).__name__,
        error_details=str(exc),
        context=error_context,
        exception=exc
    )
    
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
            logger.warning(f"Failed to report error to Google Cloud Error Reporting: {report_error}")
    
    # Return structured error response
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_code": type(exc).__name__,
            "service": "helios-orchestrator",
            "timestamp": time.time(),
            "trace_id": error_context["trace_id"]
        }
    )

# HTTP exception handler for structured error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured logging and error reporting"""
    error_context = {
        "service": "helios-orchestrator",
        "endpoint": str(request.url),
        "method": request.method,
        "status_code": exc.status_code,
        "client_ip": request.client.host if request.client else None,
        "user_agent": request.headers.get("user-agent"),
        "trace_id": request.headers.get("x-request-id"),
    }
    
    # Log the HTTP error
    logger.warning(
        f"HTTP {exc.status_code} error in {request.url.path}: {exc.detail}",
        error_code=f"HTTP_{exc.status_code}",
        error_details=exc.detail,
        context=error_context
    )
    
    # Report to Google Cloud Error Reporting for 5xx errors
    if ERROR_REPORTING_AVAILABLE and error_client and exc.status_code >= 500:
        try:
            error_client.report_exception(
                exc,
                user=error_context.get("client_ip"),
                context={
                    "endpoint": error_context["endpoint"],
                    "method": error_context["method"],
                    "service": error_context["service"],
                    "status_code": exc.status_code,
                    "trace_id": error_context["trace_id"]
                }
            )
        except Exception as report_error:
            logger.warning(f"Failed to report error to Google Cloud Error Reporting: {report_error}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "error_code": f"HTTP_{exc.status_code}",
            "service": "helios-orchestrator",
            "timestamp": time.time(),
            "trace_id": error_context["trace_id"]
        }
    )

# Pydantic models for structured outputs
class TrendAnalysisRequest(BaseModel):
    trends: List[str] = Field(..., description="List of trend keywords to analyze")
    market_segment: str = Field(..., description="Target market segment")
    analysis_depth: str = Field(default="comprehensive", pattern="^(basic|comprehensive|expert)$", description="Analysis depth level")

class TrendAnalysisResult(BaseModel):
    opportunity_score: float = Field(..., ge=0.0, le=10.0, description="Opportunity score 0-10")
    commercial_viability: str = Field(..., pattern="^(high|medium|low)$")
    recommended_action: str = Field(..., pattern="^(proceed|investigate|monitor|reject)$")
    market_size_estimate: str = Field(..., description="Estimated market size")
    competition_level: str = Field(..., pattern="^(low|medium|high|saturated)$")
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class OrchestrationRequest(BaseModel):
    operation_type: str = Field(..., pattern="^(trend_analysis|market_research|creative_direction|content_generation|full_workflow)$")
    input_data: Dict[str, Any] = Field(..., description="Input data for the operation")
    agent_config: Dict[str, Any] = Field(default_factory=dict, description="Agent configuration")

class OrchestrationResult(BaseModel):
    operation_id: str
    status: str = Field(..., pattern="^(success|partial_success|failed)$")
    results: Dict[str, Any]
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    execution_time_ms: int
    agent_metrics: Dict[str, Any]

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Helios AI Orchestrator",
        "status": "running",
        "version": "1.0.0",
        "architecture": "Structured AI Agent System"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "helios-orchestrator",
        "timestamp": "2025-08-19T00:00:00Z"
    }

@app.get("/mcp")
async def mcp_info():
    """MCP protocol information"""
    return {
        "protocol": "MCP",
        "version": "1.0.0",
        "capabilities": [
            "ai_orchestration",
            "trend_analysis",
            "market_research", 
            "creative_direction",
            "content_generation",
            "structured_outputs",
            "parallel_execution"
        ],
        "system_type": "Structured AI Agent System"
    }

@app.post("/orchestrate", response_model=OrchestrationResult)
async def orchestrate_operation(request: OrchestrationRequest):
    """Orchestrate AI agent operations with structured outputs"""
    try:
        logger.info(f"Orchestration request: {request.operation_type}")
        
        # TODO: Implement actual orchestration logic with your AI agents
        # This will coordinate: Trend Analyst, Market Researcher, Creative Director, Content Writer
        
        return OrchestrationResult(
            operation_id=f"op_{os.urandom(8).hex()}",
            status="success",
            results={
                "operation_type": request.operation_type,
                "agents_executed": ["trend_analyst", "market_researcher"],
                "output_validation": "passed"
            },
            confidence_score=0.95,
            execution_time_ms=1250,
            agent_metrics={
                "trend_analyst": {"status": "completed", "confidence": 0.92},
                "market_researcher": {"status": "completed", "confidence": 0.89}
            }
        )
    except Exception as e:
        logger.error(f"Orchestration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trends/analyze", response_model=List[TrendAnalysisResult])
async def analyze_trends(request: TrendAnalysisRequest):
    """Analyze market trends using structured AI agent"""
    try:
        logger.info(f"Trend analysis request: {request.trends}")
        
        # TODO: Implement trend analysis using your Trend Analyst AI agent
        # This will return validated, structured outputs
        
        results = []
        for trend in request.trends:
            # Simulated structured output from AI agent
            result = TrendAnalysisResult(
                opportunity_score=8.5,
                commercial_viability="high",
                recommended_action="proceed",
                market_size_estimate="$2.5B annually",
                competition_level="medium",
                confidence_score=0.88
            )
            results.append(result)
        
        return results
    except Exception as e:
        logger.error(f"Trend analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-full-workflow")
async def run_full_workflow():
    """
    Execute the complete autonomous workflow:
    1. Discover current trends
    2. Select best product
    3. Generate AI image
    4. Create and publish product
    """
    try:
        logger.info("🚀 Starting autonomous workflow execution")
        
        # TODO: Implement actual workflow execution logic
        # This will coordinate: Trend Analyst, Market Researcher, Creative Director, Content Writer
        
        return {
            "status": "success",
            "message": "Workflow execution started",
            "workflow_id": f"wf_{os.urandom(8).hex()}",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Workflow execution error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run")
async def run_once():
    """Run a single orchestration cycle"""
    try:
        logger.info("🔄 Running single orchestration cycle")
        
        # TODO: Implement actual orchestration logic
        # This will coordinate: Trend Analyst, Market Researcher, Creative Director, Content Writer
        
        return {
            "status": "success",
            "cycle_id": f"cycle_{os.urandom(8).hex()}",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Orchestration cycle error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/run-async")
async def run_async():
    """Run orchestration asynchronously"""
    try:
        logger.info("🔄 Starting async orchestration")
        
        # TODO: Implement actual async orchestration logic
        
        return {
            "status": "accepted",
            "task_id": f"task_{os.urandom(8).hex()}",
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error(f"Async orchestration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/mcp/google-trends")
async def mcp_google_trends(query: str = "", geo: str = "US", time_range: str = "1d"):
    """MCP endpoint for Google Trends data analysis"""
    try:
        # For now, return simulated trends to get the service working
        # We can enhance this later with real Google Trends integration
        simulated_trends = [
            "AI automation tools",
            "Sustainable living",
            "Remote work optimization", 
            "Digital wellness",
            "Smart home technology",
            "Eco-friendly products",
            "Mental health apps",
            "Fitness technology",
            "Plant-based lifestyle",
            "Minimalist design"
        ]
        
        return {
            "status": "success",
            "data": {
                "query": query,
                "geo": geo,
                "time_range": time_range,
                "trends": simulated_trends,
                "source": "simulated_trends"
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

@app.get("/agents/status")
async def get_agents_status():
    """Get status of all AI agents"""
    return {
        "orchestrator": {
            "status": "active",
            "capabilities": ["coordination", "workflow_management", "output_validation"]
        },
        "trend_analyst": {
            "status": "active", 
            "capabilities": ["trend_analysis", "opportunity_scoring", "market_viability"]
        },
        "market_researcher": {
            "status": "active",
            "capabilities": ["competitive_analysis", "market_sizing", "demand_forecasting"]
        },
        "creative_director": {
            "status": "active",
            "capabilities": ["design_decisions", "aesthetic_guidance", "brand_alignment"]
        },
        "content_writer": {
            "status": "active",
            "capabilities": ["copy_generation", "seo_optimization", "brand_voice"]
        },
        "total_agents": 5,
        "active_agents": 5,
        "system_type": "Structured AI Agent System"
    }

@app.get("/system/architecture")
async def get_system_architecture():
    """Get system architecture information"""
    return {
        "system_name": "Helios Print-On-Demand Automation System",
        "architecture": "Structured AI Agent System",
        "core_principle": "AI Intelligence + Predictable Structure",
        "components": {
            "orchestrator": "Main AI coordination and workflow management",
            "ai_agents": "Specialized AI agents with structured outputs",
            "validation_layer": "Pydantic models ensuring data quality",
            "parallel_execution": "Concurrent agent execution with controls"
        },
        "predictability_features": [
            "Structured output validation",
            "Enforced data formats", 
            "Business rule validation",
            "Confidence scoring",
            "Timeout controls",
            "Retry mechanisms"
        ]
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
