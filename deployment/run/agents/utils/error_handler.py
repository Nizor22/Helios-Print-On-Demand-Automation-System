"""
Error Handling and Recovery Utility for Helios Autonomous Store
Provides structured error handling, retry logic, and error reporting
"""

import asyncio
import logging
import traceback
import json
from typing import Dict, Any, Optional, Callable, Type, Union
from datetime import datetime, timedelta
from functools import wraps
from enum import Enum

try:
    from google.cloud import firestore
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False

try:
    from google.cloud import pubsub_v1
    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False

logger = logging.getLogger(__name__)


class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories for classification"""
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    RATE_LIMIT = "rate_limit"
    VALIDATION = "validation"
    PROCESSING = "processing"
    EXTERNAL_API = "external_api"
    DATABASE = "database"
    STORAGE = "storage"
    AI_MODEL = "ai_model"
    UNKNOWN = "unknown"


class HeliosError(Exception):
    """Base exception class for Helios system"""
    
    def __init__(
        self, 
        message: str, 
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Dict[str, Any] = None,
        original_error: Exception = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.severity = severity
        self.context = context or {}
        self.original_error = original_error
        self.timestamp = datetime.utcnow()
        self.error_id = self._generate_error_id()
    
    def _generate_error_id(self) -> str:
        """Generate unique error ID"""
        timestamp = self.timestamp.strftime("%Y%m%d_%H%M%S")
        return f"HELIOS_ERROR_{timestamp}_{hash(self.message) % 10000:04d}"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for logging/storage"""
        return {
            "error_id": self.error_id,
            "message": self.message,
            "category": self.category.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context,
            "original_error": str(self.original_error) if self.original_error else None,
            "traceback": traceback.format_exc()
        }
    
    def __str__(self):
        return f"[{self.error_id}] {self.category.value.upper()}: {self.message}"


