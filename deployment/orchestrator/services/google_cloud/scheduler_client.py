"""
Google Cloud Scheduler Client for Helios Autonomous Store
Handles automated workflow scheduling and task management
"""

import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass
from loguru import logger

try:
    from google.cloud import scheduler_v1
    from google.cloud.scheduler_v1 import Job, CreateJobRequest, UpdateJobRequest, DeleteJobRequest
    from google.cloud.scheduler_v1.types import Job as JobType
    from google.api_core.exceptions import GoogleAPIError
    from google.auth.exceptions import DefaultCredentialsError
    SCHEDULER_AVAILABLE = True
except ImportError:
    scheduler_v1 = None
    Job = None
    CreateJobRequest = None
    UpdateJobRequest = None
    DeleteJobRequest = None
    JobType = None
    GoogleAPIError = Exception
    DefaultCredentialsError = Exception
    SCHEDULER_AVAILABLE = False


@dataclass
class SchedulerConfig:
    """Configuration for Cloud Scheduler client"""
    project_id: str
    location: str
    enable_retry: bool = True
    max_retry_count: int = 3
    retry_delay: int = 60  # seconds


class CloudSchedulerClient:
    """Google Cloud Scheduler client for Helios Autonomous Store"""
    
    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        
        if SCHEDULER_AVAILABLE:
            self.client = scheduler_v1.CloudSchedulerClient()
            # Parent resource path
            self.parent = f"projects/{project_id}/locations/{location}"
        else:
            self.client = None
            self.parent = None
            logger.warning("Google Cloud Scheduler not available - scheduler functionality will be disabled")
        
        # Job templates for common Helios workflows
        self.job_templates = {
            "trend_discovery": {
                "description": "Automated trend discovery and analysis",
                "schedule": "0 */6 * * *",  # Every 6 hours
                "time_zone": "America/New_York",
                "http_target": {
                    "uri": "https://trend-discovery-service.run.app/discover",
                    "http_method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"automated": True, "source": "scheduler"})
                }
            },
            "content_generation": {
                "description": "Automated content generation for approved trends",
                "schedule": "0 */4 * * *",  # Every 4 hours
                "time_zone": "America/New_York",
                "http_target": {
                    "uri": "https://content-generation-service.run.app/generate",
                    "http_method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"automated": True, "source": "scheduler"})
                }
            },
            "performance_analysis": {
                "description": "Daily performance analysis and optimization",
                "schedule": "0 9 * * *",  # Daily at 9 AM
                "time_zone": "America/New_York",
                "http_target": {
                    "uri": "https://performance-service.run.app/analyze",
                    "http_method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"automated": True, "source": "scheduler"})
                }
            },
            "asset_cleanup": {
                "description": "Weekly cleanup of old assets",
                "schedule": "0 2 * * 0",  # Weekly on Sunday at 2 AM
                "time_zone": "America/New_York",
                "http_target": {
                    "uri": "https://storage-service.run.app/cleanup",
                    "http_method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"automated": True, "source": "scheduler"})
                }
            }
        }
        
        logger.info(f"✅ Cloud Scheduler client initialized for project: {project_id}")
    
    async def create_job(
        self,
        job_id: str,
        schedule: str,
        target_uri: str,
        description: str = None,
        time_zone: str = "America/New_York",
        http_method: str = "POST",
        headers: Dict[str, str] = None,
        body: str = None,
        retry_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create a new scheduled job
        
        Args:
            job_id: Unique identifier for the job
            schedule: Cron expression for scheduling
            target_uri: Target HTTP endpoint
            description: Job description
            time_zone: Timezone for scheduling
            http_method: HTTP method for the request
            headers: HTTP headers
            body: Request body
            retry_config: Retry configuration
        
        Returns:
            Job creation result
        """
        if not SCHEDULER_AVAILABLE or self.client is None:
            logger.warning("Google Cloud Scheduler not available - cannot create job")
            return {"success": False, "error": "Google Cloud Scheduler not available"}
            
        try:
            # Build job path
            job_path = f"{self.parent}/jobs/{job_id}"
            
            # Default headers
            if headers is None:
                headers = {"Content-Type": "application/json"}
            
            # Default retry config
            if retry_config is None:
                retry_config = {
                    "retry_count": 3,
                    "max_retry_duration": "300s",
                    "min_backoff_duration": "5s",
                    "max_backoff_duration": "60s",
                    "max_doublings": 5
                }
            
            # Create job request
            job = Job(
                name=job_path,
                description=description or f"Scheduled job: {job_id}",
                schedule=schedule,
                time_zone=time_zone,
                http_target=scheduler_v1.HttpTarget(
                    uri=target_uri,
                    http_method=getattr(scheduler_v1.HttpMethod, http_method.upper()),
                    headers=headers,
                    body=body.encode() if body else None
                ),
                retry_config=scheduler_v1.RetryConfig(
                    retry_count=retry_config["retry_count"],
                    max_retry_duration=retry_config["max_retry_duration"],
                    min_backoff_duration=retry_config["min_backoff_duration"],
                    max_backoff_duration=retry_config["max_backoff_duration"],
                    max_doublings=retry_config["max_doublings"]
                ) if retry_config else None
            )
            
            # Create job request
            request = CreateJobRequest(
                parent=self.parent,
                job=job
            )
            
            # Create the job
            created_job = self.client.create_job(request=request)
            
            result = {
                "status": "success",
                "job_id": job_id,
                "job_name": created_job.name,
                "schedule": created_job.schedule,
                "state": created_job.state.name,
                "creation_time": created_job.create_time.ToDatetime().isoformat(),
                "next_run_time": created_job.next_run_time.ToDatetime().isoformat() if created_job.next_run_time else None
            }
            
            logger.info(f"✅ Job created successfully: {job_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Job creation failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "job_id": job_id
            }
    
    async def create_job_from_template(
        self,
        job_id: str,
        template_name: str,
        custom_uri: str = None,
        custom_schedule: str = None
    ) -> Dict[str, Any]:
        """Create a job using predefined templates
        
        Args:
            job_id: Unique identifier for the job
            template_name: Name of the template to use
            custom_uri: Custom target URI (optional)
            custom_schedule: Custom schedule (optional)
        
        Returns:
            Job creation result
        """
        try:
            if template_name not in self.job_templates:
                return {
                    "status": "error",
                    "error": f"Unknown template: {template_name}",
                    "available_templates": list(self.job_templates.keys())
                }
            
            template = self.job_templates[template_name]
            
            # Use custom values if provided
            target_uri = custom_uri or template["http_target"]["uri"]
            schedule = custom_schedule or template["schedule"]
            
            return await self.create_job(
                job_id=job_id,
                schedule=schedule,
                target_uri=target_uri,
                description=template["description"],
                time_zone=template["time_zone"],
                http_method=template["http_target"]["http_method"],
                headers=template["http_target"]["headers"],
                body=template["http_target"]["body"]
            )
            
        except Exception as e:
            logger.error(f"❌ Template job creation failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "job_id": job_id,
                "template": template_name
            }
    
    async def list_jobs(self, max_results: int = 100) -> Dict[str, Any]:
        """List all scheduled jobs
        
        Args:
            max_results: Maximum number of results
        
        Returns:
            List of jobs with details
        """
        try:
            # List jobs request
            request = scheduler_v1.ListJobsRequest(
                parent=self.parent,
                page_size=max_results
            )
            
            # Get jobs
            page_result = self.client.list_jobs(request=request)
            jobs = []
            
            for job in page_result:
                job_info = {
                    "job_id": job.name.split("/")[-1],
                    "job_name": job.name,
                    "description": job.description,
                    "schedule": job.schedule,
                    "time_zone": job.time_zone,
                    "state": job.state.name,
                    "creation_time": job.create_time.ToDatetime().isoformat() if job.create_time else None,
                    "next_run_time": job.next_run_time.ToDatetime().isoformat() if job.next_run_time else None,
                    "last_attempt_time": job.last_attempt_time.ToDatetime().isoformat() if job.last_attempt_time else None,
                    "attempt_deadline": job.attempt_deadline.ToDatetime().isoformat() if job.attempt_deadline else None
                }
                jobs.append(job_info)
            
            result = {
                "status": "success",
                "total_jobs": len(jobs),
                "jobs": jobs
            }
            
            logger.info(f"✅ Listed {len(jobs)} scheduled jobs")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to list jobs: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_job(self, job_id: str) -> Dict[str, Any]:
        """Get details of a specific job
        
        Args:
            job_id: Job identifier
        
        Returns:
            Job details
        """
        try:
            # Build job path
            job_path = f"{self.parent}/jobs/{job_id}"
            
            # Get job request
            request = scheduler_v1.GetJobRequest(name=job_path)
            
            # Get the job
            job = self.client.get_job(request=request)
            
            job_info = {
                "status": "success",
                "job_id": job_id,
                "job_name": job.name,
                "description": job.description,
                "schedule": job.schedule,
                "time_zone": job.time_zone,
                "state": job.state.name,
                "creation_time": job.create_time.ToDatetime().isoformat() if job.create_time else None,
                "next_run_time": job.next_run_time.ToDatetime().isoformat() if job.next_run_time else None,
                "last_attempt_time": job.last_attempt_time.ToDatetime().isoformat() if job.last_attempt_time else None,
                "attempt_deadline": job.attempt_deadline.ToDatetime().isoformat() if job.attempt_deadline else None,
                "http_target": {
                    "uri": job.http_target.uri,
                    "http_method": job.http_target.http_method.name,
                    "headers": dict(job.http_target.headers),
                    "body": job.http_target.body.decode() if job.http_target.body else None
                } if job.http_target else None
            }
            
            return job_info
            
        except Exception as e:
            logger.error(f"❌ Failed to get job: {e}")
            return {
                "status": "error",
                "error": str(e),
                "job_id": job_id
            }
    
    async def update_job(
        self,
        job_id: str,
        updates: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update an existing job
        
        Args:
            job_id: Job identifier
            updates: Fields to update
        
        Returns:
            Update result
        """
        try:
            # Get current job
            current_job = await self.get_job(job_id)
            if current_job["status"] != "success":
                return current_job
            
            # Build job path
            job_path = f"{self.parent}/jobs/{job_id}"
            
            # Create updated job
            updated_job = Job(
                name=job_path,
                description=updates.get("description", current_job["description"]),
                schedule=updates.get("schedule", current_job["schedule"]),
                time_zone=updates.get("time_zone", current_job["time_zone"])
            )
            
            # Update HTTP target if provided
            if "http_target" in updates:
                http_target = updates["http_target"]
                updated_job.http_target = scheduler_v1.HttpTarget(
                    uri=http_target.get("uri", current_job["http_target"]["uri"]),
                    http_method=getattr(scheduler_v1.HttpMethod, http_target.get("http_method", "POST").upper()),
                    headers=http_target.get("headers", current_job["http_target"]["headers"]),
                    body=http_target.get("body", current_job["http_target"]["body"]).encode() if http_target.get("body") else None
                )
            
            # Update job request
            request = UpdateJobRequest(job=updated_job)
            
            # Update the job
            updated_job_result = self.client.update_job(request=request)
            
            result = {
                "status": "success",
                "job_id": job_id,
                "message": "Job updated successfully",
                "updated_fields": list(updates.keys())
            }
            
            logger.info(f"✅ Job updated successfully: {job_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Job update failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "job_id": job_id
            }
    
    async def pause_job(self, job_id: str) -> Dict[str, Any]:
        """Pause a scheduled job
        
        Args:
            job_id: Job identifier
        
        Returns:
            Pause result
        """
        try:
            # Build job path
            job_path = f"{self.parent}/jobs/{job_id}"
            
            # Pause job request
            request = scheduler_v1.PauseJobRequest(name=job_path)
            
            # Pause the job
            self.client.pause_job(request=request)
            
            result = {
                "status": "success",
                "job_id": job_id,
                "message": "Job paused successfully"
            }
            
            logger.info(f"✅ Job paused successfully: {job_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Job pause failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "job_id": job_id
            }
    
    async def resume_job(self, job_id: str) -> Dict[str, Any]:
        """Resume a paused job
        
        Args:
            job_id: Job identifier
        
        Returns:
            Resume result
        """
        try:
            # Build job path
            job_path = f"{self.parent}/jobs/{job_id}"
            
            # Resume job request
            request = scheduler_v1.ResumeJobRequest(name=job_path)
            
            # Resume the job
            self.client.resume_job(request=request)
            
            result = {
                "status": "success",
                "job_id": job_id,
                "message": "Job resumed successfully"
            }
            
            logger.info(f"✅ Job resumed successfully: {job_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Job resume failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "job_id": job_id
            }
    
    async def delete_job(self, job_id: str) -> Dict[str, Any]:
        """Delete a scheduled job
        
        Args:
            job_id: Job identifier
        
        Returns:
            Deletion result
        """
        try:
            # Build job path
            job_path = f"{self.parent}/jobs/{job_id}"
            
            # Delete job request
            request = DeleteJobRequest(name=job_path)
            
            # Delete the job
            self.client.delete_job(request=request)
            
            result = {
                "status": "success",
                "job_id": job_id,
                "message": "Job deleted successfully"
            }
            
            logger.info(f"✅ Job deleted successfully: {job_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Job deletion failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "job_id": job_id
            }
    
    async def run_job_now(self, job_id: str) -> Dict[str, Any]:
        """Run a job immediately
        
        Args:
            job_id: Job identifier
        
        Returns:
            Run result
        """
        try:
            # Build job path
            job_path = f"{self.parent}/jobs/{job_id}"
            
            # Run job request
            request = scheduler_v1.RunJobRequest(name=job_path)
            
            # Run the job
            execution = self.client.run_job(request=request)
            
            result = {
                "status": "success",
                "job_id": job_id,
                "message": "Job executed successfully",
                "execution_name": execution.name,
                "execution_time": execution.create_time.ToDatetime().isoformat() if execution.create_time else None
            }
            
            logger.info(f"✅ Job executed successfully: {job_id}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Job execution failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "job_id": job_id
            }
    
    async def setup_helios_workflows(self) -> Dict[str, Any]:
        """Setup default Helios workflow schedules"""
        try:
            logger.info("🔧 Setting up Helios workflow schedules...")
            
            setup_results = {
                "status": "success",
                "jobs_created": [],
                "jobs_failed": [],
                "total_jobs": 0
            }
            
            # Create jobs for each template
            for template_name in self.job_templates.keys():
                job_id = f"helios-{template_name}-{int(time.time())}"
                
                result = await self.create_job_from_template(job_id, template_name)
                
                if result["status"] == "success":
                    setup_results["jobs_created"].append({
                        "template": template_name,
                        "job_id": job_id,
                        "schedule": result["schedule"]
                    })
                    setup_results["total_jobs"] += 1
                else:
                    setup_results["jobs_failed"].append({
                        "template": template_name,
                        "job_id": job_id,
                        "error": result["error"]
                    })
            
            logger.info(f"✅ Helios workflows setup completed: {setup_results['total_jobs']} jobs created")
            return setup_results
            
        except Exception as e:
            logger.error(f"❌ Helios workflows setup failed: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def get_job_execution_history(self, job_id: str, max_results: int = 50) -> Dict[str, Any]:
        """Get execution history for a job
        
        Args:
            job_id: Job identifier
            max_results: Maximum number of results
        
        Returns:
            Execution history
        """
        try:
            # Build job path
            job_path = f"{self.parent}/jobs/{job_id}"
            
            # List executions request
            request = scheduler_v1.ListJobExecutionsRequest(
                parent=job_path,
                page_size=max_results
            )
            
            # Get executions
            page_result = self.client.list_job_executions(request=request)
            executions = []
            
            for execution in page_result:
                execution_info = {
                    "execution_name": execution.name,
                    "state": execution.state.name,
                    "create_time": execution.create_time.ToDatetime().isoformat() if execution.create_time else None,
                    "update_time": execution.update_time.ToDatetime().isoformat() if execution.update_time else None,
                    "attempt_deadline": execution.attempt_deadline.ToDatetime().isoformat() if execution.attempt_deadline else None,
                    "response_status": execution.response_status.code if execution.response_status else None,
                    "response_message": execution.response_status.message if execution.response_status else None
                }
                executions.append(execution_info)
            
            result = {
                "status": "success",
                "job_id": job_id,
                "total_executions": len(executions),
                "executions": executions
            }
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get job execution history: {e}")
            return {
                "status": "error",
                "error": str(e),
                "job_id": job_id
            }
    
    def close(self):
        """Close the Cloud Scheduler client"""
        try:
            if self.client:
                self.client.close()
            logger.info("✅ Cloud Scheduler client closed")
            
        except Exception as e:
            logger.error(f"❌ Error closing Cloud Scheduler client: {e}")


# Convenience functions
async def setup_helios_schedules(project_id: str, location: str = "us-central1") -> Dict[str, Any]:
    """Convenience function for setting up Helios schedules"""
    client = CloudSchedulerClient(project_id, location)
    try:
        return await client.setup_helios_workflows()
    finally:
        await client.close()


async def create_trend_discovery_job(project_id: str, target_uri: str, schedule: str = "0 */6 * * *") -> Dict[str, Any]:
    """Convenience function for creating trend discovery job"""
    client = CloudSchedulerClient(project_id)
    try:
        return await client.create_job(
            job_id=f"trend-discovery-{int(time.time())}",
            schedule=schedule,
            target_uri=target_uri,
            description="Automated trend discovery for Helios"
        )
    finally:
        await client.close()
