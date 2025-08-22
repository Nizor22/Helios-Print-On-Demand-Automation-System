"""
Google Trends Client for Helios Autonomous Store
Integrates with MCP framework for Google Trends data analysis and trend discovery
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
import httpx
from loguru import logger

from .mcp_client import GoogleMCPClient


@dataclass
class TrendData:
    """Google Trends data structure"""
    query: str
    value: int
    timestamp: datetime
    geo: str
    category: str
    related_queries: List[str]
    related_topics: List[str]
    interest_over_time: List[Dict[str, Any]]
    regional_interest: List[Dict[str, Any]]


@dataclass
class TrendComparison:
    """Trend comparison data structure"""
    queries: List[str]
    geo: str
    time_range: str
    comparison_data: List[Dict[str, Any]]
    relative_interest: Dict[str, List[int]]


@dataclass
class TrendingSearch:
    """Trending search data structure"""
    title: str
    traffic: str
    image_url: str = None
    articles: List[Dict[str, Any]] = None


class GoogleTrendsClient:
    """
    Google Trends client using MCP integration
    Provides comprehensive Google Trends data analysis
    """
    
    def __init__(self, mcp_client: GoogleMCPClient = None):
        self.mcp_client = mcp_client or GoogleMCPClient()
        self.supported_categories = [
            "all", "arts", "autos", "beauty", "books", "business", "computers",
            "dining", "education", "entertainment", "finance", "games", "health",
            "hobbies", "home", "industrial", "law", "news", "politics", "real_estate",
            "science", "shopping", "society", "sports", "technology", "travel"
        ]
        
        self.time_ranges = [
            "now 1-H", "now 4-H", "now 1-d", "now 7-d", "today 1-m", "today 3-m",
            "today 12-m", "today 5-y", "all"
        ]
        
        # Rate limiting configuration
        self.rate_limit_delay = 1.0  # seconds between requests
        self.max_retries = 3
        
        logger.info("✅ Google Trends Client initialized")
    
    async def get_trending_searches(
        self,
        geo: str = "US",
        category: str = "all"
    ) -> Dict[str, Any]:
        """Get trending searches for a specific location and category"""
        
        try:
            # Use MCP client for trending searches
            result = await self.mcp_client.get_google_trends(
                query="trending",
                geo=geo,
                time_range="now 1-d",
                category=category
            )
            
            # Process and enhance the results
            enhanced_result = await self._process_trending_searches(result, geo, category)
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error getting trending searches: {e}")
            return {"error": str(e), "geo": geo, "category": category}
    
    async def get_interest_over_time(
        self,
        query: str,
        geo: str = "US",
        time_range: str = "today 12-m",
        category: str = "all"
    ) -> Dict[str, Any]:
        """Get interest over time for a specific query"""
        
        try:
            # Use MCP client for interest over time
            result = await self.mcp_client.get_google_trends(
                query=query,
                geo=geo,
                time_range=time_range,
                category=category
            )
            
            # Process and enhance the results
            enhanced_result = await self._process_interest_over_time(result, query, geo, time_range)
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error getting interest over time: {e}")
            return {"error": str(e), "query": query, "geo": geo}
    
    async def get_related_queries(
        self,
        query: str,
        geo: str = "US",
        time_range: str = "today 12-m",
        category: str = "all"
    ) -> Dict[str, Any]:
        """Get related queries for a specific search term"""
        
        try:
            # Use MCP client for related queries
            result = await self.mcp_client.get_google_trends(
                query=query,
                geo=geo,
                time_range=time_range,
                category=category
            )
            
            # Process and enhance the results
            enhanced_result = await self._process_related_queries(result, query, geo)
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error getting related queries: {e}")
            return {"error": str(e), "query": query, "geo": geo}
    
    async def get_related_topics(
        self,
        query: str,
        geo: str = "US",
        time_range: str = "today 12-m",
        category: str = "all"
    ) -> Dict[str, Any]:
        """Get related topics for a specific search term"""
        
        try:
            # Use MCP client for related topics
            result = await self.mcp_client.get_google_trends(
                query=query,
                geo=geo,
                time_range=time_range,
                category=category
            )
            
            # Process and enhance the results
            enhanced_result = await self._process_related_topics(result, query, geo)
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error getting related topics: {e}")
            return {"error": str(e), "query": query, "geo": geo}
    
    async def get_regional_interest(
        self,
        query: str,
        geo: str = "US",
        time_range: str = "today 12-m",
        category: str = "all"
    ) -> Dict[str, Any]:
        """Get regional interest for a specific query"""
        
        try:
            # Use MCP client for regional interest
            result = await self.mcp_client.get_google_trends(
                query=query,
                geo=geo,
                time_range=time_range,
                category=category
            )
            
            # Process and enhance the results
            enhanced_result = await self._process_regional_interest(result, query, geo)
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error getting regional interest: {e}")
            return {"error": str(e), "query": query, "geo": geo}
    
    async def compare_trends(
        self,
        queries: List[str],
        geo: str = "US",
        time_range: str = "today 12-m",
        category: str = "all"
    ) -> Dict[str, Any]:
        """Compare multiple search terms"""
        
        if len(queries) < 2:
            return {"error": "At least 2 queries required for comparison"}
        
        if len(queries) > 5:
            return {"error": "Maximum 5 queries allowed for comparison"}
        
        try:
            # Use MCP client for trend comparison
            comparison_data = []
            for query in queries:
                result = await self.mcp_client.get_google_trends(
                    query=query,
                    geo=geo,
                    time_range=time_range,
                    category=category
                )
                comparison_data.append({
                    "query": query,
                    "data": result
                })
            
            # Process and enhance the comparison
            enhanced_comparison = await self._process_trend_comparison(
                comparison_data, queries, geo, time_range
            )
            return enhanced_comparison
            
        except Exception as e:
            logger.error(f"Error comparing trends: {e}")
            return {"error": str(e), "queries": queries, "geo": geo}
    
    async def discover_trending_topics(
        self,
        seed_keywords: List[str] = None,
        categories: List[str] = None,
        geo: str = "US",
        time_range: str = "today 12-m",
        limit: int = 20
    ) -> Dict[str, Any]:
        """Discover trending topics based on seed keywords and categories"""
        
        try:
            # Use MCP client for trend discovery
            result = await self.mcp_client.discover_trends(
                seed_keywords=seed_keywords or [],
                categories=categories or ["all"],
                geo=geo,
                time_range=time_range
            )
            
            # Process and enhance the results
            enhanced_result = await self._process_trend_discovery(result, seed_keywords, categories)
            
            # Limit results if specified
            if "trends" in enhanced_result and limit:
                enhanced_result["trends"] = enhanced_result["trends"][:limit]
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error discovering trending topics: {e}")
            return {"error": str(e), "seed_keywords": seed_keywords, "categories": categories}
    
    async def analyze_trend_velocity(
        self,
        query: str,
        geo: str = "US",
        time_range: str = "today 12-m"
    ) -> Dict[str, Any]:
        """Analyze trend velocity and momentum"""
        
        try:
            # Get interest over time data
            interest_data = await self.get_interest_over_time(query, geo, time_range)
            
            if "error" in interest_data:
                return interest_data
            
            # Calculate velocity metrics
            velocity_analysis = await self._calculate_trend_velocity(interest_data, query)
            return velocity_analysis
            
        except Exception as e:
            logger.error(f"Error analyzing trend velocity: {e}")
            return {"error": str(e), "query": query, "geo": geo}
    
    async def get_category_trends(
        self,
        category: str,
        geo: str = "US",
        time_range: str = "today 12-m",
        limit: int = 10
    ) -> Dict[str, Any]:
        """Get trending topics within a specific category"""
        
        if category not in self.supported_categories:
            return {"error": f"Unsupported category: {category}"}
        
        try:
            # Use MCP client for category trends
            result = await self.mcp_client.discover_trends(
                seed_keywords=[],
                categories=[category],
                geo=geo,
                time_range=time_range
            )
            
            # Process and enhance the results
            enhanced_result = await self._process_category_trends(result, category, geo)
            
            # Limit results if specified
            if "trends" in enhanced_result and limit:
                enhanced_result["trends"] = enhanced_result["trends"][:limit]
            
            return enhanced_result
            
        except Exception as e:
            logger.error(f"Error getting category trends: {e}")
            return {"error": str(e), "category": category, "geo": geo}
    
    async def _process_trending_searches(
        self,
        data: Dict[str, Any],
        geo: str,
        category: str
    ) -> Dict[str, Any]:
        """Process trending searches data"""
        
        try:
            enhanced_data = data.copy()
            
            # Add metadata
            enhanced_data["metadata"] = {
                "geo": geo,
                "category": category,
                "timestamp": datetime.now().isoformat(),
                "data_source": "Google Trends via MCP"
            }
            
            # Add trend scoring if trends exist
            if "trends" in enhanced_data:
                for trend in enhanced_data["trends"]:
                    trend["trend_score"] = self._calculate_trend_score(trend)
                    trend["momentum"] = self._calculate_trend_momentum(trend)
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error processing trending searches: {e}")
            return data
    
    async def _process_interest_over_time(
        self,
        data: Dict[str, Any],
        query: str,
        geo: str,
        time_range: str
    ) -> Dict[str, Any]:
        """Process interest over time data"""
        
        try:
            enhanced_data = data.copy()
            
            # Add metadata
            enhanced_data["metadata"] = {
                "query": query,
                "geo": geo,
                "time_range": time_range,
                "timestamp": datetime.now().isoformat(),
                "data_source": "Google Trends via MCP"
            }
            
            # Add trend analysis if time series data exists
            if "interest_over_time" in enhanced_data:
                enhanced_data["trend_analysis"] = await self._analyze_time_series(
                    enhanced_data["interest_over_time"]
                )
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error processing interest over time: {e}")
            return data
    
    async def _process_related_queries(
        self,
        data: Dict[str, Any],
        query: str,
        geo: str
    ) -> Dict[str, Any]:
        """Process related queries data"""
        
        try:
            enhanced_data = data.copy()
            
            # Add metadata
            enhanced_data["metadata"] = {
                "query": query,
                "geo": geo,
                "timestamp": datetime.now().isoformat(),
                "data_source": "Google Trends via MCP"
            }
            
            # Add relevance scoring if related queries exist
            if "related_queries" in enhanced_data:
                for related_query in enhanced_data["related_queries"]:
                    related_query["relevance_score"] = self._calculate_relevance_score(
                        related_query, query
                    )
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error processing related queries: {e}")
            return data
    
    async def _process_related_topics(
        self,
        data: Dict[str, Any],
        query: str,
        geo: str
    ) -> Dict[str, Any]:
        """Process related topics data"""
        
        try:
            enhanced_data = data.copy()
            
            # Add metadata
            enhanced_data["metadata"] = {
                "query": query,
                "geo": geo,
                "timestamp": datetime.now().isoformat(),
                "data_source": "Google Trends via MCP"
            }
            
            # Add topic categorization if related topics exist
            if "related_topics" in enhanced_data:
                for topic in enhanced_data["related_topics"]:
                    topic["category"] = self._categorize_topic(topic)
                    topic["relevance_score"] = self._calculate_topic_relevance(topic, query)
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error processing related topics: {e}")
            return data
    
    async def _process_regional_interest(
        self,
        data: Dict[str, Any],
        query: str,
        geo: str
    ) -> Dict[str, Any]:
        """Process regional interest data"""
        
        try:
            enhanced_data = data.copy()
            
            # Add metadata
            enhanced_data["metadata"] = {
                "query": query,
                "geo": geo,
                "timestamp": datetime.now().isoformat(),
                "data_source": "Google Trends via MCP"
            }
            
            # Add regional analysis if regional data exists
            if "regional_interest" in enhanced_data:
                enhanced_data["regional_analysis"] = await self._analyze_regional_data(
                    enhanced_data["regional_interest"]
                )
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error processing regional interest: {e}")
            return data
    
    async def _process_trend_comparison(
        self,
        comparison_data: List[Dict[str, Any]],
        queries: List[str],
        geo: str,
        time_range: str
    ) -> Dict[str, Any]:
        """Process trend comparison data"""
        
        try:
            enhanced_comparison = {
                "queries": queries,
                "geo": geo,
                "time_range": time_range,
                "timestamp": datetime.now().isoformat(),
                "data_source": "Google Trends via MCP",
                "comparison_data": comparison_data,
                "analysis": {}
            }
            
            # Add comparative analysis
            if comparison_data:
                enhanced_comparison["analysis"] = await self._analyze_trend_comparison_data(
                    comparison_data, queries
                )
            
            return enhanced_comparison
            
        except Exception as e:
            logger.error(f"Error processing trend comparison: {e}")
            return {"error": str(e), "queries": queries}
    
    async def _process_trend_discovery(
        self,
        data: Dict[str, Any],
        seed_keywords: List[str],
        categories: List[str]
    ) -> Dict[str, Any]:
        """Process trend discovery data"""
        
        try:
            enhanced_data = data.copy()
            
            # Add metadata
            enhanced_data["metadata"] = {
                "seed_keywords": seed_keywords,
                "categories": categories,
                "timestamp": datetime.now().isoformat(),
                "data_source": "Google Trends via MCP"
            }
            
            # Add discovery insights if trends exist
            if "trends" in enhanced_data:
                enhanced_data["discovery_insights"] = await self._analyze_discovery_insights(
                    enhanced_data["trends"], seed_keywords, categories
                )
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error processing trend discovery: {e}")
            return data
    
    async def _process_category_trends(
        self,
        data: Dict[str, Any],
        category: str,
        geo: str
    ) -> Dict[str, Any]:
        """Process category trends data"""
        
        try:
            enhanced_data = data.copy()
            
            # Add metadata
            enhanced_data["metadata"] = {
                "category": category,
                "geo": geo,
                "timestamp": datetime.now().isoformat(),
                "data_source": "Google Trends via MCP"
            }
            
            # Add category-specific analysis if trends exist
            if "trends" in enhanced_data:
                enhanced_data["category_analysis"] = await self._analyze_category_trends(
                    enhanced_data["trends"], category
                )
            
            return enhanced_data
            
        except Exception as e:
            logger.error(f"Error processing category trends: {e}")
            return data
    
    async def _calculate_trend_velocity(
        self,
        interest_data: Dict[str, Any],
        query: str
    ) -> Dict[str, Any]:
        """Calculate trend velocity and momentum"""
        
        try:
            if "interest_over_time" not in interest_data:
                return {"error": "No time series data available"}
            
            time_series = interest_data["interest_over_time"]
            
            if len(time_series) < 2:
                return {"error": "Insufficient data for velocity calculation"}
            
            # Calculate velocity metrics
            velocities = []
            accelerations = []
            
            for i in range(1, len(time_series)):
                current_value = time_series[i].get("value", 0)
                previous_value = time_series[i-1].get("value", 0)
                
                # Velocity (change in value)
                velocity = current_value - previous_value
                velocities.append(velocity)
                
                # Acceleration (change in velocity)
                if i > 1:
                    acceleration = velocity - velocities[i-2]
                    accelerations.append(acceleration)
            
            # Calculate summary statistics
            avg_velocity = sum(velocities) / len(velocities) if velocities else 0
            avg_acceleration = sum(accelerations) / len(accelerations) if accelerations else 0
            
            # Determine trend direction
            if avg_velocity > 5:
                direction = "rising"
            elif avg_velocity < -5:
                direction = "falling"
            else:
                direction = "stable"
            
            return {
                "query": query,
                "velocity_analysis": {
                    "average_velocity": avg_velocity,
                    "average_acceleration": avg_acceleration,
                    "trend_direction": direction,
                    "momentum": "strong" if abs(avg_velocity) > 10 else "moderate",
                    "data_points": len(time_series)
                },
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error calculating trend velocity: {e}")
            return {"error": str(e), "query": query}
    
    def _calculate_trend_score(self, trend: Dict[str, Any]) -> float:
        """Calculate trend score based on various metrics"""
        
        score = 0.0
        
        # Volume/interest score
        if "value" in trend:
            score += min(trend["value"] / 100, 0.4)
        
        # Growth score
        if "growth" in trend:
            score += min(trend["growth"], 0.3)
        
        # Relevance score
        if "relevance" in trend:
            score += trend["relevance"] * 0.3
        
        return min(max(score, 0.0), 1.0)
    
    def _calculate_trend_momentum(self, trend: Dict[str, Any]) -> str:
        """Calculate trend momentum category"""
        
        if "growth" not in trend:
            return "unknown"
        
        growth = trend["growth"]
        
        if growth > 0.5:
            return "exploding"
        elif growth > 0.2:
            return "rising"
        elif growth > -0.2:
            return "stable"
        elif growth > -0.5:
            return "declining"
        else:
            return "crashing"
    
    def _calculate_relevance_score(self, related_query: Dict[str, Any], original_query: str) -> float:
        """Calculate relevance score for related queries"""
        
        # Simple relevance scoring based on query similarity
        original_words = set(original_query.lower().split())
        related_words = set(related_query.get("query", "").lower().split())
        
        if not original_words or not related_words:
            return 0.0
        
        intersection = len(original_words.intersection(related_words))
        union = len(original_words.union(related_words))
        
        return intersection / union if union > 0 else 0.0
    
    def _categorize_topic(self, topic: Dict[str, Any]) -> str:
        """Categorize a topic based on its content"""
        
        # Simple topic categorization
        topic_text = topic.get("topic_title", "").lower()
        
        if any(word in topic_text for word in ["tech", "software", "app", "digital"]):
            return "technology"
        elif any(word in topic_text for word in ["fashion", "style", "clothing"]):
            return "fashion"
        elif any(word in topic_text for word in ["food", "recipe", "cooking"]):
            return "food"
        elif any(word in topic_text for word in ["sport", "fitness", "exercise"]):
            return "sports"
        else:
            return "general"
    
    def _calculate_topic_relevance(self, topic: Dict[str, Any], query: str) -> float:
        """Calculate relevance score for related topics"""
        
        # Similar to query relevance but for topics
        query_words = set(query.lower().split())
        topic_words = set(topic.get("topic_title", "").lower().split())
        
        if not query_words or not topic_words:
            return 0.0
        
        intersection = len(query_words.intersection(topic_words))
        union = len(query_words.union(topic_words))
        
        return intersection / union if union > 0 else 0.0
    
    async def _analyze_time_series(self, time_series: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze time series data for patterns"""
        
        # Placeholder for time series analysis
        return {"status": "analysis_pending", "data_points": len(time_series)}
    
    async def _analyze_regional_data(self, regional_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze regional interest data"""
        
        # Placeholder for regional analysis
        return {"status": "analysis_pending", "regions": len(regional_data)}
    
    async def _analyze_trend_comparison_data(
        self,
        comparison_data: List[Dict[str, Any]],
        queries: List[str]
    ) -> Dict[str, Any]:
        """Analyze trend comparison data"""
        
        # Placeholder for comparison analysis
        return {"status": "analysis_pending", "queries": queries}
    
    async def _analyze_discovery_insights(
        self,
        trends: List[Dict[str, Any]],
        seed_keywords: List[str],
        categories: List[str]
    ) -> Dict[str, Any]:
        """Analyze trend discovery insights"""
        
        # Placeholder for discovery insights
        return {"status": "analysis_pending", "trends_count": len(trends)}
    
    async def _analyze_category_trends(
        self,
        trends: List[Dict[str, Any]],
        category: str
    ) -> Dict[str, Any]:
        """Analyze category-specific trends"""
        
        # Placeholder for category analysis
        return {"status": "analysis_pending", "category": category, "trends_count": len(trends)}
    
    async def close(self):
        """Clean up resources"""
        if self.mcp_client:
            await self.mcp_client.close()
        logger.info("✅ Google Trends Client closed")


# Convenience functions for external use
async def get_trending_searches(geo: str = "US", category: str = "all") -> Dict[str, Any]:
    """Convenience function to get trending searches"""
    
    client = GoogleTrendsClient()
    try:
        return await client.get_trending_searches(geo, category)
    finally:
        await client.close()


async def get_interest_over_time(
    query: str,
    geo: str = "US",
    time_range: str = "today 12-m"
) -> Dict[str, Any]:
    """Convenience function to get interest over time"""
    
    client = GoogleTrendsClient()
    try:
        return await client.get_interest_over_time(query, geo, time_range)
    finally:
        await client.close()


async def compare_trends(
    queries: List[str],
    geo: str = "US",
    time_range: str = "today 12-m"
) -> Dict[str, Any]:
    """Convenience function to compare trends"""
    
    client = GoogleTrendsClient()
    try:
        return await client.compare_trends(queries, geo, time_range)
    finally:
        await client.close()


async def discover_trending_topics(
    seed_keywords: List[str] = None,
    categories: List[str] = None,
    geo: str = "US"
) -> Dict[str, Any]:
    """Convenience function to discover trending topics"""
    
    client = GoogleTrendsClient()
    try:
        return await client.discover_trending_topics(seed_keywords, categories, geo)
    finally:
        await client.close()
