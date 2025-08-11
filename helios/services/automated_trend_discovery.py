"""
Automated Trend Discovery Service for Helios
Runs every 6 hours to automatically find new trends and validate opportunities
"""

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from loguru import logger

from ..agents.ceo import HeliosCEO
from ..agents.zeitgeist import ZeitgeistAgent
from ..services.mcp_integration.google_trends_client import GoogleTrendsClient
from ..services.mcp_integration.social_trends_scanner import SocialTrendsScanner
from ..services.mcp_integration.news_sentiment_analyzer import NewsSentimentAnalyzer
from ..services.mcp_integration.competitor_intelligence import CompetitorIntelligenceService
from ..config import HeliosConfig
from ..utils.performance_monitor import PerformanceMonitor


@dataclass
class TrendOpportunity:
    """Trend opportunity data structure"""
    trend_id: str
    trend_name: str
    category: str
    opportunity_score: float
    confidence_level: float
    market_size: str
    competition_level: str
    velocity: str
    geo_relevance: List[str]
    audience_demographics: Dict[str, Any]
    related_keywords: List[str]
    social_sentiment: float
    news_sentiment: float
    competitor_activity: Dict[str, Any]
    validation_status: str = "pending"
    ceo_decision: Optional[Dict[str, Any]] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DiscoverySession:
    """Trend discovery session data"""
    session_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    trends_discovered: int = 0
    opportunities_validated: int = 0
    opportunities_approved: int = 0
    execution_time: float = 0.0
    status: str = "running"
    errors: List[str] = field(default_factory=list)


