#!/usr/bin/env python3
"""
Workflow Resilience Module for Helios System
Implements Dead-Letter Queue (DLQ) and retry mechanisms for robust workflow execution
"""

import json
import time
import traceback
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

try:
    from google.cloud import pubsub_v1
    from google.cloud.pubsub_v1.types import PublishRequest
    PUBSUB_AVAILABLE = True
except ImportError:
    pubsub_v1 = None
    PUBSUB_AVAILABLE = False

@dataclass
class WorkflowJob:
    """Represents a workflow job with retry tracking"""
    job_id: str
    payload: Dict[str, Any]
    workflow_type: str
    max_retries: int = 3
    current_retries: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_attempt: Optional[datetime] = None
    error_history: list = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed, dlq

@dataclass
class DLQMessage:
    """Dead-Letter Queue message structure"""
    job_id: str
    original_payload: Dict[str, Any]
    workflow_type: str
    failure_reason: str
    error_details: str
    retry_count: int
    failed_at: datetime
    context: Dict[str, Any] = field(default_factory=dict)

class WorkflowResilienceManager:
    """Manages workflow resilience including retries and Dead-Letter Queue"""
    
    def __init__(self, project_id: str, dlq_topic_name: str = "helios-workflow-dlq"):
        self.project_id = project_id
        self.dlq_topic_name = dlq_topic_name
        self.publisher = None
        self.dlq_topic_path = None
        
        if PUBSUB_AVAILABLE:
            self._initialize_pubsub()
    
    def _initialize_pubsub(self):
        """Initialize Google Cloud Pub/Sub client"""
        try:
            self.publisher = pubsub_v1.PublisherClient()
            self.dlq_topic_path = self.publisher.topic_path(self.project_id, self.dlq_topic_name)
            
            # Ensure the DLQ topic exists
            self._ensure_dlq_topic_exists()
        except Exception as e:
            print(f"Failed to initialize Pub/Sub: {e}")
            self.publisher = None
    
    def _ensure_dlq_topic_exists(self):
        """Ensure the DLQ topic exists, create if it doesn't"""
        try:
            from google.cloud import pubsub_admin_v1
            admin_client = pubsub_admin_v1.TopicAdminClient()
            topic_path = admin_client.topic_path(self.project_id, self.dlq_topic_name)
            
            try:
                admin_client.get_topic(request={"topic": topic_path})
            except Exception:
                # Topic doesn't exist, create it
                admin_client.create_topic(request={"name": topic_path})
                print(f"Created DLQ topic: {self.dlq_topic_path}")
        except Exception as e:
            print(f"Failed to ensure DLQ topic exists: {e}")
    
    async def execute_with_resilience(
        self, 
        job: WorkflowJob, 
        execution_func, 
        *args, 
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a workflow job with retry logic and DLQ fallback"""
        
        while job.current_retries < job.max_retries:
            try:
                job.status = "running"
                job.last_attempt = datetime.now(timezone.utc)
                
                # Execute the workflow
                result = await execution_func(*args, **kwargs)
                
                job.status = "completed"
                return {
                    "success": True,
                    "job_id": job.job_id,
                    "result": result,
                    "retry_count": job.current_retries
                }
                
            except Exception as e:
                job.current_retries += 1
                job.error_history.append({
                    "attempt": job.current_retries,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })
                
                if job.current_retries >= job.max_retries:
                    # Job has failed all retries, send to DLQ
                    await self._send_to_dlq(job, e)
                    job.status = "dlq"
                    
                    return {
                        "success": False,
                        "job_id": job.job_id,
                        "error": "Job failed all retries and sent to DLQ",
                        "retry_count": job.current_retries,
                        "dlq_message_id": job.job_id
                    }
                else:
                    # Wait before retry with exponential backoff
                    wait_time = min(2 ** job.current_retries, 60)  # Cap at 60 seconds
                    print(f"Job {job.job_id} failed, retrying in {wait_time} seconds... (attempt {job.current_retries}/{job.max_retries})")
                    time.sleep(wait_time)
        
        # This should never be reached, but just in case
        job.status = "failed"
        return {
            "success": False,
            "job_id": job.job_id,
            "error": "Unexpected retry loop exit",
            "retry_count": job.current_retries
        }
    
    async def _send_to_dlq(self, job: WorkflowJob, error: Exception):
        """Send a failed job to the Dead-Letter Queue"""
        if not self.publisher:
            print(f"DLQ not available, job {job.job_id} would be sent to DLQ")
            return None
        
        try:
            dlq_message = DLQMessage(
                job_id=job.job_id,
                original_payload=job.payload,
                workflow_type=job.workflow_type,
                failure_reason=str(error),
                error_details=traceback.format_exc() if hasattr(traceback, 'format_exc') else str(error),
                retry_count=job.current_retries,
                failed_at=datetime.now(timezone.utc),
                context={
                    "created_at": job.created_at.isoformat(),
                    "error_history": job.error_history,
                    "workflow_type": job.workflow_type
                }
            )
            
            # Serialize the DLQ message
            message_data = json.dumps({
                "job_id": dlq_message.job_id,
                "original_payload": dlq_message.original_payload,
                "workflow_type": dlq_message.workflow_type,
                "failure_reason": dlq_message.failure_reason,
                "error_details": dlq_message.error_details,
                "retry_count": dlq_message.retry_count,
                "failed_at": dlq_message.failed_at.isoformat(),
                "context": dlq_message.context
            }, default=str).encode("utf-8")
            
            # Publish to DLQ topic
            future = self.publisher.publish(
                self.dlq_topic_path,
                data=message_data,
                job_id=dlq_message.job_id,
                workflow_type=dlq_message.workflow_type,
                retry_count=str(dlq_message.retry_count)
            )
            
            message_id = future.result()
            print(f"Job {job.job_id} sent to DLQ with message ID: {message_id}")
            return message_id
            
        except Exception as e:
            print(f"Failed to send job {job.job_id} to DLQ: {e}")
            return None
    
    async def get_dlq_stats(self) -> Dict[str, Any]:
        """Get statistics about the Dead-Letter Queue"""
        if not self.publisher:
            return {"error": "DLQ not available"}
        
        try:
            from google.cloud import pubsub_admin_v1
            admin_client = pubsub_admin_v1.SubscriptionAdminClient()
            
            # List subscriptions for the DLQ topic
            subscription_path = admin_client.subscription_path(self.project_id, f"{self.dlq_topic_name}-sub")
            
            try:
                subscription = admin_client.get_subscription(request={"subscription": subscription_path})
                return {
                    "topic_name": self.dlq_topic_name,
                    "subscription_name": f"{self.dlq_topic_name}-sub",
                    "message_retention_duration": str(subscription.message_retention_duration),
                    "ack_deadline_seconds": subscription.ack_deadline_seconds
                }
            except Exception:
                return {
                    "topic_name": self.dlq_topic_name,
                    "subscription_name": f"{self.dlq_topic_name}-sub",
                    "status": "subscription_not_found"
                }
                
        except Exception as e:
            return {"error": f"Failed to get DLQ stats: {e}"}
    
    def close(self):
        """Clean up resources"""
        if self.publisher:
            self.publisher.close()

# Convenience function for creating workflow jobs
def create_workflow_job(
    job_id: str, 
    payload: Dict[str, Any], 
    workflow_type: str, 
    max_retries: int = 3
) -> WorkflowJob:
    """Create a new workflow job with resilience tracking"""
    return WorkflowJob(
        job_id=job_id,
        payload=payload,
        workflow_type=workflow_type,
        max_retries=max_retries
    )

# Export the main classes and functions
__all__ = [
    'WorkflowJob',
    'DLQMessage', 
    'WorkflowResilienceManager',
    'create_workflow_job'
]
