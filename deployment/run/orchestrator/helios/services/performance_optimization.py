"""
Performance Optimization Service for Helios
A/B testing, analytics, and continuous learning for marketing and design optimization
"""

import asyncio
import json
import time
import random
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from ..config import HeliosConfig
from ..utils.performance_monitor import PerformanceMonitor
from ..services.google_cloud.firestore_client import FirestoreClient
from ..services.google_cloud.redis_client import RedisCacheClient
from ..services.google_cloud.vertex_ai_client import VertexAIClient


class ExperimentStatus(Enum):
    """Experiment status enumeration"""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class VariantType(Enum):
    """Variant type enumeration"""
    CONTROL = "control"
    VARIANT = "variant"


@dataclass
class ABTestVariant:
    """A/B test variant configuration"""
    variant_id: str
    variant_name: str
    variant_type: VariantType
    content_variations: Dict[str, Any]
    traffic_allocation: float  # 0.0 to 1.0
    is_control: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    performance_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class ABTestExperiment:
    """A/B test experiment configuration"""
    experiment_id: str
    experiment_name: str
    description: str
    variants: List[ABTestVariant]
    start_date: datetime
    primary_metric: str
    end_date: Optional[datetime] = None
    status: ExperimentStatus = ExperimentStatus.DRAFT
    secondary_metrics: List[str] = field(default_factory=list)
    confidence_level: float = 0.95
    minimum_sample_size: int = 1000
    traffic_split: str = "equal"  # equal, weighted, dynamic
    target_audience: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ABTestResult:
    """A/B test result data"""
    variant_id: str
    variant_name: str
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue: float = 0.0
    engagement_rate: float = 0.0
    conversion_rate: float = 0.0
    ctr: float = 0.0
    cpc: float = 0.0
    cpa: float = 0.0
    roi: float = 0.0
    sample_size: int = 0
    confidence_interval: Dict[str, float] = field(default_factory=dict)
    statistical_significance: bool = False
    p_value: float = 0.0


@dataclass
class OptimizationInsight:
    """Optimization insight from analysis"""
    insight_id: str
    experiment_id: str
    insight_type: str
    description: str
    confidence: float
    impact_score: float
    recommendations: List[str]
    data_sources: List[str]
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class LearningModel:
    """Machine learning model for optimization"""
    model_id: str
    model_name: str
    model_type: str
    training_data_size: int
    accuracy_score: float
    last_trained: datetime
    performance_metrics: Dict[str, float]
    is_active: bool = True


