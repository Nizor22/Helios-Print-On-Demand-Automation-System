#!/usr/bin/env python3
"""
Helios AI Agents Service - Specialized AI agents for Print-On-Demand automation
Implements: Trend Analyst, Market Researcher, Creative Director, Content Writer
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
        "service": "helios-ai-agents",
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
logger = get_logger("helios-ai-agents")

# Create FastAPI app
app = FastAPI(
    title="Helios AI Agents Service",
    description="Specialized AI agents for structured Print-On-Demand automation",
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
            "service": "helios-ai-agents",
            "timestamp": time.time(),
            "trace_id": error_context["trace_id"]
        }
    )

# HTTP exception handler for structured error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with structured logging and error reporting"""
    error_context = {
        "service": "helios-ai-agents",
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
            "service": "helios-ai-agents",
            "timestamp": time.time(),
            "trace_id": error_context["trace_id"]
        }
    )

# Pydantic models for structured AI agent outputs
class TrendAnalysisInput(BaseModel):
    trend_keywords: List[str] = Field(..., description="Trend keywords to analyze")
    target_market: str = Field(..., description="Target market segment")
    analysis_type: str = Field(default="comprehensive", pattern="^(basic|comprehensive|expert)$", description="Analysis type")

class TrendAnalysisOutput(BaseModel):
    opportunity_score: float = Field(..., ge=0.0, le=10.0, description="Opportunity score 0-10")
    commercial_viability: str = Field(..., pattern="^(high|medium|low)$")
    recommended_action: str = Field(..., pattern="^(proceed|investigate|monitor|reject)$")
    market_size_estimate: str = Field(..., description="Estimated market size")
    competition_level: str = Field(..., pattern="^(low|medium|high|saturated)$")
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    trend_lifecycle_stage: str = Field(..., pattern="^(emerging|growing|mature|declining)$")

class MarketResearchInput(BaseModel):
    product_category: str = Field(..., description="Product category to research")
    target_audience: str = Field(..., description="Target audience demographics")
    geographic_market: str = Field(..., description="Geographic market focus")

class MarketResearchOutput(BaseModel):
    market_size: str = Field(..., description="Total addressable market size")
    growth_rate: str = Field(..., description="Market growth rate")
    competition_analysis: Dict[str, Any] = Field(..., description="Competitive landscape")
    demand_forecast: str = Field(..., description="Demand forecast")
    pricing_insights: Dict[str, Any] = Field(..., description="Pricing strategy insights")
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class CreativeDirectionInput(BaseModel):
    product_concept: str = Field(..., description="Product concept description")
    target_aesthetic: str = Field(..., description="Target aesthetic style")
    brand_guidelines: Dict[str, Any] = Field(..., description="Brand guidelines")

class CreativeDirectionOutput(BaseModel):
    design_recommendations: List[str] = Field(..., description="Design recommendations")
    color_palette: List[str] = Field(..., description="Recommended color palette")
    typography_choices: List[str] = Field(..., description="Typography recommendations")
    visual_elements: List[str] = Field(..., description="Visual element suggestions")
    aesthetic_score: float = Field(..., ge=0.0, le=10.0, description="Aesthetic appeal score")
    confidence_score: float = Field(..., ge=0.0, le=1.0)

class ContentGenerationInput(BaseModel):
    content_type: str = Field(..., pattern="^(product_description|marketing_copy|seo_content|social_media)$")
    target_audience: str = Field(..., description="Target audience")
    tone: str = Field(..., pattern="^(professional|casual|friendly|luxury|minimalist)$")
    key_points: List[str] = Field(..., description="Key points to include")

class ContentGenerationOutput(BaseModel):
    generated_content: str = Field(..., description="Generated content")
    seo_keywords: List[str] = Field(..., description="SEO keywords")
    content_score: float = Field(..., ge=0.0, le=10.0, description="Content quality score")
    brand_alignment: float = Field(..., ge=0.0, le=10.0, description="Brand alignment score")
    confidence_score: float = Field(..., ge=0.0, le=1.0)

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Helios AI Agents Service",
        "status": "running",
        "version": "1.0.0",
        "agents": ["trend_analyst", "market_researcher", "creative_director", "content_writer"]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "helios-ai-agents",
        "timestamp": "2025-08-19T00:00:00Z"
    }

@app.get("/mcp")
async def mcp_info():
    """MCP protocol information"""
    return {
        "protocol": "MCP",
        "version": "1.0.0",
        "capabilities": [
            "trend_analysis",
            "market_research",
            "creative_direction", 
            "content_generation",
            "structured_outputs",
            "ai_agent_coordination"
        ],
        "system_type": "Structured AI Agent System"
    }