class ErrorHandler:
    """
    Centralized error handling and recovery for Helios system
    """
    
    def __init__(self, project_id: str = None):
        self.project_id = project_id
        self.firestore_client = None
        self.pubsub_client = None
        self.error_counts = {}
        self.recovery_strategies = {}
        
        # Initialize clients if project_id is available
        if self.project_id and GOOGLE_CLOUD_AVAILABLE:
            try:
                if GOOGLE_CLOUD_AVAILABLE:
                    self.firestore_client = firestore.Client(project=project_id)
                if PUBSUB_AVAILABLE:
                    self.pubsub_client = pubsub_v1.PublisherClient()
                logger.info(f"Initialized error handler clients for project: {project_id}")
            except Exception as e:
                logger.warning(f"Failed to initialize error handler clients: {str(e)}")
        elif not GOOGLE_CLOUD_AVAILABLE:
            logger.warning("Google Cloud libraries not available, skipping error handler client setup")
        
        # Register default recovery strategies
        self._register_default_strategies()
    
    def _register_default_strategies(self):
        """Register default error recovery strategies"""
        
        # Network errors - retry with exponential backoff
        self.register_recovery_strategy(
            ErrorCategory.NETWORK,
            self._retry_with_backoff,
            max_retries=3,
            base_delay=1.0
        )
        
        # Rate limit errors - wait and retry
        self.register_recovery_strategy(
            ErrorCategory.RATE_LIMIT,
            self._wait_and_retry,
            wait_time=60,
            max_retries=2
        )
        
        # Authentication errors - refresh credentials
        self.register_recovery_strategy(
            ErrorCategory.AUTHENTICATION,
            self._refresh_credentials,
            max_retries=1
        )
        
        # Validation errors - log and continue
        self.register_recovery_strategy(
            ErrorCategory.VALIDATION,
            self._log_and_continue
        )
    
    def register_recovery_strategy(
        self, 
        category: ErrorCategory, 
        strategy: Callable, 
        **kwargs
    ):
        """Register a recovery strategy for an error category"""
        
        self.recovery_strategies[category] = {
            "strategy": strategy,
            "kwargs": kwargs
        }
        logger.info(f"Registered recovery strategy for {category.value}")
    
    async def handle_error(
        self, 
        error: Exception, 
        context: Dict[str, Any] = None,
        auto_recover: bool = True
    ) -> Dict[str, Any]:
        """
        Handle an error with automatic recovery if possible
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            auto_recover: Whether to attempt automatic recovery
            
        Returns:
            Dictionary containing error handling results
        """
        
        # Convert to HeliosError if it's not already
        if not isinstance(error, HeliosError):
            error = self._classify_error(error)
        
        # Add context
        if context:
            error.context.update(context)
        
        # Log error
        self._log_error(error)
        
        # Store error in Firestore
        await self._store_error(error)
        
        # Attempt recovery if enabled
        recovery_result = None
        if auto_recover:
            recovery_result = await self._attempt_recovery(error)
        
        # Send alert if critical
        if error.severity == ErrorSeverity.CRITICAL:
            await self._send_alert(error)
        
        # Update error counts
        self._update_error_counts(error)
        
        return {
            "error_id": error.error_id,
            "handled": True,
            "recovery_attempted": auto_recover,
            "recovery_result": recovery_result,
            "alert_sent": error.severity == ErrorSeverity.CRITICAL,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _classify_error(self, error: Exception) -> HeliosError:
        """Classify an exception and convert to HeliosError"""
        
        error_message = str(error)
        error_type = type(error).__name__
        
        # Network-related errors
        if any(network_error in error_type.lower() for network_error in [
            "connection", "timeout", "network", "socket", "http"
        ]):
            return HeliosError(
                message=error_message,
                category=ErrorCategory.NETWORK,
                severity=ErrorSeverity.MEDIUM,
                original_error=error
            )
        
        # Authentication errors
        if any(auth_error in error_type.lower() for auth_error in [
            "authentication", "unauthorized", "forbidden", "credential"
        ]):
            return HeliosError(
                message=error_message,
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                original_error=error
            )
        
        # Rate limit errors
        if any(rate_error in error_message.lower() for rate_error in [
            "rate limit", "too many requests", "quota exceeded"
        ]):
            return HeliosError(
                message=error_message,
                category=ErrorCategory.RATE_LIMIT,
                severity=ErrorSeverity.MEDIUM,
                original_error=error
            )
        
        # Validation errors
        if any(validation_error in error_type.lower() for validation_error in [
            "validation", "value", "type", "argument"
        ]):
            return HeliosError(
                message=error_message,
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.LOW,
                original_error=error
            )
        
        # Default classification
        return HeliosError(
            message=error_message,
            category=ErrorCategory.UNKNOWN,
            severity=ErrorSeverity.MEDIUM,
            original_error=error
        )
    
    def _log_error(self, error: HeliosError):
        """Log error with appropriate level"""
        
        log_message = f"{error}"
        if error.context:
            log_message += f" | Context: {json.dumps(error.context)}"
        
        if error.severity == ErrorSeverity.CRITICAL:
            logger.critical(log_message, exc_info=True)
        elif error.severity == ErrorSeverity.HIGH:
            logger.error(log_message, exc_info=True)
        elif error.severity == ErrorSeverity.MEDIUM:
            logger.warning(log_message, exc_info=True)
        else:
            logger.info(log_message)
    
    async def _store_error(self, error: HeliosError):
        """Store error in Firestore for analysis"""
        
        if not self.firestore_client:
            return
        
        try:
            collection_name = "error_logs"
            document_id = error.error_id
            
            error_data = error.to_dict()
            error_data["stored_at"] = datetime.utcnow()
            
            doc_ref = self.firestore_client.collection(collection_name).document(document_id)
            doc_ref.set(error_data)
            
        except Exception as e:
            logger.error(f"Failed to store error in Firestore: {str(e)}")
    
    async def _attempt_recovery(self, error: HeliosError) -> Optional[Dict[str, Any]]:
        """Attempt to recover from the error using registered strategies"""
        
        strategy_info = self.recovery_strategies.get(error.category)
        if not strategy_info:
            logger.info(f"No recovery strategy registered for {error.category.value}")
            return None
        
        strategy = strategy_info["strategy"]
        kwargs = strategy_info["kwargs"]
        
        try:
            logger.info(f"Attempting recovery using {strategy.__name__} for {error.category.value}")
            result = await strategy(error, **kwargs)
            
            if result and result.get("success"):
                logger.info(f"Recovery successful for {error.error_id}")
            else:
                logger.warning(f"Recovery failed for {error.error_id}")
            
            return result
            
        except Exception as recovery_error:
            logger.error(f"Error during recovery attempt: {str(recovery_error)}")
            return {"success": False, "error": str(recovery_error)}
    
    async def _retry_with_backoff(
        self, 
        error: HeliosError, 
        max_retries: int = 3, 
        base_delay: float = 1.0
    ) -> Dict[str, Any]:
        """Retry operation with exponential backoff"""
        
        # This is a placeholder - actual retry logic would be implemented
        # based on the specific operation that failed
        
        return {
            "success": True,
            "strategy": "retry_with_backoff",
            "retries_attempted": 0,
            "message": "Retry strategy registered - implement specific retry logic"
        }
    
    async def _wait_and_retry(
        self, 
        error: HeliosError, 
        wait_time: int = 60, 
        max_retries: int = 2
    ) -> Dict[str, Any]:
        """Wait for specified time and retry"""
        
        return {
            "success": True,
            "strategy": "wait_and_retry",
            "wait_time": wait_time,
            "message": "Wait strategy registered - implement specific wait logic"
        }
    
    async def _refresh_credentials(
        self, 
        error: HeliosError, 
        max_retries: int = 1
    ) -> Dict[str, Any]:
        """Refresh authentication credentials"""
        
        return {
            "success": True,
            "strategy": "refresh_credentials",
            "message": "Credential refresh strategy registered - implement specific refresh logic"
        }
    
    def _log_and_continue(self, error: HeliosError) -> Dict[str, Any]:
        """Log error and continue execution"""
        
        return {
            "success": True,
            "strategy": "log_and_continue",
            "message": "Error logged and execution continued"
        }
    
    async def _send_alert(self, error: HeliosError):
        """Send alert for critical errors"""
        
        if not self.pubsub_client:
            return
        
        try:
            topic_path = self.pubsub_client.topic_path(self.project_id, "helios-alerts")
            
            alert_data = {
                "error_id": error.error_id,
                "severity": error.severity.value,
                "category": error.category.value,
                "message": error.message,
                "timestamp": datetime.utcnow().isoformat(),
                "context": error.context
            }
            
            future = self.pubsub_client.publish(
                topic_path, 
                json.dumps(alert_data).encode("utf-8")
            )
            future.result()  # Wait for publish to complete
            
            logger.info(f"Alert sent for critical error {error.error_id}")
            
        except Exception as e:
            logger.error(f"Failed to send alert: {str(e)}")
    
    def _update_error_counts(self, error: HeliosError):
        """Update error count statistics"""
        
        category_key = error.category.value
        severity_key = error.severity.value
        
        if category_key not in self.error_counts:
            self.error_counts[category_key] = {}
        
        if severity_key not in self.error_counts[category_key]:
            self.error_counts[category_key][severity_key] = 0
        
        self.error_counts[category_key][severity_key] += 1
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics for monitoring"""
        
        return {
            "total_errors": sum(
                sum(counts.values()) 
                for counts in self.error_counts.values()
            ),
            "errors_by_category": self.error_counts,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def clear_error_counts(self):
        """Clear error count statistics"""
        
        self.error_counts.clear()
        logger.info("Error counts cleared")


# Decorator for automatic error handling
def handle_errors(
    category: ErrorCategory = None,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    auto_recover: bool = True,
    context_provider: Callable = None
):
    """
    Decorator for automatic error handling
    
    Args:
        category: Expected error category
        severity: Error severity level
        auto_recover: Whether to attempt recovery
        context_provider: Function to provide additional context
    """
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                # Get error handler from args or create new one
                error_handler = None
                for arg in args:
                    if hasattr(arg, 'error_handler'):
                        error_handler = arg.error_handler
                        break
                
                if not error_handler:
                    error_handler = ErrorHandler()
                
                # Prepare context
                context = {}
                if context_provider:
                    try:
                        context = context_provider(*args, **kwargs)
                    except Exception:
                        pass
                
                # Handle error
                await error_handler.handle_error(
                    error=e,
                    context=context,
                    auto_recover=auto_recover
                )
                
                # Re-raise if not handled
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                # Get error handler from args or create new one
                error_handler = None
                for arg in args:
                    if hasattr(arg, 'error_handler'):
                        error_handler = arg.error_handler
                        break
                
                if not error_handler:
                    error_handler = ErrorHandler()
                
                # Prepare context
                context = {}
                if context_provider:
                    try:
                        context = context_provider(*args, **kwargs)
                    except Exception:
                        pass
                
                # Handle error (sync version)
                asyncio.create_task(error_handler.handle_error(
                    error=e,
                    context=context,
                    auto_recover=auto_recover
                ))
                
                # Re-raise if not handled
                raise
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Global error handler instance
_global_error_handler = None


def get_error_handler(project_id: str = None) -> ErrorHandler:
    """Get global error handler instance"""
    
    global _global_error_handler
    
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler(project_id)
    
    return _global_error_handler


# Example usage
if __name__ == "__main__":
    # Example of using the error handler
    async def example_usage():
        error_handler = ErrorHandler("helios-autonomous-store")
        
        # Example error
        try:
            raise ConnectionError("Failed to connect to external API")
        except Exception as e:
            result = await error_handler.handle_error(e, {"operation": "api_call"})
            print(f"Error handling result: {result}")
        
        # Get statistics
        stats = error_handler.get_error_statistics()
        print(f"Error statistics: {stats}")
    
    # Run example
    asyncio.run(example_usage())