class PerformanceOptimizationService:
    """Comprehensive performance optimization service with A/B testing and ML"""
    
    def __init__(self, config: HeliosConfig):
        self.config = config
        self.performance_monitor = PerformanceMonitor(
            project_id=config.google_cloud_project,
            enable_cloud_monitoring=config.enable_cloud_monitoring
        )
        # Initialize Firestore client lazily to avoid startup failures
        self._firestore_client = None
        self._firestore_project_id = config.google_cloud_project
        self.redis_client = RedisCacheClient(
            host="localhost",
            port=6379,
            enable_cache=True
        ) if config.enable_redis_caching else None
        self.vertex_ai_client = VertexAIClient(
            project_id=config.google_cloud_project,
            location=config.google_cloud_location
        ) if config.google_cloud_project else None
        
        # A/B testing configuration
        self.min_traffic_allocation = 0.1  # Minimum 10% traffic per variant
        self.max_variants_per_experiment = 5
        self.default_confidence_level = 0.95
        self.default_minimum_sample_size = 1000
        
        # Performance tracking
        self.active_experiments: Dict[str, ABTestExperiment] = {}
        self.experiment_results: Dict[str, List[ABTestResult]] = {}
        self.optimization_insights: List[OptimizationInsight] = []
        self.learning_models: Dict[str, LearningModel] = {}
        
        logger.info("✅ Performance Optimization Service initialized")
    
    @property
    def firestore_client(self):
        """Get Firestore client, initializing if needed"""
        if self._firestore_client is None and self._firestore_project_id:
            try:
                self._firestore_client = FirestoreClient(project_id=self._firestore_project_id)
                logger.info("✅ Firestore client initialized for Performance Optimization")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize Firestore client: {e}")
                return None
        return self._firestore_client
    
    async def create_experiment(self, experiment_config: Dict[str, Any]) -> ABTestExperiment:
        """Create a new A/B test experiment"""
        try:
            # Validate experiment configuration
            self._validate_experiment_config(experiment_config)
            
            # Generate experiment ID
            experiment_id = f"exp_{int(time.time())}_{random.randint(1000, 9999)}"
            
            # Create variants
            variants = []
            for i, variant_config in enumerate(experiment_config["variants"]):
                variant = ABTestVariant(
                    variant_id=f"var_{experiment_id}_{i}",
                    variant_name=variant_config["variant_name"],
                    variant_type=VariantType.CONTROL if variant_config.get("is_control", False) else VariantType.VARIANT,
                    content_variations=variant_config["content_variations"],
                    traffic_allocation=variant_config["traffic_allocation"],
                    is_control=variant_config.get("is_control", False)
                )
                variants.append(variant)
            
            # Create experiment
            experiment = ABTestExperiment(
                experiment_id=experiment_id,
                experiment_name=experiment_config["experiment_name"],
                description=experiment_config["description"],
                variants=variants,
                start_date=datetime.utcnow(),
                primary_metric=experiment_config["primary_metric"],
                secondary_metrics=experiment_config.get("secondary_metrics", []),
                confidence_level=experiment_config.get("confidence_level", self.default_confidence_level),
                minimum_sample_size=experiment_config.get("minimum_sample_size", self.default_minimum_sample_size),
                traffic_split=experiment_config.get("traffic_split", "equal"),
                target_audience=experiment_config.get("target_audience", {})
            )
            
            # Store experiment in Firestore
            await self.firestore_client.create_document(
                "ab_test_experiments",
                experiment.__dict__,
                experiment_id
            )
            
            # Store in memory
            self.active_experiments[experiment_id] = experiment
            self.experiment_results[experiment_id] = []
            
            logger.info(f"✅ Created A/B test experiment: {experiment.experiment_name} ({experiment_id})")
            return experiment
            
        except Exception as e:
            logger.error(f"❌ Failed to create experiment: {e}")
            raise
    
    async def start_experiment(self, experiment_id: str) -> bool:
        """Start an A/B test experiment"""
        try:
            if experiment_id not in self.active_experiments:
                raise ValueError(f"Experiment {experiment_id} not found")
            
            experiment = self.active_experiments[experiment_id]
            
            # Validate experiment can be started
            if experiment.status != ExperimentStatus.DRAFT:
                raise ValueError(f"Experiment {experiment_id} cannot be started from status {experiment.status}")
            
            # Update status
            experiment.status = ExperimentStatus.ACTIVE
            experiment.last_updated = datetime.utcnow()
            
            # Update in Firestore
            await self.firestore_client.update_document(
                collection="ab_test_experiments",
                document_id=experiment_id,
                updates={"status": experiment.status.value, "last_updated": experiment.last_updated.isoformat()}
            )
            
            # Initialize performance tracking
            await self._initialize_experiment_tracking(experiment)
            
            logger.info(f"✅ Started experiment: {experiment.experiment_name} ({experiment_id})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start experiment {experiment_id}: {e}")
            return False
    
    async def record_interaction(
        self,
        experiment_id: str,
        variant_id: str,
        interaction_type: str,
        value: float = 1.0,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """Record user interaction for A/B testing"""
        try:
            if experiment_id not in self.active_experiments:
                logger.warning(f"⚠️ Experiment {experiment_id} not found or not active")
                return False
            
            experiment = self.active_experiments[experiment_id]
            
            # Check if experiment is active
            if experiment.status != ExperimentStatus.ACTIVE:
                logger.warning(f"⚠️ Experiment {experiment_id} is not active (status: {experiment.status})")
                return False
            
            # Validate variant
            variant = next((v for v in experiment.variants if v.variant_id == variant_id), None)
            if not variant:
                logger.warning(f"⚠️ Variant {variant_id} not found in experiment {experiment_id}")
                return False
            
            # Record interaction in Redis for real-time tracking
            interaction_key = f"ab_test:{experiment_id}:{variant_id}:{interaction_type}"
            await self.redis_client.increment_counter(interaction_key, value)
            
            # Store detailed interaction data
            interaction_data = {
                "experiment_id": experiment_id,
                "variant_id": variant_id,
                "interaction_type": interaction_type,
                "value": value,
                "timestamp": datetime.utcnow().isoformat(),
                "metadata": metadata or {}
            }
            
            await self.firestore_client.add_document(
                collection="ab_test_interactions",
                data=interaction_data
            )
            
            # Update performance metrics
            await self._update_variant_metrics(experiment_id, variant_id, interaction_type, value)
            
            logger.debug(f"📊 Recorded {interaction_type} interaction for variant {variant_id}: {value}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to record interaction: {e}")
            return False
    
    async def get_experiment_results(self, experiment_id: str) -> Dict[str, Any]:
        """Get comprehensive results for an A/B test experiment"""
        try:
            if experiment_id not in self.active_experiments:
                raise ValueError(f"Experiment {experiment_id} not found")
            
            experiment = self.active_experiments[experiment_id]
            results = self.experiment_results.get(experiment_id, [])
            
            # Calculate statistical significance
            statistical_analysis = await self._calculate_statistical_significance(experiment, results)
            
            # Generate insights
            insights = await self._generate_optimization_insights(experiment, results)
            
            # Calculate winner
            winner = await self._determine_winner(experiment, results)
            
            return {
                "experiment": experiment.__dict__,
                "results": [result.__dict__ for result in results],
                "statistical_analysis": statistical_analysis,
                "insights": [insight.__dict__ for insight in insights],
                "winner": winner,
                "recommendations": await self._generate_recommendations(experiment, results, insights)
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get experiment results: {e}")
            return {"error": str(e)}
    
    async def optimize_experiment_traffic(self, experiment_id: str) -> Dict[str, Any]:
        """Dynamically optimize traffic allocation based on performance"""
        try:
            if experiment_id not in self.active_experiments:
                raise ValueError(f"Experiment {experiment_id} not found")
            
            experiment = self.active_experiments[experiment_id]
            results = self.experiment_results.get(experiment_id, [])
            
            if experiment.traffic_split != "dynamic":
                return {"message": "Traffic optimization only available for dynamic split experiments"}
            
            # Calculate optimal traffic allocation
            optimal_allocation = await self._calculate_optimal_traffic_allocation(experiment, results)
            
            # Update traffic allocation
            await self._update_traffic_allocation(experiment_id, optimal_allocation)
            
            return {
                "experiment_id": experiment_id,
                "previous_allocation": {v.variant_id: v.traffic_allocation for v in experiment.variants},
                "new_allocation": optimal_allocation,
                "optimization_reason": "Performance-based traffic optimization"
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to optimize experiment traffic: {e}")
            return {"error": str(e)}
    
    async def train_optimization_model(self, experiment_data: List[Dict[str, Any]]) -> LearningModel:
        """Train machine learning model for optimization insights"""
        try:
            # Prepare training data
            training_data = await self._prepare_training_data(experiment_data)
            
            # Train model using Vertex AI
            model_result = await self.vertex_ai_client.train_model(
                model_name="helios_optimization_model",
                training_data=training_data,
                model_type="classification",
                hyperparameters={
                    "learning_rate": 0.001,
                    "batch_size": 32,
                    "epochs": 100,
                    "validation_split": 0.2
                }
            )
            
            if model_result and model_result.get("status") == "success":
                model_data = model_result.get("model_data", {})
                
                model = LearningModel(
                    model_id=f"model_{int(time.time())}",
                    model_name="helios_optimization_model",
                    model_type="classification",
                    training_data_size=len(training_data),
                    accuracy_score=model_data.get("accuracy", 0.0),
                    last_trained=datetime.utcnow(),
                    performance_metrics=model_data.get("metrics", {}),
                    is_active=True
                )
                
                # Store model
                self.learning_models[model.model_id] = model
                
                # Store in Firestore
                await self.firestore_client.create_document(
                    "learning_models",
                    model.__dict__,
                    model.model_id
                )
                
                logger.info(f"✅ Trained optimization model: {model.model_id} (accuracy: {model.accuracy_score:.3f})")
                return model
            else:
                raise Exception("Model training failed")
                
        except Exception as e:
            logger.error(f"❌ Failed to train optimization model: {e}")
            raise
    
    async def get_optimization_recommendations(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get AI-powered optimization recommendations"""
        try:
            # Use trained model for predictions
            if not self.learning_models:
                # Fallback to rule-based recommendations
                return await self._generate_rule_based_recommendations(context)
            
            # Get best performing model
            best_model = max(self.learning_models.values(), key=lambda m: m.accuracy_score)
            
            if not best_model.is_active:
                return await self._generate_rule_based_recommendations(context)
            
            # Generate ML-based recommendations
            recommendations = await self._generate_ml_recommendations(best_model, context)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Failed to get optimization recommendations: {e}")
            return await self._generate_rule_based_recommendations(context)
    
    async def _validate_experiment_config(self, config: Dict[str, Any]) -> None:
        """Validate experiment configuration"""
        required_fields = ["experiment_name", "description", "variants", "primary_metric"]
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required field: {field}")
        
        if len(config["variants"]) < 2:
            raise ValueError("At least 2 variants required")
        
        if len(config["variants"]) > self.max_variants_per_experiment:
            raise ValueError(f"Maximum {self.max_variants_per_experiment} variants allowed")
        
        # Validate traffic allocation
        total_allocation = sum(v["traffic_allocation"] for v in config["variants"])
        if abs(total_allocation - 1.0) > 0.01:
            raise ValueError(f"Traffic allocation must sum to 1.0 (current: {total_allocation})")
        
        # Validate minimum traffic allocation
        for variant in config["variants"]:
            if variant["traffic_allocation"] < self.min_traffic_allocation:
                raise ValueError(f"Variant {variant['variant_name']} traffic allocation too low: {variant['traffic_allocation']}")
    
    async def _initialize_experiment_tracking(self, experiment: ABTestExperiment) -> None:
        """Initialize performance tracking for experiment"""
        try:
            # Initialize Redis counters for each variant
            for variant in experiment.variants:
                for metric in [experiment.primary_metric] + experiment.secondary_metrics:
                    counter_key = f"ab_test:{experiment.experiment_id}:{variant.variant_id}:{metric}"
                    await self.redis_client.set_counter(counter_key, 0)
            
            logger.info(f"📊 Initialized tracking for experiment {experiment.experiment_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize experiment tracking: {e}")
    
    async def _update_variant_metrics(self, experiment_id: str, variant_id: str, metric: str, value: float) -> None:
        """Update performance metrics for a variant"""
        try:
            # Get current results
            if experiment_id not in self.experiment_results:
                self.experiment_results[experiment_id] = []
            
            # Find or create result for variant
            result = next((r for r in self.experiment_results[experiment_id] if r.variant_id == variant_id), None)
            
            if not result:
                experiment = self.active_experiments[experiment_id]
                variant = next((v for v in experiment.variants if v.variant_id == variant_id), None)
                
                if not variant:
                    return
                
                result = ABTestResult(
                    variant_id=variant_id,
                    variant_name=variant.variant_name
                )
                self.experiment_results[experiment_id].append(result)
            
            # Update metrics based on interaction type
            if metric == "impression":
                result.impressions += int(value)
            elif metric == "click":
                result.clicks += int(value)
            elif metric == "conversion":
                result.conversions += int(value)
            elif metric == "revenue":
                result.revenue += value
            
            # Recalculate derived metrics
            if result.impressions > 0:
                result.ctr = result.clicks / result.impressions
                result.engagement_rate = result.clicks / result.impressions
            
            if result.clicks > 0:
                result.cpc = result.revenue / result.clicks if result.revenue > 0 else 0.0
            
            if result.conversions > 0:
                result.cpa = result.revenue / result.conversions if result.revenue > 0 else 0.0
            
            if result.revenue > 0:
                result.roi = (result.revenue - result.cpc * result.clicks) / (result.cpc * result.clicks) if result.cpc > 0 else 0.0
            
            result.sample_size = result.impressions
            
        except Exception as e:
            logger.error(f"❌ Failed to update variant metrics: {e}")
    
    async def _calculate_statistical_significance(self, experiment: ABTestExperiment, results: List[ABTestResult]) -> Dict[str, Any]:
        """Calculate statistical significance between variants"""
        try:
            if len(results) < 2:
                return {"error": "Insufficient data for statistical analysis"}
            
            # Find control variant
            control_result = next((r for r in results if r.variant_id in [v.variant_id for v in experiment.variants if v.is_control]), None)
            
            if not control_result:
                return {"error": "Control variant not found"}
            
            significance_results = {}
            
            for result in results:
                if result.variant_id == control_result.variant_id:
                    continue
                
                # Calculate p-value using chi-square test for conversion rates
                if control_result.conversions > 0 and result.conversions > 0:
                    p_value = await self._calculate_chi_square_test(
                        control_result.conversions, control_result.impressions,
                        result.conversions, result.impressions
                    )
                    
                    significance_results[result.variant_id] = {
                        "p_value": p_value,
                        "significant": p_value < (1 - experiment.confidence_level),
                        "confidence_level": experiment.confidence_level,
                        "control_variant": control_result.variant_id,
                        "variant_name": result.variant_name
                    }
            
            return significance_results
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate statistical significance: {e}")
            return {"error": str(e)}
    
    async def _calculate_chi_square_test(self, control_conversions: int, control_impressions: int,
                                       variant_conversions: int, variant_impressions: int) -> float:
        """Calculate chi-square test p-value for conversion rates"""
        try:
            # Simplified chi-square test implementation
            # In production, use scipy.stats.chi2_contingency
            
            control_rate = control_conversions / control_impressions if control_impressions > 0 else 0
            variant_rate = variant_conversions / variant_impressions if variant_impressions > 0 else 0
            
            # Calculate test statistic (simplified)
            expected_control = (control_conversions + variant_conversions) * control_impressions / (control_impressions + variant_impressions)
            expected_variant = (control_conversions + variant_conversions) * variant_impressions / (control_impressions + variant_impressions)
            
            chi_square = ((control_conversions - expected_control) ** 2 / expected_control +
                         (variant_conversions - expected_variant) ** 2 / expected_variant)
            
            # Simplified p-value calculation (use proper chi-square distribution in production)
            if chi_square > 3.84:  # Critical value for 95% confidence
                return 0.05
            else:
                return 0.5
                
        except Exception as e:
            logger.error(f"❌ Chi-square test calculation failed: {e}")
            return 1.0
    
    async def _generate_optimization_insights(self, experiment: ABTestExperiment, results: List[ABTestResult]) -> List[OptimizationInsight]:
        """Generate optimization insights from experiment results"""
        insights = []
        
        try:
            if len(results) < 2:
                return insights
            
            # Find best performing variant
            best_variant = max(results, key=lambda r: r.conversion_rate if r.impressions > 0 else 0)
            
            # Generate insights
            if best_variant.conversion_rate > 0.05:  # 5% conversion rate threshold
                insights.append(OptimizationInsight(
                    insight_id=f"insight_{int(time.time())}_1",
                    experiment_id=experiment.experiment_id,
                    insight_type="high_performance",
                    description=f"Variant '{best_variant.variant_name}' shows strong performance with {best_variant.conversion_rate:.2%} conversion rate",
                    confidence=0.9,
                    impact_score=0.8,
                    recommendations=[
                        "Consider increasing traffic allocation to this variant",
                        "Analyze design elements that contribute to success",
                        "Apply successful elements to other variants"
                    ],
                    data_sources=["conversion_rate", "statistical_significance"]
                ))
            
            # Traffic allocation insights
            for result in results:
                if result.impressions < experiment.minimum_sample_size:
                    insights.append(OptimizationInsight(
                        insight_id=f"insight_{int(time.time())}_2",
                        experiment_id=experiment.experiment_id,
                        insight_type="insufficient_data",
                        description=f"Variant '{result.variant_name}' needs more traffic for reliable results",
                        confidence=0.7,
                        impact_score=0.6,
                        recommendations=[
                            "Increase traffic allocation to this variant",
                            "Extend experiment duration",
                            "Monitor performance trends"
                        ],
                        data_sources=["sample_size", "minimum_sample_size"]
                    ))
            
            return insights
            
        except Exception as e:
            logger.error(f"❌ Failed to generate optimization insights: {e}")
            return insights
    
    async def _determine_winner(self, experiment: ABTestExperiment, results: List[ABTestResult]) -> Optional[Dict[str, Any]]:
        """Determine the winning variant"""
        try:
            if len(results) < 2:
                return None
            
            # Check if minimum sample size is reached
            for result in results:
                if result.impressions < experiment.minimum_sample_size:
                    return {"status": "insufficient_data", "reason": "Minimum sample size not reached"}
            
            # Find best performing variant
            best_variant = max(results, key=lambda r: r.conversion_rate if r.impressions > 0 else 0)
            
            # Check statistical significance
            significance_results = await self._calculate_statistical_significance(experiment, results)
            
            if best_variant.variant_id in significance_results:
                significance = significance_results[best_variant.variant_id]
                
                if significance.get("significant", False):
                    return {
                        "status": "winner_determined",
                        "variant_id": best_variant.variant_id,
                        "variant_name": best_variant.variant_name,
                        "conversion_rate": best_variant.conversion_rate,
                        "statistical_significance": True,
                        "p_value": significance.get("p_value", 1.0)
                    }
                else:
                    return {
                        "status": "no_significant_difference",
                        "reason": "Performance difference not statistically significant",
                        "best_variant": best_variant.variant_name,
                        "p_value": significance.get("p_value", 1.0)
                    }
            
            return {"status": "analysis_incomplete", "reason": "Statistical analysis failed"}
            
        except Exception as e:
            logger.error(f"❌ Failed to determine winner: {e}")
            return {"status": "error", "reason": str(e)}
    
    async def _generate_recommendations(self, experiment: ABTestExperiment, results: List[ABTestResult], insights: List[OptimizationInsight]) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        try:
            # Check experiment status
            if experiment.status == ExperimentStatus.ACTIVE:
                # Check if experiment should be stopped
                winner = await self._determine_winner(experiment, results)
                if winner and winner.get("status") == "winner_determined":
                    recommendations.append("Stop experiment and implement winning variant")
                
                # Traffic optimization
                if experiment.traffic_split == "dynamic":
                    recommendations.append("Consider dynamic traffic optimization based on performance")
                
                # Sample size recommendations
                for result in results:
                    if result.impressions < experiment.minimum_sample_size:
                        recommendations.append(f"Increase traffic to variant '{result.variant_name}' for reliable results")
            
            # Performance recommendations
            best_variant = max(results, key=lambda r: r.conversion_rate if r.impressions > 0 else 0)
            worst_variant = min(results, key=lambda r: r.conversion_rate if r.impressions > 0 else 0)
            
            if best_variant.conversion_rate > worst_variant.conversion_rate * 1.5:
                recommendations.append("Significant performance difference detected - analyze successful elements")
            
            # Insight-based recommendations
            for insight in insights:
                recommendations.extend(insight.recommendations)
            
            return list(set(recommendations))  # Remove duplicates
            
        except Exception as e:
            logger.error(f"❌ Failed to generate recommendations: {e}")
            return ["Review experiment results manually"]
    
    async def _calculate_optimal_traffic_allocation(self, experiment: ABTestExperiment, results: List[ABTestResult]) -> Dict[str, float]:
        """Calculate optimal traffic allocation based on performance"""
        try:
            if len(results) < 2:
                return {v.variant_id: v.traffic_allocation for v in experiment.variants}
            
            # Calculate performance scores
            performance_scores = {}
            total_score = 0
            
            for result in results:
                # Composite performance score
                score = (result.conversion_rate * 0.4 + 
                        result.engagement_rate * 0.3 + 
                        result.ctr * 0.3)
                
                performance_scores[result.variant_id] = max(score, 0.01)  # Minimum score
                total_score += performance_scores[result.variant_id]
            
            # Calculate optimal allocation
            optimal_allocation = {}
            for variant_id, score in performance_scores.items():
                allocation = score / total_score
                # Ensure minimum allocation
                allocation = max(allocation, self.min_traffic_allocation)
                optimal_allocation[variant_id] = allocation
            
            # Normalize to sum to 1.0
            total_allocation = sum(optimal_allocation.values())
            for variant_id in optimal_allocation:
                optimal_allocation[variant_id] /= total_allocation
            
            return optimal_allocation
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate optimal traffic allocation: {e}")
            return {v.variant_id: v.traffic_allocation for v in experiment.variants}
    
    async def _update_traffic_allocation(self, experiment_id: str, new_allocation: Dict[str, float]) -> None:
        """Update traffic allocation for experiment variants"""
        try:
            experiment = self.active_experiments[experiment_id]
            
            for variant in experiment.variants:
                if variant.variant_id in new_allocation:
                    variant.traffic_allocation = new_allocation[variant.variant_id]
            
            # Update in Firestore
            await self.firestore_client.update_document(
                collection="ab_test_experiments",
                document_id=experiment_id,
                updates={"variants": [v.__dict__ for v in experiment.variants]}
            )
            
            logger.info(f"✅ Updated traffic allocation for experiment {experiment_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to update traffic allocation: {e}")
    
    async def _prepare_training_data(self, experiment_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prepare training data for machine learning model"""
        try:
            training_data = []
            
            for experiment in experiment_data:
                # Extract features
                features = {
                    "variant_count": len(experiment.get("variants", [])),
                    "confidence_level": experiment.get("confidence_level", 0.95),
                    "minimum_sample_size": experiment.get("minimum_sample_size", 1000),
                    "traffic_split_type": 1 if experiment.get("traffic_split") == "dynamic" else 0,
                    "primary_metric_type": self._encode_metric_type(experiment.get("primary_metric", "conversion"))
                }
                
                # Extract target (success indicator)
                results = experiment.get("results", [])
                if results:
                    best_result = max(results, key=lambda r: r.get("conversion_rate", 0))
                    target = 1 if best_result.get("conversion_rate", 0) > 0.05 else 0
                else:
                    target = 0
                
                training_data.append({
                    "features": features,
                    "target": target
                })
            
            return training_data
            
        except Exception as e:
            logger.error(f"❌ Failed to prepare training data: {e}")
            return []
    
    def _encode_metric_type(self, metric: str) -> int:
        """Encode metric type for ML model"""
        metric_encodings = {
            "conversion": 0,
            "revenue": 1,
            "engagement": 2,
            "ctr": 3,
            "roi": 4
        }
        return metric_encodings.get(metric, 0)
    
    async def _generate_ml_recommendations(self, model: LearningModel, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate ML-based optimization recommendations"""
        try:
            # Prepare context features
            features = {
                "variant_count": context.get("variant_count", 2),
                "confidence_level": context.get("confidence_level", 0.95),
                "minimum_sample_size": context.get("minimum_sample_size", 1000),
                "traffic_split_type": 1 if context.get("traffic_split") == "dynamic" else 0,
                "primary_metric_type": self._encode_metric_type(context.get("primary_metric", "conversion"))
            }
            
            # Get prediction from model
            prediction = await self.vertex_ai_client.predict(
                model_name=model.model_name,
                features=features
            )
            
            if prediction and prediction.get("status") == "success":
                prediction_data = prediction.get("prediction", {})
                confidence = prediction_data.get("confidence", 0.5)
                
                recommendations = []
                
                if confidence > 0.8:
                    recommendations.append({
                        "type": "ml_optimization",
                        "description": "High-confidence ML recommendation available",
                        "confidence": confidence,
                        "action": "Apply ML-based traffic optimization",
                        "impact_score": 0.9
                    })
                
                return recommendations
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Failed to generate ML recommendations: {e}")
            return []
    
    async def _generate_rule_based_recommendations(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate rule-based optimization recommendations"""
        recommendations = []
        
        try:
            # Traffic allocation recommendations
            if context.get("traffic_split") == "equal":
                recommendations.append({
                    "type": "traffic_optimization",
                    "description": "Consider dynamic traffic allocation for better performance",
                    "confidence": 0.7,
                    "action": "Switch to dynamic traffic split",
                    "impact_score": 0.6
                })
            
            # Sample size recommendations
            if context.get("minimum_sample_size", 1000) > 500:
                recommendations.append({
                    "type": "sample_size",
                    "description": "High minimum sample size may slow down experiment",
                    "confidence": 0.6,
                    "action": "Consider reducing minimum sample size",
                    "impact_score": 0.5
                })
            
            # Confidence level recommendations
            if context.get("confidence_level", 0.95) > 0.99:
                recommendations.append({
                    "type": "confidence_level",
                    "description": "Very high confidence level may be overly conservative",
                    "confidence": 0.7,
                    "action": "Consider 95% confidence level for faster results",
                    "impact_score": 0.6
                })
            
            return recommendations
            
        except Exception as e:
            logger.error(f"❌ Failed to generate rule-based recommendations: {e}")
            return []
    
    async def get_optimization_summary(self) -> Dict[str, Any]:
        """Get summary of optimization activities"""
        total_experiments = len(self.active_experiments)
        active_experiments = len([e for e in self.active_experiments.values() if e.status == ExperimentStatus.ACTIVE])
        total_insights = len(self.optimization_insights)
        total_models = len(self.learning_models)
        
        return {
            "total_experiments": total_experiments,
            "active_experiments": active_experiments,
            "total_insights": total_insights,
            "total_models": total_models,
            "active_learning_models": len([m for m in self.learning_models.values() if m.is_active]),
            "last_insight": self.optimization_insights[-1] if self.optimization_insights else None,
            "best_model": max(self.learning_models.values(), key=lambda m: m.accuracy_score) if self.learning_models else None
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.performance_monitor.close()
            await self.firestore_client.close()
            await self.redis_client.close()
            await self.vertex_ai_client.close()
            logger.info("✅ Performance Optimization Service cleaned up")
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")


async def create_performance_optimization_service(config: HeliosConfig) -> PerformanceOptimizationService:
    """Factory function to create performance optimization service"""
    return PerformanceOptimizationService(config)
