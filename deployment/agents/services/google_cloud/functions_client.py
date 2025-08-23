"""Google Cloud Functions client for Helios Autonomous Store"""

import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Union
from google.cloud import functions_v2
from google.cloud.functions_v2 import Function, CreateFunctionRequest, UpdateFunctionRequest
from google.api_core import retry
from loguru import logger


class CloudFunctionsClient:
    """Google Cloud Functions client for managing serverless functions"""
    
    def __init__(self, project_id: str, location: str = "us-central1", credentials_path: Optional[str] = None):
        """Initialize Cloud Functions client"""
        self.project_id = project_id
        self.location = location
        
        # Initialize client
        if credentials_path:
            self.client = functions_v2.FunctionServiceClient.from_service_account_file(credentials_path)
        else:
            self.client = functions_v2.FunctionServiceClient()
        
        # Function cache
        self._functions = {}
        
        logger.info(f"🔧 Cloud Functions client initialized for project: {project_id}, location: {location}")
    
    def _get_parent(self) -> str:
        """Get parent path for Cloud Functions"""
        return f"projects/{self.project_id}/locations/{self.location}"
    
    def _get_function_path(self, function_name: str) -> str:
        """Get full function path"""
        return f"{self._get_parent()}/functions/{function_name}"
    
    async def create_function(
        self,
        function_name: str,
        source_code: str,
        runtime: str = "python311",
        entry_point: str = "main",
        memory: str = "256Mi",
        cpu: str = "1",
        timeout_seconds: int = 60,
        environment_variables: Optional[Dict[str, str]] = None,
        labels: Optional[Dict[str, str]] = None
    ) -> str:
        """Create a new Cloud Function"""
        try:
            function_path = self._get_function_path(function_name)
            
            # Prepare function configuration
            function = Function(
                name=function_path,
                description=f"Helios function: {function_name}",
                build_config=functions_v2.BuildConfig(
                    runtime=runtime,
                    entry_point=entry_point,
                    source=functions_v2.Source(
                        storage_source=functions_v2.StorageSource(
                            bucket=f"{self.project_id}-functions-source",
                            object_=f"{function_name}/source.zip"
                        )
                    )
                ),
                service_config=functions_v2.ServiceConfig(
                    memory=memory,
                    cpu=cpu,
                    timeout_seconds=timeout_seconds,
                    environment_variables=environment_variables or {},
                    labels=labels or {"system": "helios", "created": str(int(time.time()))}
                )
            )
            
            # Create function request
            request = CreateFunctionRequest(
                parent=self._get_parent(),
                function_id=function_name,
                function=function
            )
            
            # Create the function
            operation = self.client.create_function(request=request)
            result = operation.result()
            
            self._functions[function_name] = result.name
            logger.info(f"✅ Created Cloud Function: {function_name}")
            return result.name
            
        except Exception as e:
            logger.error(f"❌ Failed to create function {function_name}: {e}")
            raise
    
    async def update_function(
        self,
        function_name: str,
        source_code: Optional[str] = None,
        environment_variables: Optional[Dict[str, str]] = None,
        memory: Optional[str] = None,
        cpu: Optional[str] = None,
        timeout_seconds: Optional[int] = None
    ) -> str:
        """Update an existing Cloud Function"""
        try:
            function_path = self._get_function_path(function_name)
            
            # Get current function
            current_function = self.client.get_function(name=function_path)
            
            # Prepare update mask
            update_mask = []
            if source_code:
                update_mask.append("build_config.source")
            if environment_variables:
                update_mask.append("service_config.environment_variables")
            if memory:
                update_mask.append("service_config.memory")
            if cpu:
                update_mask.append("service_config.cpu")
            if timeout_seconds:
                update_mask.append("service_config.timeout_seconds")
            
            # Create updated function
            updated_function = Function(
                name=function_path,
                build_config=current_function.build_config,
                service_config=current_function.service_config
            )
            
            # Apply updates
            if source_code:
                updated_function.build_config.source.storage_source.object_ = f"{function_name}/source-{int(time.time())}.zip"
            if environment_variables:
                updated_function.service_config.environment_variables.update(environment_variables)
            if memory:
                updated_function.service_config.memory = memory
            if cpu:
                updated_function.service_config.cpu = cpu
            if timeout_seconds:
                updated_function.service_config.timeout_seconds = timeout_seconds
            
            # Update function request
            request = UpdateFunctionRequest(
                function=updated_function,
                update_mask=",".join(update_mask)
            )
            
            # Update the function
            operation = self.client.update_function(request=request)
            result = operation.result()
            
            logger.info(f"✅ Updated Cloud Function: {function_name}")
            return result.name
            
        except Exception as e:
            logger.error(f"❌ Failed to update function {function_name}: {e}")
            raise
    
    async def delete_function(self, function_name: str) -> bool:
        """Delete a Cloud Function"""
        try:
            function_path = self._get_function_path(function_name)
            
            # Delete the function
            operation = self.client.delete_function(name=function_path)
            operation.result()
            
            # Remove from cache
            self._functions.pop(function_name, None)
            
            logger.info(f"✅ Deleted Cloud Function: {function_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to delete function {function_name}: {e}")
            return False
    
    async def invoke_function(
        self,
        function_name: str,
        data: Union[str, Dict[str, Any]],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Invoke a Cloud Function"""
        try:
            function_path = self._get_function_path(function_name)
            
            # Prepare request data
            if isinstance(data, dict):
                request_data = json.dumps(data).encode("utf-8")
            else:
                request_data = str(data).encode("utf-8")
            
            # Prepare headers
            request_headers = headers or {}
            request_headers.update({
                "Content-Type": "application/json",
                "User-Agent": "helios-autonomous-store"
            })
            
            # Create HTTP request
            http_request = functions_v2.HttpRequest(
                url=f"https://{self.location}-{self.project_id}.cloudfunctions.net/{function_name}",
                method="POST",
                headers=request_headers,
                body=request_data
            )
            
            # Invoke function
            response = self.client.call_function(
                name=function_path,
                data=request_data
            )
            
            # Parse response
            try:
                response_data = json.loads(response.result.decode("utf-8"))
            except (json.JSONDecodeError, AttributeError):
                response_data = {"raw_response": str(response.result)}
            
            logger.debug(f"📤 Invoked function {function_name}")
            return {
                "status": "success",
                "function_name": function_name,
                "response": response_data,
                "execution_time_ms": getattr(response, "execution_time_ms", 0)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to invoke function {function_name}: {e}")
            return {
                "status": "error",
                "function_name": function_name,
                "error": str(e)
            }
    
    async def list_functions(self, max_results: int = 100) -> List[Dict[str, Any]]:
        """List all Cloud Functions"""
        try:
            parent = self._get_parent()
            
            # List functions
            page_result = self.client.list_functions(parent=parent, page_size=max_results)
            
            functions = []
            for function in page_result:
                function_info = {
                    "name": function.name.split("/")[-1],
                    "full_path": function.name,
                    "runtime": function.build_config.runtime if function.build_config else "unknown",
                    "entry_point": function.build_config.entry_point if function.build_config else "unknown",
                    "memory": function.service_config.memory if function.service_config else "unknown",
                    "cpu": function.service_config.cpu if function.service_config else "unknown",
                    "timeout": function.service_config.timeout_seconds if function.service_config else 0,
                    "labels": dict(function.service_config.labels) if function.service_config and function.service_config.labels else {},
                    "state": function.state.name if function.state else "unknown",
                    "update_time": function.update_time.isoformat() if function.update_time else None
                }
                functions.append(function_info)
            
            logger.info(f"📋 Listed {len(functions)} Cloud Functions")
            return functions
            
        except Exception as e:
            logger.error(f"❌ Failed to list functions: {e}")
            return []
    
    async def get_function_status(self, function_name: str) -> Dict[str, Any]:
        """Get detailed status of a Cloud Function"""
        try:
            function_path = self._get_function_path(function_name)
            
            # Get function details
            function = self.client.get_function(name=function_path)
            
            status_info = {
                "name": function.name.split("/")[-1],
                "full_path": function.name,
                "state": function.state.name if function.state else "unknown",
                "runtime": function.build_config.runtime if function.build_config else "unknown",
                "entry_point": function.build_config.entry_point if function.build_config else "unknown",
                "memory": function.service_config.memory if function.service_config else "unknown",
                "cpu": function.service_config.cpu if function.service_config else "unknown",
                "timeout": function.service_config.timeout_seconds if function.service_config else 0,
                "environment_variables": dict(function.service_config.environment_variables) if function.service_config and function.service_config.environment_variables else {},
                "labels": dict(function.service_config.labels) if function.service_config and function.service_config.labels else {},
                "create_time": function.create_time.isoformat() if function.create_time else None,
                "update_time": function.update_time.isoformat() if function.update_time else None,
                "url": f"https://{self.location}-{self.project_id}.cloudfunctions.net/{function_name}"
            }
            
            return status_info
            
        except Exception as e:
            logger.error(f"❌ Failed to get status for function {function_name}: {e}")
            return {"error": str(e)}
    
    async def create_helios_functions(self) -> Dict[str, str]:
        """Create standard Helios Cloud Functions"""
        functions_config = {
            "helios-trend-analyzer": {
                "description": "Trend analysis and validation",
                "runtime": "python311",
                "entry_point": "analyze_trend",
                "memory": "512Mi",
                "cpu": "1",
                "timeout_seconds": 300
            },
            "helios-content-generator": {
                "description": "Content and image generation",
                "runtime": "python311",
                "entry_point": "generate_content",
                "memory": "1Gi",
                "cpu": "2",
                "timeout_seconds": 600
            },
            "helios-quality-checker": {
                "description": "Quality assurance and compliance",
                "runtime": "python311",
                "entry_point": "check_quality",
                "memory": "256Mi",
                "cpu": "1",
                "timeout_seconds": 120
            },
            "helios-publisher": {
                "description": "Product publication automation",
                "runtime": "python311",
                "entry_point": "publish_product",
                "memory": "512Mi",
                "cpu": "1",
                "timeout_seconds": 300
            }
        }
        
        created_functions = {}
        for function_name, config in functions_config.items():
            try:
                function_path = await self.create_function(
                    function_name=function_name,
                    source_code="",  # Placeholder - would need actual source code
                    **config
                )
                created_functions[function_name] = function_path
                logger.info(f"✅ Created Helios function: {function_name}")
            except Exception as e:
                logger.warning(f"⚠️  Function {function_name} may already exist: {e}")
        
        return created_functions
    
    def close(self):
        """Close client connection"""
        try:
            self.client.close()
            logger.info("🔧 Cloud Functions client connection closed")
        except Exception as e:
            logger.warning(f"⚠️  Error closing Cloud Functions connection: {e}")


# Async context manager wrapper
class AsyncCloudFunctionsClient:
    """Async context manager for Cloud Functions client"""
    
    def __init__(self, project_id: str, location: str = "us-central1", credentials_path: Optional[str] = None):
        self.client = CloudFunctionsClient(project_id, location, credentials_path)
    
    async def __aenter__(self):
        return self.client
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.client.close()