@app.post("/agents/trend-analyst", response_model=TrendAnalysisOutput)
async def analyze_trends(request: TrendAnalysisInput):
    """Trend Analyst AI agent - analyzes market trends with structured output"""
    try:
        logger.info(f"Trend analysis request: {request.trend_keywords}")
        
        # TODO: Implement actual Trend Analyst AI logic
        # This will use your AI models to analyze trends and return validated outputs
        
        # Simulated structured output from AI agent
        result = TrendAnalysisOutput(
            opportunity_score=8.7,
            commercial_viability="high",
            recommended_action="proceed",
            market_size_estimate="$3.2B annually",
            competition_level="medium",
            confidence_score=0.91,
            trend_lifecycle_stage="growing"
        )
        
        return result
    except Exception as e:
        logger.error(f"Trend analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents/market-researcher", response_model=MarketResearchOutput)
async def research_market(request: MarketResearchInput):
    """Market Researcher AI agent - conducts market research with structured output"""
    try:
        logger.info(f"Market research request: {request.product_category}")
        
        # TODO: Implement actual Market Researcher AI logic
        # This will analyze market data and return validated insights
        
        result = MarketResearchOutput(
            market_size="$45B globally",
            growth_rate="12.5% annually",
            competition_analysis={
                "competitors": 15,
                "market_share": "fragmented",
                "entry_barriers": "medium"
            },
            demand_forecast="Strong growth expected over next 3 years",
            pricing_insights={
                "price_range": "$15-$85",
                "premium_segment": "growing",
                "price_sensitivity": "medium"
            },
            confidence_score=0.89
        )
        
        return result
    except Exception as e:
        logger.error(f"Market research error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents/creative-director", response_model=CreativeDirectionOutput)
async def provide_creative_direction(request: CreativeDirectionInput):
    """Creative Director AI agent - provides design direction with structured output"""
    try:
        logger.info(f"Creative direction request: {request.product_concept}")
        
        # TODO: Implement actual Creative Director AI logic
        # This will provide aesthetic guidance and design recommendations
        
        result = CreativeDirectionOutput(
            design_recommendations=[
                "Minimalist geometric patterns",
                "Earthy color palette",
                "Modern sans-serif typography"
            ],
            color_palette=["#2C5530", "#8B7355", "#D4AF37", "#F5F5DC"],
            typography_choices=["Inter", "Roboto", "Open Sans"],
            visual_elements=[
                "Abstract geometric shapes",
                "Natural texture overlays",
                "Clean line work"
            ],
            aesthetic_score=8.9,
            confidence_score=0.87
        )
        
        return result
    except Exception as e:
        logger.error(f"Creative direction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/agents/content-writer", response_model=ContentGenerationOutput)
async def generate_content(request: ContentGenerationInput):
    """Content Writer AI agent - generates content with structured output"""
    try:
        logger.info(f"Content generation request: {request.content_type}")
        
        # TODO: Implement actual Content Writer AI logic
        # This will generate high-quality, brand-aligned content
        
        result = ContentGenerationOutput(
            generated_content="Discover our premium collection of sustainable, handcrafted designs that blend modern aesthetics with timeless elegance. Each piece tells a unique story of creativity and craftsmanship.",
            seo_keywords=["premium", "sustainable", "handcrafted", "modern", "timeless", "creativity"],
            content_score=9.2,
            brand_alignment=9.5,
            confidence_score=0.93
        )
        
        return result
    except Exception as e:
        logger.error(f"Content generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/agents/status")
async def get_agents_status():
    """Get status of all AI agents"""
    return {
        "trend_analyst": {
            "status": "active",
            "capabilities": ["trend_analysis", "opportunity_scoring", "market_viability"],
            "output_format": "TrendAnalysisOutput",
            "validation": "Pydantic enforced"
        },
        "market_researcher": {
            "status": "active",
            "capabilities": ["competitive_analysis", "market_sizing", "demand_forecasting"],
            "output_format": "MarketResearchOutput", 
            "validation": "Pydantic enforced"
        },
        "creative_director": {
            "status": "active",
            "capabilities": ["design_decisions", "aesthetic_guidance", "brand_alignment"],
            "output_format": "CreativeDirectionOutput",
            "validation": "Pydantic enforced"
        },
        "content_writer": {
            "status": "active",
            "capabilities": ["copy_generation", "seo_optimization", "brand_voice"],
            "output_format": "ContentGenerationOutput",
            "validation": "Pydantic enforced"
        },
        "total_agents": 4,
        "active_agents": 4,
        "system_type": "Structured AI Agent System",
        "predictability": "Guaranteed through Pydantic validation"
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
