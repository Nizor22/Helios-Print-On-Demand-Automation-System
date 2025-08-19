"""
Performance Monitoring Utility for Helios Autonomous Store
Tracks execution times, resource usage, and performance metrics
"""

import asyncio
import time
import logging
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
import json
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime, timedelta, timezone
from functools import wraps
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, asdict
from collections import defaultdict, deque

try:
    from google.cloud import firestore
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False

try:
    from google.cloud import monitoring_v3
    MONITORING_AVAILABLE = True
except ImportError:
    MONITORING_AVAILABLE = False

try:
    from google.cloud import pubsub_v1
    PUBSUB_AVAILABLE = True
except ImportError:
    PUBSUB_AVAILABLE = False

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    
    operation_name: str
    execution_time: float
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    context: Dict[str, Any] = None
    resource_usage: Dict[str, float] = None
    metadata: Dict[str, Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


class PerformanceMonitor:
    """
    Performance monitoring and metrics collection for Helios system
    """
    
    def __init__(self, project_id: str = None, enable_cloud_monitoring: bool = True):
        self.project_id = project_id
        self.enable_cloud_monitoring = enable_cloud_monitoring
        
        # Metrics storage
        self.metrics: deque = deque(maxlen=10000)  # Keep last 10k metrics
        self.operation_stats: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self.resource_baseline: Dict[str, float] = {}
        
        # Cloud clients
        self.firestore_client = None
        self.monitoring_client = None
        self.pubsub_client = None
        
        # Initialize cloud clients if project_id is available
        if self.project_id and enable_cloud_monitoring:
            self._initialize_cloud_clients()
        
        # Performance thresholds
        self.thresholds = {
            "execution_time_warning": 5.0,  # seconds
            "execution_time_critical": 15.0,  # seconds
            "memory_usage_warning": 80.0,  # percentage
            "memory_usage_critical": 95.0,  # percentage
            "cpu_usage_warning": 70.0,  # percentage
            "cpu_usage_critical": 90.0  # percentage
        }
        
        # Start resource monitoring
        self._start_resource_monitoring()
    
    def _initialize_cloud_clients(self):
        """Initialize Google Cloud clients for monitoring"""
        
        if not GOOGLE_CLOUD_AVAILABLE:
            logger.warning("Google Cloud libraries not available, skipping cloud monitoring setup")
            self.enable_cloud_monitoring = False
            return
        
        try:
            if GOOGLE_CLOUD_AVAILABLE:
                self.firestore_client = firestore.Client(project=self.project_id)
            if MONITORING_AVAILABLE:
                self.monitoring_client = monitoring_v3.MetricServiceClient()
            if PUBSUB_AVAILABLE:
                self.pubsub_client = pubsub_v1.PublisherClient()
            logger.info(f"Initialized cloud monitoring clients for project: {self.project_id}")
        except Exception as e:
            logger.warning(f"Failed to initialize cloud monitoring clients: {str(e)}")
            self.enable_cloud_monitoring = False
    
    def _start_resource_monitoring(self):
        """Start background resource monitoring"""
        
        # Set initial baseline
        self._update_resource_baseline()
        
        # Start monitoring task
        asyncio.create_task(self._resource_monitoring_loop())
    
    def _update_resource_baseline(self):
        """Update resource usage baseline"""
        
        try:
            if PSUTIL_AVAILABLE:
                cpu_percent = psutil.cpu_percent(interval=1)
                memory = psutil.virtual_memory()
                
                self.resource_baseline = {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available": memory.available / (1024**3),  # GB
                    "disk_usage": psutil.disk_usage('/').percent
                }
            else:
                # Fallback when psutil is not available
                self.resource_baseline = {
                    "cpu_percent": 0.0,
                    "memory_percent": 0.0,
                    "memory_available": 0.0,
                    "disk_usage": 0.0
                }
            
        except Exception as e:
            logger.warning(f"Failed to update resource baseline: {str(e)}")
            # Set fallback values on error
            self.resource_baseline = {
                "cpu_percent": 0.0,
                "memory_percent": 0.0,
                "memory_available": 0.0,
                "disk_usage": 0.0
            }
    
    async def _resource_monitoring_loop(self):
        """Background resource monitoring loop"""
        
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                self._update_resource_baseline()
                
                # Check for resource alerts
                await self._check_resource_alerts()
                
            except Exception as e:
                logger.error(f"Error in resource monitoring loop: {str(e)}")
    
    async def _check_resource_alerts(self):
        """Check for resource usage alerts"""
        
        try:
            current_cpu = self.resource_baseline.get("cpu_percent", 0)
            current_memory = self.resource_baseline.get("memory_percent", 0)
            
            alerts = []
            
            # CPU alerts
            if current_cpu >= self.thresholds["cpu_usage_critical"]:
                alerts.append({
                    "type": "cpu_usage",
                    "severity": "critical",
                    "value": current_cpu,
                    "threshold": self.thresholds["cpu_usage_critical"]
                })
            elif current_cpu >= self.thresholds["cpu_usage_warning"]:
                alerts.append({
                    "type": "cpu_usage",
                    "severity": "warning",
                    "value": current_cpu,
                    "threshold": self.thresholds["cpu_usage_warning"]
                })
            
            # Memory alerts
            if current_memory >= self.thresholds["memory_usage_critical"]:
                alerts.append({
                    "type": "memory_usage",
                    "severity": "critical",
                    "value": current_memory,
                    "threshold": self.thresholds["memory_usage_critical"]
                })
            elif current_memory >= self.thresholds["memory_usage_warning"]:
                alerts.append({
                    "type": "memory_usage",
                    "severity": "warning",
                    "value": current_memory,
                    "threshold": self.thresholds["memory_usage_warning"]
                })
            
            # Send alerts if any
            for alert in alerts:
                await self._send_resource_alert(alert)
                
        except Exception as e:
            logger.error(f"Error checking resource alerts: {str(e)}")
    
    async def _send_resource_alert(self, alert: Dict[str, Any]):
        """Send resource usage alert"""
        
        if not self.pubsub_client:
            return
        
        try:
            topic_path = self.pubsub_client.topic_path(self.project_id, "helios-resource-alerts")
            
            alert_data = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "project_id": self.project_id,
                "alert": alert
            }
            
            future = self.pubsub_client.publish(
                topic_path,
                json.dumps(alert_data).encode("utf-8")
            )
            future.result()
            
            logger.warning(f"Resource alert sent: {alert}")
            
        except Exception as e:
            logger.error(f"Failed to send resource alert: {str(e)}")
    
    def record_metric(self, metric: PerformanceMetric):
        """Record a performance metric"""
        
        # Add to local storage
        self.metrics.append(metric)
        
        # Update operation statistics
        self._update_operation_stats(metric)
        
        # Check for performance alerts
        self._check_performance_alerts(metric)
        
        # Store in Firestore if available
        if self.firestore_client:
            asyncio.create_task(self._store_metric(metric))
        
        # Send to Cloud Monitoring if enabled
        if self.enable_cloud_monitoring and self.monitoring_client:
            asyncio.create_task(self._send_to_cloud_monitoring(metric))

    def record_metric_with_labels(self, metric_name: str, value: float, labels: Dict[str, str] = None, timestamp: datetime = None):
        """Record a performance metric with labels (compatibility method)"""
        
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Create a PerformanceMetric object
        metric = PerformanceMetric(
            operation_name=metric_name,
            execution_time=value,
            timestamp=timestamp,
            success=True,
            context=labels or {}
        )
        
        # Record using the standard method
        self.record_metric(metric)

    async def track_metric(self, metric_name: str, data: Dict[str, Any]):
        """Compatibility shim for existing callers expecting an async track_metric.
        Records a metric using record_metric_with_labels with execution_time from data
        if available, otherwise 0.0.
        """
        try:
            value = float(data.get("execution_time", data.get("processing_time_ms", 0.0)))
            # Convert ms to seconds if the value looks like milliseconds
            if value and value > 100:  # heuristic
                value = value / 1000.0
        except Exception:
            value = 0.0
        labels = {k: str(v) for k, v in (data or {}).items() if k not in ("execution_time", "processing_time_ms")}
        self.record_metric_with_labels(metric_name, value, labels)
    
    def _update_operation_stats(self, metric: PerformanceMetric):
        """Update operation statistics"""
        
        op_name = metric.operation_name
        
        if op_name not in self.operation_stats:
            self.operation_stats[op_name] = {
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "total_execution_time": 0.0,
                "min_execution_time": float('inf'),
                "max_execution_time": 0.0,
                "last_execution": None,
                "error_rate": 0.0
            }
        
        stats = self.operation_stats[op_name]
        stats["total_executions"] += 1
        stats["total_execution_time"] += metric.execution_time
        
        if metric.success:
            stats["successful_executions"] += 1
        else:
            stats["failed_executions"] += 1
        
        stats["min_execution_time"] = min(stats["min_execution_time"], metric.execution_time)
        stats["max_execution_time"] = max(stats["max_execution_time"], metric.execution_time)
        stats["last_execution"] = metric.timestamp
        
        # Calculate error rate
        stats["error_rate"] = stats["failed_executions"] / stats["total_executions"]
        
        # Calculate average execution time
        stats["avg_execution_time"] = stats["total_execution_time"] / stats["total_executions"]
    
    def _check_performance_alerts(self, metric: PerformanceMetric):
        """Check for performance alerts"""
        
        if metric.execution_time >= self.thresholds["execution_time_critical"]:
            logger.critical(
                f"Critical performance alert: {metric.operation_name} took "
                f"{metric.execution_time:.2f}s (threshold: {self.thresholds['execution_time_critical']}s)"
            )
        elif metric.execution_time >= self.thresholds["execution_time_warning"]:
            logger.warning(
                f"Performance warning: {metric.operation_name} took "
                f"{metric.execution_time:.2f}s (threshold: {self.thresholds['execution_time_warning']}s)"
            )
    
    async def _store_metric(self, metric: PerformanceMetric):
        """Store metric in Firestore"""
        
        try:
            collection_name = "performance_metrics"
            document_id = f"{metric.operation_name}_{metric.timestamp.strftime('%Y%m%d_%H%M%S_%f')}"
            
            doc_ref = self.firestore_client.collection(collection_name).document(document_id)
            doc_ref.set(metric.to_dict())
            
        except Exception as e:
            logger.error(f"Failed to store metric in Firestore: {str(e)}")
    
    async def _send_to_cloud_monitoring(self, metric: PerformanceMetric):
        """Send metric to Google Cloud Monitoring"""
        
        try:
            # Create time series data point
            time_series = monitoring_v3.TimeSeries()
            time_series.metric.type = f"custom.googleapis.com/helios/{metric.operation_name}"
            time_series.metric.labels["operation"] = metric.operation_name
            time_series.metric.labels["success"] = str(metric.success).lower()
            
            # Set resource
            time_series.resource.type = "global"
            time_series.resource.labels["project_id"] = self.project_id
            
            # Set data point
            point = monitoring_v3.Point()
            point.interval.end_time.FromDatetime(metric.timestamp)
            point.value.double_value = metric.execution_time
            time_series.points = [point]
            
            # Send to monitoring
            project_name = f"projects/{self.project_id}"
            self.monitoring_client.create_time_series(
                request={
                    "name": project_name,
                    "time_series": [time_series]
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to send metric to Cloud Monitoring: {str(e)}")
    
    def get_operation_stats(self, operation_name: str = None) -> Dict[str, Any]:
        """Get performance statistics for operations"""
        
        if operation_name:
            return self.operation_stats.get(operation_name, {})
        
        return dict(self.operation_stats)
    
    def get_recent_metrics(
        self, 
        operation_name: str = None, 
        minutes: int = 60
    ) -> List[PerformanceMetric]:
        """Get recent metrics within specified time window"""
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        
        if operation_name:
            return [
                metric for metric in self.metrics
                if metric.operation_name == operation_name and metric.timestamp >= cutoff_time
            ]
        
        return [
            metric for metric in self.metrics
            if metric.timestamp >= cutoff_time
        ]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary"""
        
        total_metrics = len(self.metrics)
        if total_metrics == 0:
            return {"message": "No metrics recorded yet"}
        
        # Calculate overall statistics
        all_times = [metric.execution_time for metric in self.metrics]
        success_count = sum(1 for metric in self.metrics if metric.success)
        
        summary = {
            "total_operations": total_metrics,
            "successful_operations": success_count,
            "failed_operations": total_metrics - success_count,
            "overall_success_rate": success_count / total_metrics,
            "execution_time_stats": {
                "min": min(all_times),
                "max": max(all_times),
                "average": sum(all_times) / len(all_times)
            },
            "operation_breakdown": dict(self.operation_stats),
            "resource_baseline": self.resource_baseline,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return summary
    
    def clear_metrics(self):
        """Clear all stored metrics"""
        
        self.metrics.clear()
        self.operation_stats.clear()
        logger.info("All performance metrics cleared")
    
    def set_thresholds(self, **kwargs):
        """Set performance thresholds"""
        
        for key, value in kwargs.items():
            if key in self.thresholds:
                self.thresholds[key] = value
                logger.info(f"Updated threshold {key}: {value}")
            else:
                logger.warning(f"Unknown threshold key: {key}")

    async def close(self):
        """Clean up resources and close connections"""
        try:
            logger.info("🧹 Cleaning up PerformanceMonitor...")
            
            # Close cloud clients if they exist
            if hasattr(self, 'firestore_client') and self.firestore_client:
                try:
                    self.firestore_client.close()
                except Exception:
                    pass
                self.firestore_client = None
            
            if hasattr(self, 'monitoring_client') and self.monitoring_client:
                try:
                    self.monitoring_client.close()
                except Exception:
                    pass
                self.monitoring_client = None
            
            if hasattr(self, 'pubsub_client') and self.pubsub_client:
                try:
                    self.pubsub_client.close()
                except Exception:
                    pass
                self.pubsub_client = None
            
            logger.info("✅ PerformanceMonitor cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Error during PerformanceMonitor cleanup: {str(e)}")


# Performance monitoring decorators
def monitor_performance(operation_name: str = None, context_provider: Callable = None):
    """
    Decorator to monitor function performance
    
    Args:
        operation_name: Name for the operation (defaults to function name)
        context_provider: Function to provide additional context
    """
    
    def decorator(func):
        op_name = operation_name or func.__name__
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            context = {}
            
            try:
                # Get context if provider is available
                if context_provider:
                    try:
                        context = context_provider(*args, **kwargs)
                    except Exception:
                        pass
                
                # Execute function
                result = await func(*args, **kwargs)
                return result
                
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                # Record metric
                execution_time = time.time() - start_time
                
                # Get resource usage
                resource_usage = {}
                try:
                    process = psutil.Process()
                    resource_usage = {
                        "cpu_percent": process.cpu_percent(),
                        "memory_percent": process.memory_percent(),
                        "memory_rss": process.memory_info().rss / (1024**2)  # MB
                    }
                except Exception:
                    pass
                
                metric = PerformanceMetric(
                    operation_name=op_name,
                    execution_time=execution_time,
                    timestamp=datetime.now(timezone.utc),
                    success=success,
                    error_message=error_message,
                    context=context,
                    resource_usage=resource_usage
                )
                
                # Get global monitor instance
                monitor = get_performance_monitor()
                monitor.record_metric(metric)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            success = True
            error_message = None
            context = {}
            
            try:
                # Get context if provider is available
                if context_provider:
                    try:
                        context = context_provider(*args, **kwargs)
                    except Exception:
                        pass
                
                # Execute function
                result = func(*args, **kwargs)
                return result
                
            except Exception as e:
                success = False
                error_message = str(e)
                raise
            finally:
                # Record metric
                execution_time = time.time() - start_time
                
                # Get resource usage
                resource_usage = {}
                try:
                    process = psutil.Process()
                    resource_usage = {
                        "cpu_percent": process.cpu_percent(),
                        "memory_percent": process.memory_percent(),
                        "memory_rss": process.memory_info().rss / (1024**2)  # MB
                    }
                except Exception:
                    pass
                
                metric = PerformanceMetric(
                    operation_name=op_name,
                    execution_time=execution_time,
                    timestamp=datetime.now(timezone.utc),
                    success=success,
                    error_message=error_message,
                    context=context,
                    resource_usage=resource_usage
                )
                
                # Get global monitor instance
                monitor = get_performance_monitor()
                monitor.record_metric(metric)
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


@contextmanager
def performance_context(operation_name: str, context: Dict[str, Any] = None):
    """Context manager for performance monitoring"""
    
    start_time = time.time()
    success = True
    error_message = None
    
    try:
        yield
    except Exception as e:
        success = False
        error_message = str(e)
        raise
    finally:
        execution_time = time.time() - start_time
        
        metric = PerformanceMetric(
            operation_name=operation_name,
            execution_time=execution_time,
            timestamp=datetime.utcnow(),
            success=success,
            error_message=error_message,
            context=context or {}
        )
        
        monitor = get_performance_monitor()
        monitor.record_metric(metric)


@asynccontextmanager
async def async_performance_context(operation_name: str, context: Dict[str, Any] = None):
    """Async context manager for performance monitoring"""
    
    start_time = time.time()
    success = True
    error_message = None
    
    try:
        yield
    except Exception as e:
        success = False
        error_message = str(e)
        raise
    finally:
        execution_time = time.time() - start_time
        
        metric = PerformanceMetric(
            operation_name=operation_name,
            execution_time=execution_time,
            timestamp=datetime.utcnow(),
            success=success,
            error_message=error_message,
            context=context or {}
        )
        
        monitor = get_performance_monitor()
        monitor.record_metric(metric)


# Global performance monitor instance
_global_monitor = None


def get_performance_monitor(project_id: str = None) -> PerformanceMonitor:
    """Get global performance monitor instance"""
    
    global _global_monitor
    
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor(project_id)
    
    return _global_monitor


# Example usage
if __name__ == "__main__":
    # Example of using the performance monitor
    async def example_usage():
        monitor = PerformanceMonitor("helios-autonomous-store")
        
        # Example operation
        @monitor_performance("example_operation")
        async def example_operation():
            await asyncio.sleep(1)  # Simulate work
            return "success"
        
        # Execute operation
        result = await example_operation()
        print(f"Operation result: {result}")
        
        # Get performance summary
        summary = monitor.get_performance_summary()
        print(f"Performance summary: {json.dumps(summary, indent=2)}")
    
    # Run example
    asyncio.run(example_usage())
