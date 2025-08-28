#!/usr/bin/env python3
"""
Simple Web Dashboard for Helios System
Allows users to trigger autonomous workflows and monitor the system
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import your autonomous workflow
try:
    from .workflows.autonomous_discovery import AutonomousDiscoveryWorkflow
    from .services.autonomous_workflow import AutonomousWorkflow
    from .config import HeliosConfig
    AUTONOMOUS_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Autonomous workflows not available: {e}")
    AUTONOMOUS_AVAILABLE = False

app = FastAPI(title="Helios Autonomous Store Dashboard", version="1.0.0")

# Store workflow status
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

@app.get("/", response_class=HTMLResponse)
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

@app.post("/api/trigger-workflow")
async def trigger_workflow(trigger: WorkflowTrigger, background_tasks: BackgroundTasks):
    """Trigger the autonomous workflow"""
    if workflow_status["is_running"]:
        raise HTTPException(status_code=400, detail="Workflow already running")
    
    if not AUTONOMOUS_AVAILABLE:
        raise HTTPException(status_code=500, detail="Autonomous workflows not available")
    
    # Start workflow in background
    background_tasks.add_task(run_autonomous_workflow, trigger)
    
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

async def run_autonomous_workflow(trigger: WorkflowTrigger):
    """Run the autonomous workflow in the background"""
    try:
        workflow_status["is_running"] = True
        workflow_status["current_step"] = "Initializing..."
        workflow_status["errors"] = None
        workflow_status["results"] = None
        
        # Initialize workflow based on type
        if trigger.workflow_type == "autonomous_discovery":
            workflow = AutonomousDiscoveryWorkflow()
            workflow_status["current_step"] = "Starting autonomous trend discovery..."
            
            # Run the workflow
            result = await workflow.execute(
                time_range=trigger.time_range,
                regions=trigger.regions,
                categories=trigger.categories
            )
            
            workflow_status["results"] = result
            workflow_status["current_step"] = "Completed successfully"
            
        elif trigger.workflow_type == "product_generation":
            # This would use the AutonomousWorkflow class
            workflow_status["current_step"] = "Product generation not yet implemented"
            
        else:
            workflow_status["current_step"] = "Unknown workflow type"
            
    except Exception as e:
        workflow_status["errors"] = str(e)
        workflow_status["current_step"] = f"Error: {str(e)}"
    finally:
        workflow_status["is_running"] = False
        workflow_status["last_run"] = datetime.now().isoformat()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
