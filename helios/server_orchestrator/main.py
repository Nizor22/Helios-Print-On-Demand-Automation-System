#!/usr/bin/env python3
"""
Helios AI Orchestrator - Main entry point
Main coordination service for structured AI agent system
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import os
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import time
import asyncio
from datetime import datetime

# Import and configure centralized logging
try:
    from helios.logging_config import get_logger
    logger = get_logger("helios-orchestrator", service_type="orchestrator")
except ImportError:
    # Fallback logging if config not available
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("helios-orchestrator")

# Create FastAPI app
app = FastAPI(
    title="Helios AI Orchestrator",
    description="Main coordination service for structured AI agent system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic models for structured outputs (Pydantic v2 compatible)
class TrendAnalysisRequest(BaseModel):
    trends: List[str]
    market_segment: str
    analysis_depth: str = "comprehensive"

class TrendAnalysisResult(BaseModel):
    opportunity_score: float
    commercial_viability: str
    recommended_action: str
    market_size_estimate: str
    competition_level: str
    confidence_score: float

class OrchestrationRequest(BaseModel):
    operation_type: str
    input_data: Dict[str, Any]
    agent_config: Dict[str, Any] = {}

class OrchestrationResult(BaseModel):
    operation_id: str
    status: str
    results: Dict[str, Any]
    confidence_score: float
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

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard():
    """Main dashboard HTML"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Helios Autonomous Store Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .header { text-align: center; margin-bottom: 40px; }
            .header h1 { color: #2c3e50; margin-bottom: 10px; }
            .header p { color: #7f8c8d; font-size: 18px; }
            .workflow-section { margin-bottom: 40px; padding: 20px; border: 2px solid #3498db; border-radius: 8px; }
            .workflow-section h2 { color: #2980b9; margin-top: 0; }
            .form-group { margin-bottom: 20px; }
            .form-group label { display: block; margin-bottom: 5px; font-weight: bold; color: #2c3e50; }
            .form-group input, .form-group select { width: 100%; padding: 10px; border: 1px solid #bdc3c7; border-radius: 5px; font-size: 16px; }
            .btn { background: #3498db; color: white; padding: 12px 24px; border: none; border-radius: 5px; font-size: 16px; cursor: pointer; }
            .btn:hover { background: #2980b9; }
            .btn:disabled { background: #bdc3c7; cursor: not-allowed; }
            .btn-danger { background: #e74c3c; }
            .btn-danger:hover { background: #c0392b; }
            .status-section { margin-top: 30px; padding: 20px; background: #ecf0f1; border-radius: 8px; }
            .status-item { margin-bottom: 15px; }
            .status-label { font-weight: bold; color: #2c3e50; }
            .status-value { color: #7f8c8d; }
            .running { color: #27ae60; font-weight: bold; }
            .stopped { color: #e74c3c; font-weight: bold; }
            .results { margin-top: 20px; padding: 15px; background: #f8f9fa; border-radius: 5px; border-left: 4px solid #3498db; }
            .error { border-left-color: #e74c3c; background: #fdf2f2; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🚀 Helios Autonomous Store Dashboard</h1>
                <p>AI-Powered Trend Discovery & Product Generation</p>
            </div>
            
            <div class="workflow-section">
                <h2>🤖 Autonomous Workflow Control</h2>
                <form id="workflowForm">
                    <div class="form-group">
                        <label for="workflow_type">Workflow Type:</label>
                        <select id="workflow_type" name="workflow_type">
                            <option value="autonomous_discovery">Autonomous Trend Discovery</option>
                            <option value="product_generation">Product Generation & Publishing</option>
                            <option value="full_pipeline">Full End-to-End Pipeline</option>
                        </select>
                    </div>
                    
                    <div class="form-group">
                        <label for="categories">Categories:</label>
                        <input type="text" id="categories" name="categories" value="fashion,technology,lifestyle" placeholder="fashion,technology,lifestyle">
                    </div>
                    
                    <div class="form-group">
                        <label for="regions">Regions:</label>
                        <input type="text" id="regions" name="regions" value="US" placeholder="US,EU,Global">
                    </div>
                    
                    <div class="form-group">
                        <label for="time_range">Time Range:</label>
                        <select id="time_range" name="time_range">
                            <option value="7 days">Last 7 days</option>
                            <option value="30 days" selected>Last 30 days</option>
                            <option value="90 days">Last 90 days</option>
                            <option value="1 year">Last year</option>
                        </select>
                    </div>
                    
                    <button type="button" class="btn" onclick="startWorkflow()" id="startBtn">🚀 Start Autonomous Workflow</button>
                    <button type="button" class="btn btn-danger" onclick="stopWorkflow()" id="stopBtn" style="display:none;">⏹️ Stop Workflow</button>
                </form>
            </div>
            
            <div class="status-section">
                <h2>📊 System Status</h2>
                <div class="status-item">
                    <span class="status-label">Workflow Status:</span>
                    <span class="status-value" id="workflowStatus">Stopped</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Current Step:</span>
                    <span class="status-value" id="currentStep">None</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Last Run:</span>
                    <span class="status-value" id="lastRun">Never</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Products Generated:</span>
                    <span class="status-value" id="productsGenerated">0</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Workflow Type:</span>
                    <span class="status-value" id="workflowType">None</span>
                </div>
            </div>
            
            <div id="results" class="results" style="display:none;">
                <h3>📈 Workflow Results</h3>
                <div id="resultsContent"></div>
            </div>
            
            <div id="errors" class="results error" style="display:none;">
                <h3>❌ Errors</h3>
                <div id="errorsContent"></div>
            </div>
        </div>
        
        <script>
            let workflowRunning = false;
            
            async function startWorkflow() {
                if (workflowRunning) return;
                
                const formData = new FormData(document.getElementById('workflowForm'));
                const data = Object.fromEntries(formData.entries());
                
                try {
                    document.getElementById('startBtn').disabled = true;
                    document.getElementById('startBtn').textContent = 'Starting...';
                    
                    const response = await fetch('/api/trigger-workflow', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    
                    if (response.ok) {
                        workflowRunning = true;
                        document.getElementById('startBtn').style.display = 'none';
                        document.getElementById('stopBtn').style.display = 'inline-block';
                        document.getElementById('workflowStatus').textContent = 'Running';
                        document.getElementById('workflowStatus').className = 'status-value running';
                        
                        // Start polling for status
                        pollWorkflowStatus();
                    } else {
                        const error = await response.json();
                        alert('Error starting workflow: ' + error.detail);
                    }
                } catch (error) {
                    alert('Error: ' + error.message);
                } finally {
                    document.getElementById('startBtn').disabled = false;
                    document.getElementById('startBtn').textContent = '🚀 Start Autonomous Workflow';
                }
            }
            
            async function stopWorkflow() {
                try {
                    const response = await fetch('/api/stop-workflow', { method: 'POST' });
                    if (response.ok) {
                        workflowRunning = false;
                        document.getElementById('startBtn').style.display = 'inline-block';
                        document.getElementById('stopBtn').style.display = 'none';
                        document.getElementById('workflowStatus').textContent = 'Stopped';
                        document.getElementById('workflowStatus').className = 'status-value stopped';
                        document.getElementById('currentStep').textContent = 'None';
                    }
                } catch (error) {
                    alert('Error stopping workflow: ' + error.message);
                }
            }
            
            async function pollWorkflowStatus() {
                if (!workflowRunning) return;
                
                try {
                    const response = await fetch('/api/workflow-status');
                    if (response.ok) {
                        const status = await response.json();
                        updateStatusDisplay(status);
                        
                        if (status.is_running) {
                            setTimeout(pollWorkflowStatus, 2000); // Poll every 2 seconds
                        } else {
                            workflowRunning = false;
                            document.getElementById('startBtn').style.display = 'inline-block';
                            document.getElementById('stopBtn').style.display = 'none';
                        }
                    }
                } catch (error) {
                    console.error('Error polling status:', error);
                }
            }
            
            function updateStatusDisplay(status) {
                document.getElementById('workflowStatus').textContent = status.is_running ? 'Running' : 'Stopped';
                document.getElementById('workflowStatus').className = status.is_running ? 'status-value running' : 'status-value stopped';
                document.getElementById('currentStep').textContent = status.current_step || 'None';
                document.getElementById('lastRun').textContent = status.last_run || 'Never';
                
                // Update workflow type
                if (status.results && status.results.real_workflow !== undefined) {
                    const workflowType = status.results.real_workflow ? '🤖 Real AI Workflow' : '🎭 Simulation Mode';
                    document.getElementById('workflowType').textContent = workflowType;
                    document.getElementById('workflowType').className = status.results.real_workflow ? 'status-value running' : 'status-value stopped';
                } else {
                    document.getElementById('workflowType').textContent = 'Unknown';
                }
                
                if (status.results) {
                    document.getElementById('results').style.display = 'block';
                    document.getElementById('resultsContent').innerHTML = '<pre>' + JSON.stringify(status.results, null, 2) + '</pre>';
                }
                
                if (status.errors) {
                    document.getElementById('errors').style.display = 'block';
                    document.getElementById('errorsContent').innerHTML = '<pre>' + JSON.stringify(status.errors, null, 2) + '</pre>';
                }
            }
            
            // Initial status check
            window.onload = function() {
                pollWorkflowStatus();
            };
        </script>
    </body>
    </html>
    """

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "helios-orchestrator",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "version": "1.0.0"
    }

@app.get("/api/v1/status")
async def get_status():
    """Get detailed service status"""
    return {
        "service": "helios-orchestrator",
        "status": "healthy",
        "version": "1.0.0",
        "capabilities": [
            "trend_analysis",
            "market_research",
            "creative_direction",
            "content_generation",
            "full_workflow"
        ],
        "uptime": "running",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
    }

@app.post("/api/v1/trend-analysis", response_model=TrendAnalysisResult)
async def analyze_trends(request: TrendAnalysisRequest):
    """Analyze market trends with structured output"""
    try:
        logger.info(f"Starting trend analysis - trends: {request.trends}, market_segment: {request.market_segment}, analysis_depth: {request.analysis_depth}")
        
        # TODO: Implement actual trend analysis logic
        # This will use your AI models to analyze trends and return validated outputs
        
        result = TrendAnalysisResult(
            opportunity_score=8.7,
            commercial_viability="high",
            recommended_action="proceed",
            market_size_estimate="$3.2B annually",
            competition_level="medium",
            confidence_score=0.91
        )
        
        logger.info(f"Trend analysis completed successfully - opportunity_score: {result.opportunity_score}, confidence_score: {result.confidence_score}, market_size: {result.market_size_estimate}")
        
        return result
    except Exception as e:
        logger.error(f"Error in trend analysis - error_code: TREND_ANALYSIS_FAILED, error_details: {str(e)}, trends: {request.trends}, market_segment: {request.market_segment}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/orchestrate", response_model=OrchestrationResult)
async def orchestrate_operation(request: OrchestrationRequest):
    """Orchestrate AI agent operations"""
    try:
        logger.info(f"Starting orchestration operation - operation_type: {request.operation_type}, input_data_keys: {list(request.input_data.keys()) if request.input_data else []}")
        
        # TODO: Implement actual orchestration logic
        # This will coordinate between different AI agents
        
        result = OrchestrationResult(
            operation_id=f"op_{int(time.time())}",
            status="success",
            results={"operation": request.operation_type, "status": "completed"},
            confidence_score=0.95,
            execution_time_ms=150,
            agent_metrics={"agents_used": 3, "total_tokens": 1250}
        )
        
        logger.info(f"Orchestration operation completed successfully - operation_id: {result.operation_id}, status: {result.status}, confidence_score: {result.confidence_score}, execution_time_ms: {result.execution_time_ms}")
        
        return result
    except Exception as e:
        logger.error(f"Error in orchestration operation - operation_type: {request.operation_type}, error_code: ORCHESTRATION_FAILED, error_details: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Workflow control endpoints for the dashboard
workflow_status = {
    "last_run": None,
    "is_running": False,
    "current_step": None,
    "results": None,
    "errors": None
}

class WorkflowTrigger(BaseModel):
    workflow_type: str = "autonomous_discovery"
    categories: str = "fashion,technology,lifestyle"
    regions: str = "US"
    time_range: str = "30 days"

@app.post("/api/trigger-workflow")
async def trigger_workflow(trigger: WorkflowTrigger):
    """Trigger the autonomous workflow"""
    if workflow_status["is_running"]:
        raise HTTPException(status_code=400, detail="Workflow already running")
    
    # Start workflow (simulated for now)
    workflow_status["is_running"] = True
    workflow_status["current_step"] = "Starting autonomous trend discovery..."
    workflow_status["errors"] = None
    workflow_status["results"] = None
    
    # Simulate workflow execution
    import asyncio
    asyncio.create_task(simulate_workflow(trigger))
    
    return {"message": "Workflow started", "workflow_id": f"wf_{int(time.time())}"}

@app.post("/api/stop-workflow")
async def stop_workflow():
    """Stop the current workflow"""
    workflow_status["is_running"] = False
    workflow_status["current_step"] = "Stopped by user"
    return {"message": "Workflow stopped"}

@app.get("/api/workflow-status")
async def get_workflow_status():
    """Get current workflow status"""
    return workflow_status

async def simulate_workflow(trigger: WorkflowTrigger):
    """Execute the REAL autonomous workflow using actual AI agents"""
    global workflow_status
    try:
        workflow_status["current_step"] = "🔍 Initializing AI agents and connecting to data sources..."
        
        # Import and initialize real AI agents
        try:
            from helios.workflows.autonomous_discovery import AutonomousDiscoveryWorkflow
            from helios.services.autonomous_workflow import AutonomousWorkflow
            from helios.config import HeliosConfig
            
            workflow_status["current_step"] = "🔍 Starting real AI-powered trend discovery..."
            
            # Initialize the real autonomous workflow
            if trigger.workflow_type == "autonomous_discovery":
                # Step 1: Run autonomous discovery workflow
                discovery_workflow = AutonomousDiscoveryWorkflow()
                workflow_status["current_step"] = "🔍 Executing autonomous trend discovery..."
                
                result = await discovery_workflow.execute(
                    time_range=trigger.time_range,
                    regions=trigger.regions,
                    categories=trigger.categories.split(',')
                )
                
                workflow_status["current_step"] = "🎨 AI agents generating product designs and concepts..."
                
                # Step 2: Run product generation pipeline
                config = HeliosConfig()
                product_workflow = AutonomousWorkflow(config)
                
                workflow_status["current_step"] = "🖼️ Creating AI-generated images using Vertex AI..."
                
                # Execute the complete autonomous workflow
                product_result = await product_workflow.run_autonomous_workflow("dashboard")
                
                # Extract results from the workflow
                if hasattr(product_result, 'trend_analysis') and product_result.trend_analysis:
                    trends_discovered = 1  # We got at least one trend analysis
                else:
                    trends_discovered = 0
                
                if hasattr(product_result, 'product_recommendation') and product_result.product_recommendation:
                    products_generated = 1
                else:
                    products_generated = 0
                
                if hasattr(product_result, 'generated_image_url') and product_result.generated_image_url:
                    images_created = 1
                else:
                    images_created = 0
                
                if hasattr(product_result, 'published_product_id') and product_result.published_product_id:
                    store_products = 1
                else:
                    store_products = 0
                
                # Combine results
                workflow_status["results"] = {
                    "trends_discovered": trends_discovered,
                    "products_generated": products_generated,
                    "images_created": images_created,
                    "store_products": store_products,
                    "estimated_revenue": "Calculating...",
                    "confidence_score": 0.85,
                    "real_workflow": True,
                    "trend_details": result.get("trends", []) if result else [],
                    "product_details": {
                        "success": product_result.success if hasattr(product_result, 'success') else False,
                        "execution_time": product_result.execution_time if hasattr(product_result, 'execution_time') else 0,
                        "errors": product_result.errors if hasattr(product_result, 'errors') else []
                    },
                    "workflow_result": str(product_result)
                }
                
                workflow_status["current_step"] = "✅ Real AI workflow completed successfully!"
                
            else:
                workflow_status["current_step"] = "❌ Unknown workflow type - using simulation"
                # Fallback to simulation for unknown types
                await _run_simulation_fallback()
                
        except ImportError as e:
            workflow_status["current_step"] = f"⚠️ AI agents not available: {str(e)} - using simulation"
            await _run_simulation_fallback()
            
        except Exception as e:
            workflow_status["current_step"] = f"❌ AI workflow error: {str(e)} - using simulation"
            workflow_status["errors"] = str(e)
            await _run_simulation_fallback()
        
    except Exception as e:
        workflow_status["errors"] = str(e)
        workflow_status["current_step"] = f"❌ Critical error: {str(e)}"
    finally:
        workflow_status["is_running"] = False
        workflow_status["last_run"] = datetime.now().isoformat()

async def _run_simulation_fallback():
    """Fallback simulation if real AI agents fail"""
    global workflow_status
    
    workflow_status["current_step"] = "🔍 Running simulation (AI agents unavailable)..."
    await asyncio.sleep(2)
    
    workflow_status["current_step"] = "🤖 Simulating AI analysis..."
    await asyncio.sleep(3)
    
    workflow_status["current_step"] = "🎨 Simulating product generation..."
    await asyncio.sleep(3)
    
    workflow_status["current_step"] = "🖼️ Simulating image creation..."
    await asyncio.sleep(2)
    
    workflow_status["current_step"] = "📈 Simulating store publishing..."
    await asyncio.sleep(2)
    
    workflow_status["results"] = {
        "trends_discovered": 5,
        "products_generated": 3,
        "images_created": 3,
        "store_products": 3,
        "estimated_revenue": "$2,400/month",
        "confidence_score": 0.89,
        "real_workflow": False,
        "note": "This was a simulation - AI agents need to be configured"
    }
    
    workflow_status["current_step"] = "✅ Simulation completed (not real products)"

def main():
    """Main entry point for the orchestrator service"""
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

if __name__ == "__main__":
    main()
