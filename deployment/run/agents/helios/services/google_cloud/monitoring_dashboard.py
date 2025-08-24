from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
from google.cloud import monitoring_v3
from google.cloud.monitoring_v3 import types
from google.protobuf import timestamp_pb2
from loguru import logger

from ...config import HeliosConfig


class CloudMonitoringDashboard:
    """Google Cloud Monitoring Dashboard service for Helios performance monitoring"""
    
    def __init__(self, config: HeliosConfig):
        self.config = config
        self.project_id = config.google_cloud_project
        self.client = None
        
        if config.enable_cloud_monitoring and self.project_id:
            try:
                self.client = monitoring_v3.DashboardServiceClient()
                logger.info(f"✅ Cloud Monitoring Dashboard service initialized for project: {self.project_id}")
            except Exception as e:
                logger.error(f"❌ Failed to initialize Cloud Monitoring Dashboard service: {e}")
                self.client = None
    
    async def create_helios_dashboard(self) -> Dict[str, Any]:
        """Create the main Helios performance monitoring dashboard"""
        if not self.client:
            return {"status": "error", "error": "Cloud Monitoring not enabled or configured"}
        
        try:
            dashboard_config = self._get_helios_dashboard_config()
            
            # Create dashboard
            dashboard = types.Dashboard(
                display_name="Helios Autonomous Store - Performance Dashboard",
                grid_layout=types.GridLayout(
                    columns=2,
                    widgets=self._create_dashboard_widgets()
                )
            )
            
            # Create the dashboard
            parent = f"projects/{self.project_id}"
            created_dashboard = self.client.create_dashboard(
                request={
                    "parent": parent,
                    "dashboard": dashboard
                }
            )
            
            logger.info(f"✅ Helios dashboard created: {created_dashboard.name}")
            
            return {
                "status": "success",
                "dashboard_name": created_dashboard.name,
                "dashboard_url": f"https://console.cloud.google.com/monitoring/dashboards/custom/{created_dashboard.name.split('/')[-1]}?project={self.project_id}",
                "config": dashboard_config
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create Helios dashboard: {e}")
            return {"status": "error", "error": str(e)}
    
    async def create_alerting_policies(self) -> Dict[str, Any]:
        """Create alerting policies for critical Helios metrics"""
        if not self.client:
            return {"status": "error", "error": "Cloud Monitoring not enabled or configured"}
        
        try:
            alerting_client = monitoring_v3.AlertPolicyServiceClient()
            
            policies = []
            
            # 1. Pipeline Execution Time Alert
            execution_time_policy = self._create_execution_time_alert()
            policies.append(execution_time_policy)
            
            # 2. Success Rate Alert
            success_rate_policy = self._create_success_rate_alert()
            policies.append(success_rate_policy)
            
            # 3. Error Rate Alert
            error_rate_policy = self._create_error_rate_alert()
            policies.append(error_rate_policy)
            
            # 4. Resource Utilization Alert
            resource_policy = self._create_resource_utilization_alert()
            policies.append(resource_policy)
            
            # Create all policies
            created_policies = []
            parent = f"projects/{self.project_id}"
            
            for policy in policies:
                try:
                    created_policy = alerting_client.create_alert_policy(
                        request={"parent": parent, "alert_policy": policy}
                    )
                    created_policies.append({
                        "name": created_policy.name,
                        "display_name": created_policy.display_name,
                        "type": policy.display_name
                    })
                    logger.info(f"✅ Alert policy created: {created_policy.display_name}")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to create alert policy {policy.display_name}: {e}")
            
            return {
                "status": "success",
                "policies_created": len(created_policies),
                "policies": created_policies
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create alerting policies: {e}")
            return {"status": "error", "error": str(e)}
    
    async def setup_custom_metrics(self) -> Dict[str, Any]:
        """Set up custom metrics for Helios-specific monitoring"""
        if not self.client:
            return {"status": "error", "error": "Cloud Monitoring not enabled or configured"}
        
        try:
            metric_client = monitoring_v3.MetricServiceClient()
            
            custom_metrics = [
                {
                    "type": "custom.googleapis.com/helios/pipeline_execution_time",
                    "description": "Helios pipeline execution time in seconds",
                    "labels": ["trend_name", "stage", "status"]
                },
                {
                    "type": "custom.googleapis.com/helios/trend_opportunity_score",
                    "description": "Trend opportunity score (0-10)",
                    "labels": ["trend_name", "category", "source"]
                },
                {
                    "type": "custom.googleapis.com/helios/audience_confidence",
                    "description": "Audience analysis confidence score (0-1)",
                    "labels": ["trend_name", "demographic_cluster", "persona_type"]
                },
                {
                    "type": "custom.googleapis.com/helios/design_generation_success",
                    "description": "Design generation success rate",
                    "labels": ["trend_name", "product_type", "design_style"]
                },
                {
                    "type": "custom.googleapis.com/helios/publication_success",
                    "description": "Product publication success rate",
                    "labels": ["trend_name", "product_type", "sales_channel"]
                }
            ]
            
            # Create metric descriptors
            created_metrics = []
            parent = f"projects/{self.project_id}"
            
            for metric in custom_metrics:
                try:
                    descriptor = types.MetricDescriptor(
                        type=metric["type"],
                        description=metric["description"],
                        metric_kind=types.MetricDescriptor.MetricKind.GAUGE,
                        value_type=types.MetricDescriptor.ValueType.DOUBLE,
                        labels=[
                            types.LabelDescriptor(key=label, value_type=types.LabelDescriptor.ValueType.STRING)
                            for label in metric["labels"]
                        ]
                    )
                    
                    created_descriptor = metric_client.create_metric_descriptor(
                        request={"name": parent, "metric_descriptor": descriptor}
                    )
                    
                    created_metrics.append({
                        "type": metric["type"],
                        "name": created_descriptor.name,
                        "description": metric["description"]
                    })
                    
                    logger.info(f"✅ Custom metric created: {metric['type']}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Failed to create metric {metric['type']}: {e}")
            
            return {
                "status": "success",
                "metrics_created": len(created_metrics),
                "metrics": created_metrics
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to setup custom metrics: {e}")
            return {"status": "error", "error": str(e)}
    
    async def create_performance_dashboard(self) -> Dict[str, Any]:
        """Create a dedicated performance monitoring dashboard"""
        if not self.client:
            return {"status": "error", "error": "Cloud Monitoring not enabled or configured"}
        
        try:
            dashboard = types.Dashboard(
                display_name="Helios - Performance Intelligence Dashboard",
                grid_layout=types.GridLayout(
                    columns=3,
                    widgets=self._create_performance_widgets()
                )
            )
            
            parent = f"projects/{self.project_id}"
            created_dashboard = self.client.create_dashboard(
                request={
                    "parent": parent,
                    "dashboard": dashboard
                }
            )
            
            logger.info(f"✅ Performance dashboard created: {created_dashboard.name}")
            
            return {
                "status": "success",
                "dashboard_name": created_dashboard.name,
                "dashboard_url": f"https://console.cloud.google.com/monitoring/dashboards/custom/{created_dashboard.name.split('/')[-1]}?project={self.project_id}",
                "type": "performance_intelligence"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to create performance dashboard: {e}")
            return {"status": "error", "error": str(e)}
    
    def _get_helios_dashboard_config(self) -> Dict[str, Any]:
        """Get the configuration for the Helios dashboard"""
        return {
            "dashboard_name": "Helios Autonomous Store - Performance Dashboard",
            "description": "Comprehensive monitoring dashboard for Helios AI-powered e-commerce pipeline",
            "refresh_interval": "60s",
            "sections": [
                "Pipeline Performance",
                "Trend Analysis",
                "Creative Generation",
                "Publication Success",
                "Resource Utilization"
            ]
        }
    
    def _create_dashboard_widgets(self) -> List[types.Widget]:
        """Create widgets for the main Helios dashboard"""
        widgets = []
        
        # 1. Pipeline Execution Time Chart
        execution_time_widget = types.Widget(
            title="Pipeline Execution Time",
            xy_chart=types.XyChart(
                data_sets=[
                    types.XyChart.DataSet(
                        time_series_query=types.TimeSeriesQuery(
                            time_series_filter=types.TimeSeriesFilter(
                                filter=f'metric.type = "custom.googleapis.com/helios/pipeline_execution_time"'
                            )
                        ),
                        plot_type=types.XyChart.DataSet.PlotType.LINE
                    )
                ],
                timeshift_duration="3600s"
            )
        )
        widgets.append(execution_time_widget)
        
        # 2. Success Rate Gauge
        success_rate_widget = types.Widget(
            title="Pipeline Success Rate",
            scorecard=types.Scorecard(
                time_series_query=types.TimeSeriesQuery(
                    time_series_filter=types.TimeSeriesFilter(
                        filter=f'metric.type = "custom.googleapis.com/helios/pipeline_success_rate"'
                    )
                ),
                gauge_view=types.Scorecard.GaugeView()
            )
        )
        widgets.append(success_rate_widget)
        
        # 3. Trend Opportunity Scores
        trend_scores_widget = types.Widget(
            title="Trend Opportunity Scores",
            xy_chart=types.XyChart(
                data_sets=[
                    types.XyChart.DataSet(
                        time_series_query=types.TimeSeriesQuery(
                            time_series_filter=types.TimeSeriesFilter(
                                filter=f'metric.type = "custom.googleapis.com/helios/trend_opportunity_score"'
                            )
                        ),
                        plot_type=types.XyChart.DataSet.PlotType.BAR
                    )
                ]
            )
        )
        widgets.append(trend_scores_widget)
        
        # 4. Audience Confidence Chart
        audience_widget = types.Widget(
            title="Audience Analysis Confidence",
            xy_chart=types.XyChart(
                data_sets=[
                    types.XyChart.DataSet(
                        time_series_query=types.TimeSeriesQuery(
                            time_series_filter=types.TimeSeriesFilter(
                                filter=f'metric.type = "custom.googleapis.com/helios/audience_confidence"'
                            )
                        ),
                        plot_type=types.XyChart.DataSet.PlotType.LINE
                    )
                ]
            )
        )
        widgets.append(audience_widget)
        
        return widgets
    
    def _create_performance_widgets(self) -> List[types.Widget]:
        """Create widgets for the performance intelligence dashboard"""
        widgets = []
        
        # 1. Performance Metrics Summary
        summary_widget = types.Widget(
            title="Performance Metrics Summary",
            text=types.Text(
                content="<h3>Helios Performance Intelligence</h3><p>Real-time monitoring of AI pipeline performance</p>"
            )
        )
        widgets.append(summary_widget)
        
        # 2. Execution Time Distribution
        time_dist_widget = types.Widget(
            title="Execution Time Distribution",
            xy_chart=types.XyChart(
                data_sets=[
                    types.XyChart.DataSet(
                        time_series_query=types.TimeSeriesQuery(
                            time_series_filter=types.TimeSeriesFilter(
                                filter=f'metric.type = "custom.googleapis.com/helios/pipeline_execution_time"'
                            )
                        ),
                        plot_type=types.XyChart.DataSet.PlotType.HISTOGRAM
                    )
                ]
            )
        )
        widgets.append(time_dist_widget)
        
        # 3. Success Rate Trends
        success_trend_widget = types.Widget(
            title="Success Rate Trends",
            xy_chart=types.XyChart(
                data_sets=[
                    types.XyChart.DataSet(
                        time_series_query=types.TimeSeriesQuery(
                            time_series_filter=types.TimeSeriesFilter(
                                filter=f'metric.type = "custom.googleapis.com/helios/pipeline_success_rate"'
                            )
                        ),
                        plot_type=types.XyChart.DataSet.PlotType.LINE
                    )
                ],
                timeshift_duration="86400s"  # 24 hours
            )
        )
        widgets.append(success_trend_widget)
        
        return widgets
    
    def _create_execution_time_alert(self) -> types.AlertPolicy:
        """Create alert policy for pipeline execution time"""
        return types.AlertPolicy(
            display_name="Helios Pipeline Execution Time Alert",
            conditions=[
                types.AlertPolicy.Condition(
                    display_name="Pipeline execution time exceeds threshold",
                    condition_threshold=types.AlertPolicy.Condition.MetricThreshold(
                        filter=f'metric.type = "custom.googleapis.com/helios/pipeline_execution_time"',
                        comparison=types.ComparisonType.COMPARISON_GREATER_THAN,
                        threshold_value=300.0,  # 5 minutes
                        duration="60s"
                    )
                )
            ],
            notification_channels=[],  # Add notification channels as needed
            alert_strategy=types.AlertPolicy.AlertStrategy(
                auto_close="3600s"  # Auto-close after 1 hour
            )
        )
    
    def _create_success_rate_alert(self) -> types.AlertPolicy:
        """Create alert policy for pipeline success rate"""
        return types.AlertPolicy(
            display_name="Helios Pipeline Success Rate Alert",
            conditions=[
                types.AlertPolicy.Condition(
                    display_name="Pipeline success rate below threshold",
                    condition_threshold=types.AlertPolicy.Condition.MetricThreshold(
                        filter=f'metric.type = "custom.googleapis.com/helios/pipeline_success_rate"',
                        comparison=types.ComparisonType.COMPARISON_LESS_THAN,
                        threshold_value=0.85,  # 85%
                        duration="300s"
                    )
                )
            ],
            notification_channels=[],
            alert_strategy=types.AlertPolicy.AlertStrategy(
                auto_close="3600s"
            )
        )
    
    def _create_error_rate_alert(self) -> types.AlertPolicy:
        """Create alert policy for error rate"""
        return types.AlertPolicy(
            display_name="Helios Error Rate Alert",
            conditions=[
                types.AlertPolicy.Condition(
                    display_name="Error rate above threshold",
                    condition_threshold=types.AlertPolicy.Condition.MetricThreshold(
                        filter=f'metric.type = "custom.googleapis.com/helios/error_rate"',
                        comparison=types.ComparisonType.COMPARISON_GREATER_THAN,
                        threshold_value=0.15,  # 15%
                        duration="300s"
                    )
                )
            ],
            notification_channels=[],
            alert_strategy=types.AlertPolicy.AlertStrategy(
                auto_close="3600s"
            )
        )
    
    def _create_resource_utilization_alert(self) -> types.AlertPolicy:
        """Create alert policy for resource utilization"""
        return types.AlertPolicy(
            display_name="Helios Resource Utilization Alert",
            conditions=[
                types.AlertPolicy.Condition(
                    display_name="CPU utilization above threshold",
                    condition_threshold=types.AlertPolicy.Condition.MetricThreshold(
                        filter='metric.type = "compute.googleapis.com/instance/cpu/utilization"',
                        comparison=types.ComparisonType.COMPARISON_GREATER_THAN,
                        threshold_value=0.8,  # 80%
                        duration="300s"
                    )
                )
            ],
            notification_channels=[],
            alert_strategy=types.AlertPolicy.AlertStrategy(
                auto_close="1800s"  # Auto-close after 30 minutes
            )
        )
    
    async def setup_complete_monitoring(self) -> Dict[str, Any]:
        """Set up complete monitoring infrastructure for Helios"""
        if not self.client:
            return {"status": "error", "error": "Cloud Monitoring not enabled or configured"}
        
        try:
            logger.info("🚀 Setting up complete Helios monitoring infrastructure...")
            
            results = {}
            
            # 1. Create main dashboard
            logger.info("📊 Creating main Helios dashboard...")
            dashboard_result = await self.create_helios_dashboard()
            results["main_dashboard"] = dashboard_result
            
            # 2. Create performance dashboard
            logger.info("📈 Creating performance intelligence dashboard...")
            perf_result = await self.create_performance_dashboard()
            results["performance_dashboard"] = perf_result
            
            # 3. Set up custom metrics
            logger.info("🔧 Setting up custom metrics...")
            metrics_result = await self.setup_custom_metrics()
            results["custom_metrics"] = metrics_result
            
            # 4. Create alerting policies
            logger.info("🚨 Creating alerting policies...")
            alerts_result = await self.create_alerting_policies()
            results["alerting_policies"] = alerts_result
            
            # Summary
            successful_setups = sum(1 for r in results.values() if r.get("status") == "success")
            total_setups = len(results)
            
            logger.info(f"✅ Monitoring setup completed: {successful_setups}/{total_setups} successful")
            
            return {
                "status": "success",
                "setup_summary": {
                    "total_components": total_setups,
                    "successful_setups": successful_setups,
                    "failed_setups": total_setups - successful_setups
                },
                "results": results
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to setup complete monitoring: {e}")
            return {"status": "error", "error": str(e)}
