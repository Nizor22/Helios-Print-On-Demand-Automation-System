"""
Helios Orchestrator Service - Main controller for the autonomous store
Coordinates all agents and services with priority-driven execution
"""

import asyncio
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger

from ..agents.ceo import HeliosCEO
from ..agents.trend_analysis_ai import TrendAnalysisAI, TrendAnalysisMode
from ..config import HeliosConfig
from ..utils.performance_monitor import PerformanceMonitor
from .automated_trend_discovery import AutomatedTrendDiscovery, create_automated_trend_discovery
from .product_generation_pipeline import ProductGenerationPipeline, create_product_generation_pipeline
from .performance_optimization import PerformanceOptimizationService, create_performance_optimization_service
from .google_cloud.cloud_scheduler_client import CloudSchedulerClient
from .google_cloud.firestore_client import FirestoreClient
from ..utils.redis_cache_client import RedisCacheClient


@dataclass
class OrchestrationSession:
    """Orchestration session data"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    trends_discovered: int = 0
    products_generated: int = 0
    experiments_created: int = 0
    execution_time: float = 0.0
    status: str = "running"
    errors: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, Any] = field(default_factory=dict)


class HeliosOrchestrator:
    """Main orchestrator for Helios Autonomous Store"""
    
    def __init__(self, config: HeliosConfig):
        self.config = config
        self.performance_monitor = PerformanceMonitor(config)
        
        # Initialize AI agents
        self.trend_ai: Optional[TrendAnalysisAI] = None
        self.ceo_agent: Optional[HeliosCEO] = None
        
        # Initialize core services
        self.trend_discovery: Optional[AutomatedTrendDiscovery] = None
        self.product_pipeline: Optional[ProductGenerationPipeline] = None
        self.performance_optimization: Optional[PerformanceOptimizationService] = None
        
        # Cloud services
        self.scheduler_client: Optional[CloudSchedulerClient] = None
        self.firestore_client: Optional[FirestoreClient] = None
        self.redis_client: Optional[RedisCacheClient] = None
        
        # Session tracking
        self.active_session: Optional[OrchestrationSession] = None
        self.session_history: List[OrchestrationSession] = []
        
        # Configuration
        self.trend_discovery_interval = timedelta(hours=6)
        self.product_generation_interval = timedelta(hours=4)
        self.performance_analysis_interval = timedelta(hours=24)
        
        # AI agent configuration
        self.use_ai_orchestration = True  # Enable AI-powered orchestration
        
        logger.info("🚀 Helios Orchestrator initialized with AI capabilities")
    
    async def initialize_services(self) -> bool:
        """Initialize all core services and cloud clients"""
        try:
            logger.info("🔧 Initializing Helios services...")
            
            # Initialize AI agents first
            if self.use_ai_orchestration:
                logger.info("🤖 Initializing AI agents...")
                self.trend_ai = TrendAnalysisAI(self.config)
                self.ceo_agent = HeliosCEO(
                    min_opportunity=self.config.min_opportunity_score,
                    min_confidence=self.config.min_audience_confidence
                )
                logger.info("✅ AI agents initialized")
            
            # Initialize core services
            self.trend_discovery = await create_automated_trend_discovery(self.config)
            self.product_pipeline = await create_product_generation_pipeline(self.config)
            self.performance_optimization = await create_performance_optimization_service(self.config)
            
            # Ensure trend discovery uses AI agent
            if self.use_ai_orchestration and self.trend_discovery:
                self.trend_discovery.use_ai_agent = True
                logger.info("✅ Trend discovery configured to use AI agent")
            
            # Initialize cloud services (optional for development)
            try:
                if self.config.google_cloud_project:
                    self.scheduler_client = CloudSchedulerClient(
                        project_id=self.config.google_cloud_project,
                        location=self.config.google_cloud_region
                    )
                    logger.info("✅ Cloud Scheduler client initialized")
                else:
                    logger.warning("⚠️  Google Cloud Project not configured - Cloud Scheduler disabled")
                    self.scheduler_client = None
            except Exception as e:
                logger.warning(f"⚠️  Cloud Scheduler initialization failed: {e} - continuing without it")
                self.scheduler_client = None
            
            try:
                if self.config.google_cloud_project:
                    self.firestore_client = FirestoreClient(
                        project_id=self.config.google_cloud_project
                    )
                    logger.info("✅ Firestore client initialized")
                else:
                    logger.warning("⚠️  Google Cloud Project not configured - Firestore disabled")
                    self.firestore_client = None
            except Exception as e:
                logger.warning(f"⚠️  Firestore initialization failed: {e} - continuing without it")
                self.firestore_client = None
            
            try:
                if self.config.enable_redis_caching and self.config.google_cloud_project:
                    # Use local Redis instead of Google Cloud Redis for development
                    self.redis_client = RedisCacheClient(
                        host="localhost",
                        port=6379,
                        enable_cache=True
                    )
                    logger.info("✅ Redis client initialized (local)")
                else:
                    logger.info("ℹ️  Redis caching disabled")
                    self.redis_client = None
            except Exception as e:
                logger.warning(f"⚠️  Redis initialization failed: {e} - continuing without it")
                self.redis_client = None
            
            logger.info("✅ All services initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize services: {e}")
            return False
    
    async def setup_automated_workflows(self) -> Dict[str, Any]:
        """Setup automated workflows using Google Cloud Scheduler"""
        try:
            logger.info("📅 Setting up automated workflows...")
            
            if not self.scheduler_client:
                logger.warning("⚠️  Scheduler client not available - workflows will run manually")
                return {"status": "warning", "message": "Scheduler not available - manual operation mode"}
            
            # Setup all Helios workflows
            result = await self.scheduler_client.setup_helios_workflows()
            
            logger.info("✅ Automated workflows configured successfully")
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to setup automated workflows: {e}")
            return {"status": "error", "message": str(e)}
    
    async def start_orchestration_session(self) -> OrchestrationSession:
        """Start a new orchestration session"""
        session_id = f"orchestration_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        
        self.active_session = OrchestrationSession(
            session_id=session_id,
            start_time=datetime.utcnow()
        )
        
        logger.info(f"🎭 Starting orchestration session: {session_id}")
        return self.active_session
    
    async def run_trend_discovery_cycle(self) -> Dict[str, Any]:
        """Run the automated trend discovery cycle"""
        try:
            if not self.trend_discovery:
                raise RuntimeError("Trend discovery service not initialized")
            
            logger.info("🔍 Running automated trend discovery cycle...")
            
            # Get seed keywords using AI if enabled
            if self.use_ai_orchestration and self.trend_ai:
                # Use AI to generate smart seed keywords based on market analysis
                ai_keywords = await self._get_ai_generated_keywords()
                seed_keywords = ai_keywords
            else:
                # Use default seed keywords
                seed_keywords = await self._get_seed_keywords()
            
            # Run discovery with seed keywords
            discovery_result = await self.trend_discovery.run_discovery_pipeline(seed_keywords)
            
            if discovery_result.get("status") == "success":
                trends_data = discovery_result.get("trends_discovered", [])
                validated_opportunities = discovery_result.get("opportunities_validated", [])
                session = discovery_result.get("session")
                
                # If AI orchestration is enabled, get AI insights
                if self.use_ai_orchestration and self.trend_ai and validated_opportunities:
                    ai_insights = await self._get_ai_insights_for_opportunities(validated_opportunities)
                    discovery_result["ai_insights"] = ai_insights
            else:
                logger.error(f"❌ Discovery pipeline failed: {discovery_result.get('error')}")
                return {"status": "error", "message": discovery_result.get("error")}
            
            # Store results
            await self._store_discovery_results(validated_opportunities)
            
            # Update session
            if self.active_session:
                self.active_session.trends_discovered = len(validated_opportunities)
            
            logger.info(f"✅ Trend discovery completed: {len(validated_opportunities)} opportunities found")
            return {
                "status": "success",
                "opportunities_found": len(validated_opportunities),
                "opportunities": validated_opportunities
            }
            
        except Exception as e:
            logger.error(f"❌ Trend discovery cycle failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def run_product_generation_cycle(self, trend_opportunities: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Run the product generation pipeline for approved trends"""
        try:
            if not self.product_pipeline:
                raise RuntimeError("Product pipeline service not initialized")
            
            logger.info(f"🎨 Running product generation cycle for {len(trend_opportunities)} trends...")
            
            generated_products = []
            
            for opportunity in trend_opportunities:
                try:
                    # Generate product package
                    result = await self.product_pipeline.run_generation_pipeline(opportunity)
                    
                    if result.get("status") == "success":
                        generated_products.append(result)
                        
                        # Update session
                        if self.active_session:
                            self.active_session.products_generated += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to generate product for trend {opportunity.get('trend_name')}: {e}")
                    continue
            
            # Store results
            await self._store_product_results(generated_products)
            
            logger.info(f"✅ Product generation completed: {len(generated_products)} products created")
            return {
                "status": "success",
                "products_generated": len(generated_products),
                "products": generated_products
            }
            
        except Exception as e:
            logger.error(f"❌ Product generation cycle failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def run_performance_optimization_cycle(self) -> Dict[str, Any]:
        """Run the performance optimization and A/B testing cycle"""
        try:
            if not self.performance_optimization:
                raise RuntimeError("Performance optimization service not initialized")
            
            logger.info("📊 Running performance optimization cycle...")
            
            # Get active experiments
            active_experiments = await self._get_active_experiments()
            
            # Analyze experiment results
            optimization_results = []
            for experiment in active_experiments:
                try:
                    results = await self.performance_optimization.get_experiment_results(experiment["experiment_id"])
                    
                    if results.get("status") == "success":
                        # Generate optimization insights
                        insights = await self.performance_optimization._generate_optimization_insights(
                            experiment, results.get("results", [])
                        )
                        
                        # Apply optimizations
                        optimization = await self.performance_optimization.optimize_experiment_traffic(
                            experiment["experiment_id"]
                        )
                        
                        optimization_results.append({
                            "experiment_id": experiment["experiment_id"],
                            "results": results,
                            "insights": insights,
                            "optimization": optimization
                        })
                        
                        # Update session
                        if self.active_session:
                            self.active_session.experiments_created += 1
                    
                except Exception as e:
                    logger.error(f"❌ Failed to optimize experiment {experiment.get('experiment_id')}: {e}")
                    continue
            
            # Store results
            await self._store_optimization_results(optimization_results)
            
            logger.info(f"✅ Performance optimization completed: {len(optimization_results)} experiments optimized")
            return {
                "status": "success",
                "experiments_optimized": len(optimization_results),
                "results": optimization_results
            }
            
        except Exception as e:
            logger.error(f"❌ Performance optimization cycle failed: {e}")
            return {"status": "error", "message": str(e)}
    
    async def run_complete_cycle(self) -> Dict[str, Any]:
        """Run the complete orchestration cycle"""
        try:
            logger.info("🔄 Starting complete Helios orchestration cycle...")
            
            # Start orchestration session
            session = await self.start_orchestration_session()
            
            cycle_start = time.time()
            
            # 1. Trend Discovery
            discovery_result = await self.run_trend_discovery_cycle()
            
            if discovery_result.get("status") != "success":
                logger.warning("⚠️ Trend discovery failed, continuing with existing opportunities...")
                trend_opportunities = await self._get_existing_opportunities()
            else:
                trend_opportunities = discovery_result.get("opportunities", [])
            
            # 2. Product Generation
            if trend_opportunities:
                generation_result = await self.run_product_generation_cycle(trend_opportunities)
            else:
                logger.info("ℹ️ No trend opportunities available for product generation")
                generation_result = {"status": "skipped", "reason": "No opportunities"}
            
            # 3. Performance Optimization
            optimization_result = await self.run_performance_optimization_cycle()
            
            # Complete session
            cycle_time = time.time() - cycle_start
            session.end_time = datetime.utcnow()
            session.execution_time = cycle_time
            session.status = "completed"
            
            # Store session
            self.session_history.append(session)
            self.active_session = None
            
            # Generate summary
            summary = await self._generate_cycle_summary(
                discovery_result, generation_result, optimization_result, session
            )
            
            logger.info(f"✅ Complete cycle finished in {cycle_time:.1f}s")
            return summary
            
        except Exception as e:
            logger.error(f"❌ Complete cycle failed: {e}")
            if self.active_session:
                self.active_session.status = "failed"
                self.active_session.errors.append(str(e))
                self.active_session.end_time = datetime.utcnow()
            
            return {"status": "error", "message": str(e)}
    
    async def start_continuous_operation(self) -> None:
        """Start continuous operation with scheduled cycles"""
        try:
            logger.info("🔄 Starting continuous Helios operation...")
            
            # Setup automated workflows
            await self.setup_automated_workflows()
            
            # Run initial cycle
            await self.run_complete_cycle()
            
            # Start continuous loop
            while True:
                try:
                    logger.info("⏰ Waiting for next cycle...")
                    await asyncio.sleep(self.trend_discovery_interval.total_seconds())
                    
                    # Run next cycle
                    await self.run_complete_cycle()
                    
                except asyncio.CancelledError:
                    logger.info("🛑 Continuous operation cancelled")
                    break
                except Exception as e:
                    logger.error(f"❌ Cycle failed, retrying in 1 hour: {e}")
                    await asyncio.sleep(3600)  # Wait 1 hour before retry
            
        except Exception as e:
            logger.error(f"❌ Continuous operation failed: {e}")
    
    async def _get_seed_keywords(self) -> List[str]:
        """Get seed keywords for trend discovery"""
        # This could be enhanced with historical data, seasonal trends, etc.
        return [
            "sustainable fashion", "eco-friendly products", "minimalist design",
            "tech accessories", "home decor trends", "wellness products",
            "pet accessories", "garden tools", "kitchen gadgets", "fitness gear"
        ]
    
    async def _get_ai_generated_keywords(self) -> List[str]:
        """Generate intelligent seed keywords using AI based on market analysis"""
        try:
            logger.info("🤖 Generating AI-powered seed keywords...")
            
            # Get current market trends
            market_trends = await self.trend_ai.analyze_trends(
                keywords=["market trends", "consumer behavior", "emerging markets"],
                mode=TrendAnalysisMode.DISCOVERY,
                categories=["general"],
                geo="US",
                time_range="now 1-d"
            )
            
            # Extract keywords from AI analysis
            ai_keywords = []
            for trend in market_trends[:5]:  # Top 5 trends
                ai_keywords.append(trend.trend_name)
                ai_keywords.extend(trend.marketing_angles[:2])  # Add marketing angles as keywords
            
            # Add some default keywords as fallback
            default_keywords = ["trending", "viral", "popular", "hot", "new"]
            ai_keywords.extend(default_keywords)
            
            # Remove duplicates and limit
            unique_keywords = list(set(ai_keywords))[:20]
            
            logger.info(f"✅ Generated {len(unique_keywords)} AI-powered keywords")
            return unique_keywords
            
        except Exception as e:
            logger.warning(f"⚠️ AI keyword generation failed, using defaults: {e}")
            return ["trending", "viral", "popular", "hot", "new"]
    
    async def _get_ai_insights_for_opportunities(self, opportunities: List[Any]) -> Dict[str, Any]:
        """Get AI insights for validated opportunities"""
        try:
            insights = {
                "total_opportunities": len(opportunities),
                "ai_recommendations": [],
                "strategy_optimization": None,
                "priority_ranking": []
            }
            
            # Convert opportunities to AI format for analysis
            ai_trends = []
            for opp in opportunities:
                # Simple conversion - this would be more detailed in production
                ai_trends.append({
                    "trend_name": opp.trend_name,
                    "opportunity_score": opp.opportunity_score,
                    "category": opp.category
                })
            
            # Get AI strategy optimization
            if ai_trends:
                strategy = await self.trend_ai.optimize_trend_strategy(
                    ai_trends,
                    business_constraints={
                        "budget": "automated",
                        "resources": "cloud-based",
                        "min_roi": 3.0,
                        "max_products_per_day": 50
                    }
                )
                insights["strategy_optimization"] = strategy
            
            logger.info("✅ AI insights generated for opportunities")
            return insights
            
        except Exception as e:
            logger.error(f"❌ Failed to generate AI insights: {e}")
            return {"error": str(e)}
    
    async def _get_existing_opportunities(self) -> List[Dict[str, Any]]:
        """Get existing trend opportunities from storage"""
        try:
            if self.firestore_client:
                # Get from Firestore
                opportunities = await self.firestore_client.get_collection("trend_opportunities")
                return [doc.to_dict() for doc in opportunities if doc.exists]
            else:
                # Fallback to empty list
                return []
        except Exception as e:
            logger.error(f"❌ Failed to get existing opportunities: {e}")
            return []
    
    async def _get_active_experiments(self) -> List[Dict[str, Any]]:
        """Get active A/B test experiments"""
        try:
            if self.firestore_client:
                # Get from Firestore
                experiments = await self.firestore_client.get_collection("ab_experiments")
                return [doc.to_dict() for doc in experiments if doc.exists and doc.get("status") == "active"]
            else:
                # Fallback to empty list
                return []
        except Exception as e:
            logger.error(f"❌ Failed to get active experiments: {e}")
            return []
    
    async def _store_discovery_results(self, opportunities: List[Dict[str, Any]]) -> None:
        """Store trend discovery results"""
        try:
            if self.firestore_client:
                for opportunity in opportunities:
                    await self.firestore_client.add_document(
                        "trend_opportunities",
                        opportunity
                    )
        except Exception as e:
            logger.error(f"❌ Failed to store discovery results: {e}")
    
    async def _store_product_results(self, products: List[Dict[str, Any]]) -> None:
        """Store product generation results"""
        try:
            if self.firestore_client:
                for product in products:
                    await self.firestore_client.add_document(
                        "generated_products",
                        product
                    )
        except Exception as e:
            logger.error(f"❌ Failed to store product results: {e}")
    
    async def _store_optimization_results(self, results: List[Dict[str, Any]]) -> None:
        """Store performance optimization results"""
        try:
            if self.firestore_client:
                for result in results:
                    await self.firestore_client.add_document(
                        "optimization_results",
                        result
                    )
        except Exception as e:
            logger.error(f"❌ Failed to store optimization results: {e}")
    
    async def _generate_cycle_summary(
        self,
        discovery_result: Dict[str, Any],
        generation_result: Dict[str, Any],
        optimization_result: Dict[str, Any],
        session: OrchestrationSession
    ) -> Dict[str, Any]:
        """Generate summary of the orchestration cycle"""
        return {
            "status": "success",
            "session_id": session.session_id,
            "execution_time": session.execution_time,
            "trends_discovered": session.trends_discovered,
            "products_generated": session.products_generated,
            "experiments_created": session.experiments_created,
            "discovery_result": discovery_result,
            "generation_result": generation_result,
            "optimization_result": optimization_result,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def get_orchestration_summary(self) -> Dict[str, Any]:
        """Get summary of all orchestration sessions"""
        return {
            "total_sessions": len(self.session_history),
            "active_session": self.active_session.session_id if self.active_session else None,
            "recent_sessions": [
                {
                    "session_id": session.session_id,
                    "status": session.status,
                    "execution_time": session.execution_time,
                    "trends_discovered": session.trends_discovered,
                    "products_generated": session.products_generated,
                    "experiments_created": session.experiments_created,
                    "start_time": session.start_time.isoformat(),
                    "end_time": session.end_time.isoformat() if session.end_time else None
                }
                for session in self.session_history[-10:]  # Last 10 sessions
            ]
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            logger.info("🧹 Cleaning up Helios orchestrator...")
            
            if self.trend_discovery:
                await self.trend_discovery.cleanup()
            
            if self.product_pipeline:
                await self.product_pipeline.cleanup()
            
            if self.performance_optimization:
                await self.performance_optimization.cleanup()
            
            if self.scheduler_client:
                await self.scheduler_client.close()
            
            logger.info("✅ Cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")


async def create_helios_orchestrator(config: HeliosConfig) -> HeliosOrchestrator:
    """Create and initialize Helios orchestrator"""
    orchestrator = HeliosOrchestrator(config)
    
    # Initialize services (some may fail in development mode)
    await orchestrator.initialize_services()
    
    return orchestrator