class AutomatedTrendDiscovery:
    """Automated trend discovery service that runs every 6 hours"""
    
    def __init__(self, config: HeliosConfig):
        self.config = config
        self.ceo_agent = HeliosCEO(
            min_opportunity=config.min_opportunity_score,
            min_confidence=config.min_audience_confidence
        )
        self.zeitgeist_agent = ZeitgeistAgent()
        self.google_trends_client = GoogleTrendsClient()
        self.social_scanner = SocialTrendsScanner()
        self.news_analyzer = NewsSentimentAnalyzer()
        self.competitor_intel = CompetitorIntelligenceService(
            project_id=config.google_cloud_project or "helios-pod-system",
            location=config.google_cloud_region or "us-central1"
        )
        self.performance_monitor = PerformanceMonitor(config)
        
        # Discovery configuration
        self.discovery_interval = timedelta(hours=6)
        self.max_trends_per_session = 50
        self.min_opportunity_threshold = config.min_opportunity_score
        self.min_confidence_threshold = config.min_audience_confidence
        
        # Session tracking
        self.active_session: Optional[DiscoverySession] = None
        self.discovery_history: List[DiscoverySession] = []
        
        logger.info("✅ Automated Trend Discovery Service initialized")
    
    async def start_discovery_session(self, seed_keywords: List[str] = None) -> DiscoverySession:
        """Start a new trend discovery session"""
        session_id = f"discovery_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        self.active_session = DiscoverySession(
            session_id=session_id,
            start_time=datetime.now(timezone.utc)
        )
        
        logger.info(f"🔍 Starting discovery session: {session_id}")
        return self.active_session
    
    async def run_discovery_pipeline(self, seed_keywords: List[str] = None) -> Dict[str, Any]:
        """Run the complete automated discovery pipeline"""
        start_time = time.time()
        
        try:
            # Start discovery session
            session = await self.start_discovery_session(seed_keywords)
            
            # STAGE 1: Multi-source trend discovery
            logger.info("🔍 STAGE 1: Multi-source trend discovery")
            trends_data = await self._discover_trends_multi_source(seed_keywords)
            
            # STAGE 2: Trend analysis and scoring
            logger.info("📊 STAGE 2: Trend analysis and scoring")
            analyzed_trends = await self._analyze_trends(trends_data)
            
            # STAGE 3: CEO validation
            logger.info("👔 STAGE 3: CEO validation")
            validated_opportunities = await self._validate_opportunities(analyzed_trends)
            
            # STAGE 4: Session completion
            session.end_time = datetime.now(timezone.utc)
            session.execution_time = time.time() - start_time
            session.trends_discovered = len(trends_data)
            session.opportunities_validated = len(validated_opportunities)
            session.opportunities_approved = len([o for o in validated_opportunities if o.validation_status == "approved"])
            session.status = "completed"
            
            # Record performance metrics
            self.performance_monitor.record_metric_with_labels(
                "discovery_session_duration",
                session.execution_time,
                labels={"session_id": session.session_id}
            )
            
            self.performance_monitor.record_metric_with_labels(
                "trends_discovered_per_session",
                session.trends_discovered,
                labels={"session_id": session.session_id}
            )
            
            self.performance_monitor.record_metric_with_labels(
                "opportunities_approved_per_session",
                session.opportunities_approved,
                labels={"session_id": session.session_id}
            )
            
            # Store session in history
            self.discovery_history.append(session)
            
            logger.info(f"✅ Discovery session completed: {session.opportunities_approved} opportunities approved")
            
            return {
                "session": session,
                "trends_discovered": trends_data,
                "opportunities_validated": validated_opportunities,
                "execution_time": session.execution_time,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ Discovery pipeline failed: {e}")
            if self.active_session:
                self.active_session.status = "failed"
                self.active_session.errors.append(str(e))
                self.active_session.end_time = datetime.now(timezone.utc)
                self.active_session.execution_time = time.time() - start_time
            
            return {
                "status": "error",
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def _discover_trends_multi_source(self, seed_keywords: List[str] = None) -> List[Dict[str, Any]]:
        """Discover trends from multiple sources in parallel"""
        tasks = []
        
        # Google Trends discovery
        tasks.append(self._discover_google_trends(seed_keywords))
        
        # Social media trends
        tasks.append(self._discover_social_trends(seed_keywords))
        
        # News sentiment analysis
        tasks.append(self._discover_news_trends(seed_keywords))
        
        # Competitor intelligence
        tasks.append(self._discover_competitor_trends(seed_keywords))
        
        # Zeitgeist agent discovery
        if seed_keywords:
            tasks.append(self._discover_zeitgeist_trends(seed_keywords))
        
        # Execute all discovery tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Combine and deduplicate results
        all_trends = []
        for result in results:
            if isinstance(result, list):
                all_trends.extend(result)
            elif isinstance(result, dict) and "trends" in result:
                all_trends.extend(result["trends"])
        
        # Deduplicate by trend name
        unique_trends = {}
        for trend in all_trends:
            trend_name = trend.get("trend_name", "").lower().strip()
            if trend_name and trend_name not in unique_trends:
                unique_trends[trend_name] = trend
        
        logger.info(f"🔍 Discovered {len(unique_trends)} unique trends from multiple sources")
        return list(unique_trends.values())
    
    async def _discover_google_trends(self, seed_keywords: List[str] = None) -> List[Dict[str, Any]]:
        """Discover trends using Google Trends"""
        try:
            # Get trending searches
            trending_searches = await self.google_trends_client.get_trending_searches(
                geo="US", category="all"
            )
            
            # Get category-specific trends
            category_trends = await self.google_trends_client.get_category_trends(
                category="shopping", geo="US", time_range="now 7-d"
            )
            
            # Combine results
            trends = []
            if "trending_searches" in trending_searches:
                trends.extend(trending_searches["trending_searches"])
            
            if "trends" in category_trends:
                trends.extend(category_trends["trends"])
            
            # Add seed keyword analysis if provided
            if seed_keywords:
                for keyword in seed_keywords[:5]:  # Limit to 5 keywords
                    try:
                        interest_data = await self.google_trends_client.get_interest_over_time(
                            query=keyword, geo="US", time_range="now 7-d"
                        )
                        if "interest_data" in interest_data:
                            trends.append({
                                "trend_name": keyword,
                                "source": "google_trends_seed",
                                "interest_data": interest_data["interest_data"],
                                "trend_score": interest_data.get("trend_score", 0)
                            })
                    except Exception as e:
                        logger.warning(f"Failed to analyze seed keyword {keyword}: {e}")
            
            logger.info(f"🔍 Google Trends: Discovered {len(trends)} trends")
            return trends
            
        except Exception as e:
            logger.error(f"❌ Google Trends discovery failed: {e}")
            return []
    
    async def _discover_social_trends(self, seed_keywords: List[str] = None) -> List[Dict[str, Any]]:
        """Discover trends from social media"""
        try:
            social_trends = await self.social_scanner.scan_trending_topics(
                platforms=["twitter", "instagram", "tiktok"],
                categories=["fashion", "lifestyle", "entertainment"],
                limit=20
            )
            
            trends = []
            if "trending_topics" in social_trends:
                for topic in social_trends["trending_topics"]:
                    trends.append({
                        "trend_name": topic.get("topic", ""),
                        "source": "social_media",
                        "platform": topic.get("platform", ""),
                        "engagement": topic.get("engagement", 0),
                        "trend_score": topic.get("trend_score", 0)
                    })
            
            logger.info(f"🔍 Social Media: Discovered {len(trends)} trends")
            return trends
            
        except Exception as e:
            logger.error(f"❌ Social trends discovery failed: {e}")
            return []
    
    async def _discover_news_trends(self, seed_keywords: List[str] = None) -> List[Dict[str, Any]]:
        """Discover trends from news analysis"""
        try:
            news_trends = await self.news_analyzer.analyze_trending_topics(
                categories=["business", "technology", "entertainment"],
                time_window="7d",
                limit=15
            )
            
            trends = []
            if "trending_topics" in news_trends:
                for topic in news_trends["trending_topics"]:
                    trends.append({
                        "trend_name": topic.get("topic", ""),
                        "source": "news_analysis",
                        "sentiment": topic.get("sentiment", 0),
                        "volume": topic.get("volume", 0),
                        "trend_score": topic.get("trend_score", 0)
                    })
            
            logger.info(f"🔍 News Analysis: Discovered {len(trends)} trends")
            return trends
            
        except Exception as e:
            logger.error(f"❌ News trends discovery failed: {e}")
            return []
    
    async def _discover_competitor_trends(self, seed_keywords: List[str] = None) -> List[Dict[str, Any]]:
        """Discover trends from competitor intelligence"""
        try:
            competitor_trends = await self.competitor_intel.analyze_competitor_trends(
                competitors=["etsy", "redbubble", "teepublic"],
                categories=["vintage_gaming", "retro_style", "gaming_merch"],
                time_window="30d"
            )
            
            trends = []
            if "trending_products" in competitor_trends:
                for product in competitor_trends["trending_products"]:
                    trends.append({
                        "trend_name": product.get("product_name", ""),
                        "source": "competitor_intelligence",
                        "competitor": product.get("competitor", ""),
                        "sales_velocity": product.get("sales_velocity", 0),
                        "trend_score": product.get("trend_score", 0)
                    })
            
            logger.info(f"🔍 Competitor Intelligence: Discovered {len(trends)} trends")
            return trends
            
        except Exception as e:
            logger.error(f"❌ Competitor trends discovery failed: {e}")
            return []
    
    async def _discover_zeitgeist_trends(self, seed_keywords: List[str] = None) -> List[Dict[str, Any]]:
        """Discover trends using Zeitgeist agent"""
        try:
            zeitgeist_result = await self.zeitgeist_agent.run(
                seed=" ".join(seed_keywords) if seed_keywords else None
            )
            
            trends = []
            if zeitgeist_result.get("status") == "approved":
                trend_data = zeitgeist_result.get("trend_data", {})
                trends.append({
                    "trend_name": trend_data.get("trend_name", ""),
                    "source": "zeitgeist_agent",
                    "opportunity_score": trend_data.get("opportunity_score", 0),
                    "confidence_level": trend_data.get("confidence_level", 0),
                    "trend_score": trend_data.get("trend_score", 0)
                })
            
            logger.info(f"🔍 Zeitgeist Agent: Discovered {len(trends)} trends")
            return trends
            
        except Exception as e:
            logger.error(f"❌ Zeitgeist trends discovery failed: {e}")
            return []
    
    async def _analyze_trends(self, trends_data: List[Dict[str, Any]]) -> List[TrendOpportunity]:
        """Analyze and score discovered trends"""
        opportunities = []
        
        for trend in trends_data:
            try:
                # Calculate composite trend score
                trend_score = self._calculate_composite_score(trend)
                
                # Skip low-scoring trends
                if trend_score < self.min_opportunity_threshold:
                    continue
                
                # Create trend opportunity
                opportunity = TrendOpportunity(
                    trend_id=f"trend_{int(time.time())}_{len(opportunities)}",
                    trend_name=trend.get("trend_name", ""),
                    category=trend.get("category", "general"),
                    opportunity_score=trend_score,
                    confidence_level=trend.get("confidence_level", 0.5),
                    market_size=self._estimate_market_size(trend),
                    competition_level=self._assess_competition(trend),
                    velocity=self._assess_velocity(trend),
                    geo_relevance=trend.get("geo_relevance", ["US"]),
                    audience_demographics=self._analyze_audience(trend),
                    related_keywords=trend.get("related_keywords", []),
                    social_sentiment=trend.get("social_sentiment", 0.0),
                    news_sentiment=trend.get("news_sentiment", 0.0),
                    competitor_activity=trend.get("competitor_activity", {})
                )
                
                opportunities.append(opportunity)
                
            except Exception as e:
                logger.warning(f"Failed to analyze trend {trend.get('trend_name', 'unknown')}: {e}")
                continue
        
        # Sort by opportunity score (highest first)
        opportunities.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        # Limit to top opportunities
        opportunities = opportunities[:self.max_trends_per_session]
        
        logger.info(f"📊 Analyzed {len(opportunities)} high-scoring opportunities")
        return opportunities
    
    async def _validate_opportunities(self, opportunities: List[TrendOpportunity]) -> List[TrendOpportunity]:
        """Validate opportunities using CEO agent"""
        validated_opportunities = []
        
        for opportunity in opportunities:
            try:
                # Prepare trend data for CEO validation
                trend_data = {
                    "trend_name": opportunity.trend_name,
                    "opportunity_score": opportunity.opportunity_score,
                    "confidence_level": opportunity.confidence_level,
                    "market_size": opportunity.market_size,
                    "competition_level": opportunity.competition_level,
                    "velocity": opportunity.velocity,
                    "audience_demographics": opportunity.audience_demographics,
                    "related_keywords": opportunity.related_keywords
                }
                
                # CEO validation
                ceo_decision = await self.ceo_agent.validate_trend(trend_data)
                
                # Update opportunity with CEO decision
                opportunity.ceo_decision = {
                    "approved": ceo_decision.approved,
                    "priority": ceo_decision.priority.value if hasattr(ceo_decision.priority, 'value') else "medium",
                    "reasoning": ceo_decision.reasoning,
                    "mcp_model_used": ceo_decision.mcp_model_used
                }
                
                if ceo_decision.approved:
                    opportunity.validation_status = "approved"
                    logger.info(f"✅ CEO approved: {opportunity.trend_name} (score: {opportunity.opportunity_score})")
                else:
                    opportunity.validation_status = "rejected"
                    logger.info(f"❌ CEO rejected: {opportunity.trend_name} (score: {opportunity.opportunity_score})")
                
                validated_opportunities.append(opportunity)
                
            except Exception as e:
                logger.warning(f"Failed to validate opportunity {opportunity.trend_name}: {e}")
                opportunity.validation_status = "validation_failed"
                opportunity.ceo_decision = {"error": str(e)}
                validated_opportunities.append(opportunity)
        
        return validated_opportunities
    
    def _calculate_composite_score(self, trend: Dict[str, Any]) -> float:
        """Calculate composite trend score"""
        base_score = 0.0
        
        # Source-specific scoring
        source = trend.get("source", "")
        if source == "google_trends":
            base_score += trend.get("trend_score", 0) * 0.3
        elif source == "social_media":
            base_score += trend.get("trend_score", 0) * 0.25
        elif source == "news_analysis":
            base_score += trend.get("trend_score", 0) * 0.2
        elif source == "competitor_intelligence":
            base_score += trend.get("trend_score", 0) * 0.25
        elif source == "zeitgeist_agent":
            base_score += trend.get("trend_score", 0) * 0.3
        
        # Engagement metrics
        engagement = trend.get("engagement", 0)
        base_score += min(engagement / 1000, 1.0) * 0.2
        
        # Sentiment bonus
        sentiment = trend.get("sentiment", 0)
        if sentiment > 0.6:
            base_score += 0.1
        elif sentiment < 0.4:
            base_score -= 0.1
        
        # Volume bonus
        volume = trend.get("volume", 0)
        if volume > 1000:
            base_score += 0.1
        
        return min(max(base_score, 0.0), 10.0)
    
    def _estimate_market_size(self, trend: Dict[str, Any]) -> str:
        """Estimate market size based on trend data"""
        engagement = trend.get("engagement", 0)
        volume = trend.get("volume", 0)
        
        if engagement > 10000 or volume > 10000:
            return "large"
        elif engagement > 1000 or volume > 1000:
            return "medium"
        else:
            return "small"
    
    def _assess_competition(self, trend: Dict[str, Any]) -> str:
        """Assess competition level"""
        competitor_activity = trend.get("competitor_activity", {})
        if competitor_activity.get("high_activity", False):
            return "high"
        elif competitor_activity.get("medium_activity", False):
            return "medium"
        else:
            return "low"
    
    def _assess_velocity(self, trend: Dict[str, Any]) -> str:
        """Assess trend velocity"""
        trend_score = trend.get("trend_score", 0)
        if trend_score > 7.0:
            return "high"
        elif trend_score > 4.0:
            return "medium"
        else:
            return "low"
    
    def _analyze_audience(self, trend: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze audience demographics"""
        return {
            "age_groups": ["18-24", "25-34", "35-44"],
            "interests": trend.get("related_keywords", [])[:5],
            "geographic_focus": trend.get("geo_relevance", ["US"]),
            "platform_preference": trend.get("source", "general")
        }
    
    async def get_discovery_summary(self) -> Dict[str, Any]:
        """Get summary of discovery activities"""
        total_sessions = len(self.discovery_history)
        total_trends = sum(s.trends_discovered for s in self.discovery_history)
        total_opportunities = sum(s.opportunities_validated for s in self.discovery_history)
        total_approved = sum(s.opportunities_approved for s in self.discovery_history)
        
        return {
            "total_sessions": total_sessions,
            "total_trends_discovered": total_trends,
            "total_opportunities_validated": total_opportunities,
            "total_opportunities_approved": total_approved,
            "approval_rate": total_approved / total_opportunities if total_opportunities > 0 else 0,
            "last_session": self.discovery_history[-1] if self.discovery_history else None,
            "active_session": self.active_session
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.google_trends_client.close()
            await self.social_scanner.close()
            await self.news_analyzer.close()
            await self.competitor_intel.close()
            await self.performance_monitor.close()
            logger.info("✅ Automated Trend Discovery Service cleaned up")
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")


async def create_automated_trend_discovery(config: HeliosConfig) -> AutomatedTrendDiscovery:
    """Factory function to create automated trend discovery service"""
    return AutomatedTrendDiscovery(config)
