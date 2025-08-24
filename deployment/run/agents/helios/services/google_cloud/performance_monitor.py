from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
from loguru import logger

from ...config import HeliosConfig
from .monitoring_dashboard import CloudMonitoringDashboard


@dataclass
class PerformanceMetric:
    """Individual performance metric"""
    name: str
    value: float
    timestamp: datetime
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceSnapshot:
    """Snapshot of performance metrics at a point in time"""
    timestamp: datetime
    metrics: List[PerformanceMetric] = field(default_factory=list)
    pipeline_status: str = "unknown"
    execution_time: float = 0.0
    success_rate: float = 0.0
    error_count: int = 0


@dataclass
class PerformanceAnalysis:
    """Analysis of performance data"""
    success_prediction: float  # 0.0 to 1.0
    optimization_triggers: List[str]
    recommendations: List[str]
    performance_score: float  # 0.0 to 10.0
    bottlenecks: List[str]
    efficiency_metrics: Dict[str, float]


class CloudPerformanceReporter:
    """Performance monitoring service for Helios"""
    
    def __init__(self, config: HeliosConfig):
        self.config = config
        self.metrics_buffer: List[PerformanceMetric] = []
        self.performance_history: List[PerformanceSnapshot] = []
        self.monitoring_dashboard = CloudMonitoringDashboard(config)
        
        # Performance thresholds
        self.execution_time_threshold = config.max_execution_time
        self.success_rate_threshold = 0.85
        self.error_rate_threshold = 0.15
        
        # Initialize monitoring if enabled
        if config.enable_performance_monitoring:
            logger.info("✅ Performance monitoring initialized")
        else:
            logger.info("⚠️ Performance monitoring disabled")
    
    async def record_metric(self, name: str, value: float, labels: Dict[str, str] = None, 
                          metadata: Dict[str, Any] = None) -> None:
        """Record a performance metric"""
        try:
            metric = PerformanceMetric(
                name=name,
                value=value,
                timestamp=datetime.utcnow(),
                labels=labels or {},
                metadata=metadata or {}
            )
            
            self.metrics_buffer.append(metric)
            
            # Flush buffer if it gets too large
            if len(self.metrics_buffer) >= 100:
                await self.flush_metrics()
                
            logger.debug(f"📊 Metric recorded: {name} = {value}")
            
        except Exception as e:
            logger.error(f"❌ Failed to record metric {name}: {e}")
    
    async def record_pipeline_metric(self, pipeline_data: Dict[str, Any]) -> None:
        """Record pipeline-specific performance metrics"""
        try:
            timestamp = datetime.utcnow()
            
            # Record execution time
            execution_time = pipeline_data.get("pipeline_execution_time", 0)
            await self.record_metric(
                "custom.googleapis.com/helios/pipeline_execution_time",
                execution_time,
                labels={
                    "trend_name": pipeline_data.get("trend_data", {}).get("trend_name", "unknown"),
                    "stage": "complete",
                    "status": pipeline_data.get("status", "unknown")
                }
            )
            
            # Record trend opportunity score
            if "ceo_decision" in pipeline_data:
                opportunity_score = pipeline_data["ceo_decision"].get("opportunity_score", 0)
                await self.record_metric(
                    "custom.googleapis.com/helios/trend_opportunity_score",
                    opportunity_score,
                    labels={
                        "trend_name": pipeline_data["ceo_decision"].get("trend_name", "unknown"),
                        "category": pipeline_data["ceo_decision"].get("category", "unknown"),
                        "source": pipeline_data["ceo_decision"].get("source", "unknown")
                    }
                )
            
            # Record audience confidence
            if "audience_result" in pipeline_data:
                confidence = pipeline_data["audience_result"].get("confidence_score", 0)
                await self.record_metric(
                    "custom.googleapis.com/helios/audience_confidence",
                    confidence,
                    labels={
                        "trend_name": pipeline_data.get("trend_data", {}).get("trend_name", "unknown"),
                        "demographic_cluster": pipeline_data["audience_result"].get("primary_persona", {}).get("demographic_cluster", "unknown"),
                        "persona_type": pipeline_data["audience_result"].get("primary_persona", {}).get("persona_type", "unknown")
                    }
                )
            
            # Record design generation success
            if "creative_result" in pipeline_data:
                designs = pipeline_data["creative_result"].get("designs", [])
                success_rate = 1.0 if designs else 0.0
                await self.record_metric(
                    "custom.googleapis.com/helios/design_generation_success",
                    success_rate,
                    labels={
                        "trend_name": pipeline_data.get("trend_data", {}).get("trend_name", "unknown"),
                        "product_type": "mixed",
                        "design_style": "ai_generated"
                    }
                )
            
            # Record publication success
            if "publish_results" in pipeline_data:
                publish_results = pipeline_data["publish_results"]
                if publish_results:
                    successful_pubs = sum(1 for r in publish_results if r.get("status") == "published")
                    success_rate = successful_pubs / len(publish_results) if publish_results else 0.0
                    await self.record_metric(
                        "custom.googleapis.com/helios/publication_success",
                        success_rate,
                        labels={
                            "trend_name": pipeline_data.get("trend_data", {}).get("trend_name", "unknown"),
                            "product_type": "mixed",
                            "sales_channel": "etsy"
                        }
                    )
            
            # Create performance snapshot
            snapshot = PerformanceSnapshot(
                timestamp=timestamp,
                execution_time=execution_time,
                pipeline_status=pipeline_data.get("status", "unknown"),
                success_rate=1.0 if pipeline_data.get("status") == "success" else 0.0,
                error_count=1 if pipeline_data.get("status") == "error" else 0
            )
            
            self.performance_history.append(snapshot)
            
            # Keep only last 1000 snapshots
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
            
            logger.info(f"📊 Pipeline metrics recorded: execution_time={execution_time}s, status={pipeline_data.get('status')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to record pipeline metrics: {e}")
    
    async def record_stage_metric(self, stage_name: str, stage_data: Dict[str, Any]) -> None:
        """Record stage-specific performance metrics"""
        try:
            # Record stage execution time
            if "execution_time" in stage_data:
                await self.record_metric(
                    "custom.googleapis.com/helios/stage_execution_time",
                    stage_data["execution_time"],
                    labels={
                        "stage": stage_name,
                        "status": stage_data.get("status", "unknown")
                    }
                )
            
            # Record stage-specific metrics
            if stage_name == "discovery":
                await self._record_discovery_metrics(stage_data)
            elif stage_name == "analysis":
                await self._record_analysis_metrics(stage_data)
            elif stage_name == "ethics":
                await self._record_ethics_metrics(stage_data)
            elif stage_name == "creative":
                await self._record_creative_metrics(stage_data)
            elif stage_name == "publication":
                await self._record_publication_metrics(stage_data)
            
        except Exception as e:
            logger.error(f"❌ Failed to record stage metrics for {stage_name}: {e}")
    
    async def _record_discovery_metrics(self, stage_data: Dict[str, Any]) -> None:
        """Record trend discovery metrics"""
        if "trend_data" in stage_data:
            trend_data = stage_data["trend_data"]
            await self.record_metric(
                "custom.googleapis.com/helios/trend_discovery_quality",
                trend_data.get("opportunity_score", 0),
                labels={
                    "trend_name": trend_data.get("trend_name", "unknown"),
                    "source": trend_data.get("source", "unknown"),
                    "category": trend_data.get("category", "unknown")
                }
            )
    
    async def _record_analysis_metrics(self, stage_data: Dict[str, Any]) -> None:
        """Record audience analysis metrics"""
        if "audience_result" in stage_data:
            audience = stage_data["audience_result"]
            await self.record_metric(
                "custom.googleapis.com/helios/audience_analysis_quality",
                audience.get("confidence_score", 0),
                labels={
                    "demographic_cluster": audience.get("primary_persona", {}).get("demographic_cluster", "unknown"),
                    "persona_type": audience.get("primary_persona", {}).get("persona_type", "unknown")
                }
            )
    
    async def _record_ethics_metrics(self, stage_data: Dict[str, Any]) -> None:
        """Record ethics screening metrics"""
        if "ethics_result" in stage_data:
            ethics = stage_data["ethics_result"]
            await self.record_metric(
                "custom.googleapis.com/helios/ethics_screening_result",
                1.0 if ethics.get("status") == "approved" else 0.0,
                labels={
                    "status": ethics.get("status", "unknown"),
                    "risk_level": ethics.get("risk_level", "unknown")
                }
            )
    
    async def _record_creative_metrics(self, stage_data: Dict[str, Any]) -> None:
        """Record creative generation metrics"""
        if "creative_result" in stage_data:
            creative = stage_data["creative_result"]
            designs = creative.get("designs", [])
            await self.record_metric(
                "custom.googleapis.com/helios/design_generation_count",
                len(designs),
                labels={
                    "design_style": "ai_generated",
                    "product_type": "mixed"
                }
            )
    
    async def _record_publication_metrics(self, stage_data: Dict[str, Any]) -> None:
        """Record publication metrics"""
        if "publish_results" in stage_data:
            results = stage_data["publish_results"]
            if results:
                successful = sum(1 for r in results if r.get("status") == "published")
                await self.record_metric(
                    "custom.googleapis.com/helios/publication_success_count",
                    successful,
                    labels={
                        "sales_channel": "etsy",
                        "product_type": "mixed"
                    }
                )
    
    async def analyze_performance(self, time_window: timedelta = timedelta(hours=24)) -> PerformanceAnalysis:
        """Analyze performance over a time window"""
        try:
            cutoff_time = datetime.utcnow() - time_window
            recent_snapshots = [
                s for s in self.performance_history 
                if s.timestamp >= cutoff_time
            ]
            
            if not recent_snapshots:
                return PerformanceAnalysis(
                    success_prediction=0.5,
                    optimization_triggers=["insufficient_data"],
                    recommendations=["Collect more performance data"],
                    performance_score=5.0,
                    bottlenecks=[],
                    efficiency_metrics={}
                )
            
            # Calculate key metrics
            total_executions = len(recent_snapshots)
            successful_executions = sum(1 for s in recent_snapshots if s.pipeline_status == "success")
            success_rate = successful_executions / total_executions if total_executions > 0 else 0.0
            
            avg_execution_time = sum(s.execution_time for s in recent_snapshots) / total_executions
            error_rate = sum(s.error_count for s in recent_snapshots) / total_executions
            
            # Calculate performance score (0-10)
            time_score = max(0, 10 - (avg_execution_time / self.execution_time_threshold) * 5)
            success_score = success_rate * 5
            error_penalty = error_rate * 3
            performance_score = min(10, max(0, time_score + success_score - error_penalty))
            
            # Identify optimization triggers
            optimization_triggers = []
            if avg_execution_time > self.execution_time_threshold:
                optimization_triggers.append("execution_time_exceeds_threshold")
            if success_rate < self.success_rate_threshold:
                optimization_triggers.append("success_rate_below_threshold")
            if error_rate > self.error_rate_threshold:
                optimization_triggers.append("error_rate_above_threshold")
            
            # Generate recommendations
            recommendations = []
            if "execution_time_exceeds_threshold" in optimization_triggers:
                recommendations.append("Optimize pipeline stages to reduce execution time")
            if "success_rate_below_threshold" in optimization_triggers:
                recommendations.append("Investigate and fix pipeline failures")
            if "error_rate_above_threshold" in optimization_triggers:
                recommendations.append("Improve error handling and retry logic")
            
            # Identify bottlenecks
            bottlenecks = []
            if avg_execution_time > 300:  # 5 minutes
                bottlenecks.append("pipeline_execution_time")
            if success_rate < 0.8:
                bottlenecks.append("pipeline_success_rate")
            
            # Calculate efficiency metrics
            efficiency_metrics = {
                "avg_execution_time": avg_execution_time,
                "success_rate": success_rate,
                "error_rate": error_rate,
                "throughput_per_hour": total_executions / (time_window.total_seconds() / 3600),
                "performance_score": performance_score
            }
            
            # Predict success probability
            success_prediction = success_rate * 0.7 + (1 - error_rate) * 0.3
            
            return PerformanceAnalysis(
                success_prediction=success_prediction,
                optimization_triggers=optimization_triggers,
                recommendations=recommendations,
                performance_score=performance_score,
                bottlenecks=bottlenecks,
                efficiency_metrics=efficiency_metrics
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to analyze performance: {e}")
            return PerformanceAnalysis(
                success_prediction=0.5,
                optimization_triggers=["analysis_error"],
                recommendations=["Fix performance analysis"],
                performance_score=5.0,
                bottlenecks=[],
                efficiency_metrics={}
            )
    
    async def flush_metrics(self) -> None:
        """Flush buffered metrics to Cloud Monitoring"""
        if not self.metrics_buffer:
            return
            
        try:
            # Write metrics to Cloud Monitoring
            await self._write_metrics_to_cloud_monitoring()
            
            # Clear the buffer after successful write
            self.metrics_buffer.clear()
            self.logger.info(f"Successfully flushed {len(self.metrics_buffer)} metrics to Cloud Monitoring")
            
        except Exception as e:
            self.logger.error(f"Failed to flush metrics to Cloud Monitoring: {e}")
            # Keep metrics in buffer for retry on next flush

    async def _write_metrics_to_cloud_monitoring(self) -> None:
        """Write buffered metrics to Google Cloud Monitoring"""
        try:
            # Import here to avoid circular imports
            from google.cloud import monitoring_v3
            from google.protobuf.timestamp_pb2 import Timestamp
            
            # Initialize monitoring client
            client = monitoring_v3.MetricServiceClient()
            project_name = f"projects/{self.config.google_cloud.project_id}"
            
            # Group metrics by type for efficient writing
            time_series_data = []
            
            for metric in self.metrics_buffer:
                # Create time series point
                point = monitoring_v3.Point()
                point.interval.end_time.FromDatetime(metric.timestamp)
                point.value.double_value = metric.value
                
                # Create time series
                time_series = monitoring_v3.TimeSeries()
                time_series.metric.type = metric.name
                time_series.resource.type = "global"
                time_series.resource.labels["project_id"] = self.config.google_cloud.project_id
                
                # Add labels
                for key, value in metric.labels.items():
                    time_series.metric.labels[key] = str(value)
                
                time_series.points = [point]
                time_series_data.append(time_series)
            
            # Write time series data in batches
            batch_size = 200  # Cloud Monitoring limit
            for i in range(0, len(time_series_data), batch_size):
                batch = time_series_data[i:i + batch_size]
                client.create_time_series(
                    request={
                        "name": project_name,
                        "time_series": batch
                    }
                )
                
            self.logger.info(f"Successfully wrote {len(time_series_data)} time series to Cloud Monitoring")
            
        except ImportError:
            self.logger.warning("Google Cloud Monitoring client not available, metrics will be logged only")
        except Exception as e:
            self.logger.error(f"Failed to write metrics to Cloud Monitoring: {e}")
            raise
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of current performance"""
        try:
            # Analyze recent performance
            analysis = await self.analyze_performance()
            
            # Get current metrics
            current_metrics = {
                "total_metrics_recorded": len(self.metrics_buffer) + len(self.performance_history),
                "metrics_in_buffer": len(self.metrics_buffer),
                "snapshots_in_history": len(self.performance_history)
            }
            
            # Get recent performance trends
            if self.performance_history:
                recent = self.performance_history[-10:]  # Last 10 snapshots
                current_metrics.update({
                    "recent_success_rate": sum(1 for s in recent if s.pipeline_status == "success") / len(recent),
                    "recent_avg_execution_time": sum(s.execution_time for s in recent) / len(recent),
                    "last_execution_time": self.performance_history[-1].execution_time if self.performance_history else 0
                })
            
            return {
                "status": "success",
                "performance_analysis": analysis,
                "current_metrics": current_metrics,
                "monitoring_enabled": self.config.enable_performance_monitoring,
                "cloud_monitoring_enabled": self.config.enable_cloud_monitoring
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get performance summary: {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    async def setup_monitoring_infrastructure(self) -> None:
        """Set up complete monitoring infrastructure"""
        try:
            self.logger.info("Setting up Helios monitoring infrastructure...")
            
            # Set up all monitoring components
            await self.monitoring_dashboard.setup_complete_monitoring()
            
            # Start periodic metric flushing
            await self._start_metric_flushing()
            
            self.logger.info("✅ Helios monitoring infrastructure setup complete")
            
        except Exception as e:
            self.logger.error(f"Failed to setup monitoring infrastructure: {e}")
            raise

    async def _start_metric_flushing(self) -> None:
        """Start periodic metric flushing to Cloud Monitoring"""
        try:
            import asyncio
            
            async def flush_loop():
                while True:
                    try:
                        await asyncio.sleep(30)  # Flush every 30 seconds
                        await self.flush_metrics()
                    except Exception as e:
                        self.logger.error(f"Error in metric flush loop: {e}")
                        await asyncio.sleep(5)  # Wait before retry
            
            # Start the flush loop in the background
            asyncio.create_task(flush_loop())
            self.logger.info("Started periodic metric flushing (every 30 seconds)")
            
        except ImportError:
            self.logger.warning("asyncio not available, periodic flushing disabled")
        except Exception as e:
            self.logger.error(f"Failed to start metric flushing: {e}")
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        try:
            # Flush any remaining metrics
            await self.flush_metrics()
            
            # Clear history if it's too large
            if len(self.performance_history) > 10000:
                self.performance_history = self.performance_history[-5000:]
                logger.info("🧹 Cleaned up performance history")
            
            logger.info("✅ Performance monitor cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to cleanup performance monitor: {e}")


# Factory function for easy access
def get_performance_monitor(config: HeliosConfig) -> CloudPerformanceReporter:
    """Get performance monitor instance"""
    return CloudPerformanceReporter(config)


# Convenience functions for common operations
async def record_pipeline_performance(pipeline_data: Dict[str, Any], config: HeliosConfig) -> None:
    """Record pipeline performance metrics"""
    monitor = get_performance_monitor(config)
    await monitor.record_pipeline_metric(pipeline_data)


async def analyze_system_performance(config: HeliosConfig, time_window_hours: int = 24) -> PerformanceAnalysis:
    """Analyze system performance over a time window"""
    monitor = get_performance_monitor(config)
    return await monitor.analyze_performance(timedelta(hours=time_window_hours))


async def setup_performance_monitoring(config: HeliosConfig) -> Dict[str, Any]:
    """Set up complete performance monitoring"""
    monitor = get_performance_monitor(config)
    return await monitor.setup_monitoring_infrastructure()
