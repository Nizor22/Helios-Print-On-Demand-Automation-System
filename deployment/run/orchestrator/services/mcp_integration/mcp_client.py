"""
Google MCP (Model Context Protocol) Client for Helios Autonomous Store
Provides integration with MCP server for trend discovery and analysis
"""

import os
import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import httpx
from urllib.parse import urljoin

from loguru import logger


@dataclass
class MCPToolConfig:
    """Configuration for MCP tools"""
    name: str
    endpoint: str
    description: str
    parameters: Dict[str, Any]
    rate_limit: Optional[int] = None


class GoogleMCPClient:
    """
    Google MCP client for Helios Autonomous Store
    Integrates with MCP server for trend discovery and analysis
    """
    
    def __init__(self, server_url: str = None, auth_token: str = None):
        self.server_url = server_url or os.getenv("GOOGLE_MCP_URL", "http://localhost:8080")
        self.auth_token = auth_token or os.getenv("GOOGLE_MCP_AUTH_TOKEN")
        self.client = None
        self.initialized = False
        
        # Configure MCP tools
        self.tools = {
            "google_trends": MCPToolConfig(
                name="google_trends",
                endpoint="/mcp/google-trends",
                description="Google Trends data analysis",
                parameters={"query": "string", "geo": "string", "time_range": "string"}
            ),
            "social_media": MCPToolConfig(
                name="social_media",
                endpoint="/mcp/social-trends", 
                description="Social media trend scanning",
                parameters={"platforms": "list", "keywords": "list", "time_range": "string"}
            ),
            "news_analysis": MCPToolConfig(
                name="news_analysis",
                endpoint="/mcp/news",
                description="News sentiment analysis",
                parameters={"query": "string", "sources": "list", "time_range": "string"}
            ),
            "competitor_intel": MCPToolConfig(
                name="competitor_intel",
                endpoint="/mcp/competitor-intel",
                description="Competitor intelligence gathering",
                parameters={"competitors": "list", "analysis_type": "string", "time_range": "string"}
            ),
            "trend_discovery": MCPToolConfig(
                name="trend_discovery",
                endpoint="/mcp/discover",
                description="Comprehensive trend discovery",
                parameters={"keywords": "list", "geo": "string", "time_range": "string", "categories": "list"}
            )
        }
        
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize the MCP client"""
        try:
            # Create HTTP client
            headers = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"
            
            self.client = httpx.AsyncClient(
                base_url=self.server_url,
                headers=headers,
                timeout=30.0
            )
            
            self.initialized = True
            logger.info(f"✅ Google MCP client initialized for server: {self.server_url}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize MCP client: {e}")
            raise
    
    async def _make_request(
        self,
        endpoint: str,
        method: str = "POST",
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make a request to the MCP server"""
        try:
            if method.upper() == "GET":
                response = await self.client.get(endpoint, params=params)
            else:
                response = await self.client.post(endpoint, json=data, params=params)
            
            response.raise_for_status()
            return response.json()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ MCP server error: {e.response.status_code} - {e.response.text}")
            return {
                "status": "error",
                "error": f"HTTP {e.response.status_code}: {e.response.text}",
                "timestamp": time.time()
            }
        except httpx.RequestError as e:
            logger.error(f"❌ MCP request failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
        except Exception as e:
            logger.error(f"❌ Unexpected error in MCP request: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def get_google_trends(
        self,
        query: str,
        geo: str = "US",
        time_range: str = "today 12-m",
        category: str = "all"
    ) -> Dict[str, Any]:
        """
        Get Google Trends data using MCP
        
        Args:
            query: Search query
            geo: Geographic location
            time_range: Time range for analysis
            category: Category filter
            
        Returns:
            Google Trends data and analysis
        """
        try:
            tool_config = self.tools["google_trends"]
            
            data = {
                "query": query,
                "geo": geo,
                "time_range": time_range,
                "category": category
            }
            
            result = await self._make_request(tool_config.endpoint, data=data)
            
            if result.get("status") == "success":
                logger.info(f"✅ Google Trends data retrieved for: {query}")
            else:
                logger.warning(f"⚠️ Google Trends request failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Google Trends failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def scan_social_media(
        self,
        keywords: List[str],
        platforms: List[str] = None,
        time_range: str = "24h",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Scan social media for trends using MCP
        
        Args:
            keywords: Keywords to search for
            platforms: Social media platforms to scan
            time_range: Time range for scanning
            limit: Maximum number of results
            
        Returns:
            Social media trend data
        """
        try:
            tool_config = self.tools["social_media"]
            
            if platforms is None:
                platforms = ["twitter", "reddit", "youtube"]
            
            data = {
                "keywords": keywords,
                "platforms": platforms,
                "time_range": time_range,
                "limit": limit
            }
            
            result = await self._make_request(tool_config.endpoint, data=data)
            
            if result.get("status") == "success":
                logger.info(f"✅ Social media scan completed for {len(keywords)} keywords")
            else:
                logger.warning(f"⚠️ Social media scan failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Social media scan failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def analyze_news(
        self,
        query: str,
        sources: List[str] = None,
        time_range: str = "7d",
        sentiment_analysis: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze news using MCP
        
        Args:
            query: News search query
            sources: News sources to analyze
            time_range: Time range for news
            sentiment_analysis: Whether to perform sentiment analysis
            
        Returns:
            News analysis results
        """
        try:
            tool_config = self.tools["news_analysis"]
            
            if sources is None:
                sources = ["Google News", "RSS feeds", "News API"]
            
            data = {
                "query": query,
                "sources": sources,
                "time_range": time_range,
                "sentiment_analysis": sentiment_analysis
            }
            
            result = await self._make_request(tool_config.endpoint, data=data)
            
            if result.get("status") == "success":
                logger.info(f"✅ News analysis completed for: {query}")
            else:
                logger.warning(f"⚠️ News analysis failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ News analysis failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def get_competitor_intelligence(
        self,
        competitors: List[str],
        analysis_type: str = "comprehensive",
        time_range: str = "30d"
    ) -> Dict[str, Any]:
        """
        Get competitor intelligence using MCP
        
        Args:
            competitors: List of competitor names
            analysis_type: Type of analysis to perform
            time_range: Time range for analysis
            
        Returns:
            Competitor intelligence data
        """
        try:
            tool_config = self.tools["competitor_intel"]
            
            data = {
                "competitors": competitors,
                "analysis_type": analysis_type,
                "time_range": time_range
            }
            
            result = await self._make_request(tool_config.endpoint, data=data)
            
            if result.get("status") == "success":
                logger.info(f"✅ Competitor intelligence retrieved for {len(competitors)} competitors")
            else:
                logger.warning(f"⚠️ Competitor intelligence failed: {result.get('error')}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Competitor intelligence failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def discover_trends(
        self,
        seed_keywords: List[str] = None,
        categories: List[str] = None,
        geo: str = "US",
        time_range: str = "today 12-m"
    ) -> Dict[str, Any]:
        """
        Discover trends using multiple MCP tools
        
        Args:
            seed_keywords: Initial keywords for trend discovery
            categories: Product categories to focus on
            geo: Geographic location
            time_range: Time range for analysis
            
        Returns:
            Comprehensive trend discovery results
        """
        try:
            logger.info("🔍 Starting comprehensive trend discovery...")
            
            # Initialize results
            trends_data = {
                "status": "success",
                "discovery_time": time.time(),
                "trends": [],
                "sources": {},
                "analysis": {}
            }
            
            # 1. Google Trends Analysis
            if seed_keywords:
                for keyword in seed_keywords[:5]:  # Limit to 5 keywords
                    trends_result = await self.get_google_trends(
                        query=keyword,
                        geo=geo,
                        time_range=time_range
                    )
                    
                    if trends_result.get("status") == "success":
                        trends_data["sources"]["google_trends"] = trends_result
                        
                        # Extract trend information
                        if "data" in trends_result:
                            for trend in trends_result["data"].get("trends", []):
                                trend_info = {
                                    "keyword": keyword,
                                    "trend_name": trend.get("name", keyword),
                                    "volume": trend.get("volume", 0),
                                    "growth_rate": trend.get("growth", 0),
                                    "source": "google_trends",
                                    "geo": geo,
                                    "time_range": time_range
                                }
                                trends_data["trends"].append(trend_info)
            
            # 2. Social Media Scanning
            if seed_keywords:
                social_result = await self.scan_social_media(
                    keywords=seed_keywords,
                    time_range=time_range,
                    limit=50
                )
                
                if social_result.get("status") == "success":
                    trends_data["sources"]["social_media"] = social_result
                    
                    # Extract social media trends
                    if "data" in social_result:
                        for platform, data in social_result["data"].items():
                            for trend in data.get("trends", []):
                                trend_info = {
                                    "keyword": trend.get("keyword", "unknown"),
                                    "trend_name": trend.get("name", trend.get("keyword", "unknown")),
                                    "volume": trend.get("mentions", 0),
                                    "engagement": trend.get("engagement", 0),
                                    "sentiment": trend.get("sentiment", "neutral"),
                                    "source": f"social_{platform}",
                                    "geo": geo,
                                    "time_range": time_range
                                }
                                trends_data["trends"].append(trend_info)
            
            # 3. News Analysis
            if seed_keywords:
                news_result = await self.analyze_news(
                    query=" OR ".join(seed_keywords[:3]),  # Limit to 3 keywords
                    time_range=time_range,
                    sentiment_analysis=True
                )
                
                if news_result.get("status") == "success":
                    trends_data["sources"]["news"] = news_result
                    
                    # Extract news-based trends
                    if "data" in news_result:
                        for article in news_result["data"].get("articles", []):
                            trend_info = {
                                "keyword": article.get("keywords", ["news"])[0],
                                "trend_name": article.get("title", "News Trend"),
                                "volume": 1,  # Single article
                                "sentiment": article.get("sentiment", "neutral"),
                                "source": "news",
                                "geo": geo,
                                "time_range": time_range,
                                "url": article.get("url"),
                                "published": article.get("published")
                            }
                            trends_data["trends"].append(trend_info)
            
            # 4. Competitor Intelligence
            if categories:
                competitor_result = await self.get_competitor_intelligence(
                    competitors=categories,  # Use categories as competitor proxies
                    analysis_type="market_trends",
                    time_range=time_range
                )
                
                if competitor_result.get("status") == "success":
                    trends_data["sources"]["competitor_intel"] = competitor_result
            
            # Analyze and rank trends
            trends_data["analysis"] = await self._analyze_trends_data(trends_data["trends"])
            
            logger.info(f"✅ Trend discovery completed: {len(trends_data['trends'])} trends found")
            return trends_data
            
        except Exception as e:
            logger.error(f"❌ Trend discovery failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def _analyze_trends_data(self, trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze and rank trend data"""
        try:
            if not trends:
                return {"total_trends": 0, "ranked_trends": []}
            
            # Group trends by keyword
            keyword_groups = {}
            for trend in trends:
                keyword = trend.get("keyword", "unknown")
                if keyword not in keyword_groups:
                    keyword_groups[keyword] = []
                keyword_groups[keyword].append(trend)
            
            # Calculate composite scores
            ranked_trends = []
            for keyword, trend_list in keyword_groups.items():
                # Calculate volume score
                total_volume = sum(t.get("volume", 0) for t in trend_list)
                
                # Calculate growth score
                total_growth = sum(t.get("growth_rate", 0) for t in trend_list)
                
                # Calculate engagement score (for social media)
                total_engagement = sum(t.get("engagement", 0) for t in trend_list)
                
                # Calculate sentiment score
                sentiment_scores = {"positive": 1, "neutral": 0.5, "negative": 0}
                avg_sentiment = sum(sentiment_scores.get(t.get("sentiment", "neutral"), 0.5) for t in trend_list) / len(trend_list)
                
                # Calculate source diversity
                sources = set(t.get("source", "unknown") for t in trend_list)
                source_diversity = len(sources) / 4  # Normalize to 0-1
                
                # Composite score (0-10 scale)
                composite_score = (
                    (total_volume / 100) * 0.3 +  # 30% weight for volume
                    (total_growth / 100) * 0.25 +  # 25% weight for growth
                    (total_engagement / 100) * 0.2 +  # 20% weight for engagement
                    avg_sentiment * 0.15 +  # 15% weight for sentiment
                    source_diversity * 0.1  # 10% weight for source diversity
                ) * 10  # Scale to 0-10
                
                ranked_trends.append({
                    "keyword": keyword,
                    "composite_score": round(composite_score, 2),
                    "total_volume": total_volume,
                    "total_growth": total_growth,
                    "total_engagement": total_engagement,
                    "avg_sentiment": round(avg_sentiment, 2),
                    "source_diversity": round(source_diversity, 2),
                    "sources": list(sources),
                    "trend_count": len(trend_list),
                    "trends": trend_list
                })
            
            # Sort by composite score
            ranked_trends.sort(key=lambda x: x["composite_score"], reverse=True)
            
            return {
                "total_trends": len(trends),
                "unique_keywords": len(keyword_groups),
                "ranked_trends": ranked_trends,
                "top_trends": ranked_trends[:10] if len(ranked_trends) > 10 else ranked_trends
            }
            
        except Exception as e:
            logger.error(f"❌ Trend analysis failed: {e}")
            return {"error": str(e)}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check MCP server health"""
        try:
            response = await self.client.get("/health")
            response.raise_for_status()
            
            return {
                "status": "healthy",
                "server_url": self.server_url,
                "response_time": response.elapsed.total_seconds(),
                "timestamp": time.time()
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "server_url": self.server_url,
                "error": str(e),
                "timestamp": time.time()
            }
    
    async def get_tool_info(self, tool_name: str = None) -> Dict[str, Any]:
        """Get information about MCP tools"""
        if tool_name:
            if tool_name not in self.tools:
                return {"error": f"Unknown tool: {tool_name}"}
            return {
                "tool": tool_name,
                **self.tools[tool_name].__dict__
            }
        
        return {
            "available_tools": list(self.tools.keys()),
            "tools": {name: tool.__dict__ for name, tool in self.tools.items()},
            "server_url": self.server_url
        }
    
    async def close(self):
        """Close the MCP client"""
        if self.client:
            await self.client.aclose()
            logger.info("✅ MCP client closed")

    async def test_connection(self) -> Dict[str, Any]:
        """Test connection to MCP server and get server info"""
        try:
            # Try to get server info or health check
            result = await self._make_request("/api/health", method="GET")
            if result.get("status") == "error":
                # Try alternative health endpoint
                result = await self._make_request("/health", method="GET")
            
            return {
                "status": "success",
                "server_url": self.server_url,
                "connected": True,
                "server_info": result
            }
        except Exception as e:
            return {
                "status": "error",
                "server_url": self.server_url,
                "connected": False,
                "error": str(e)
            }
    
    async def get_real_trends(self, geo: str = "US", limit: int = 20) -> Dict[str, Any]:
        """
        Get real trending data from MCP server
        
        Args:
            geo: Geographic location
            limit: Maximum number of trends
            
        Returns:
            Real trending data with metadata
        """
        try:
            # Try the trend discovery endpoint first
            data = {
                "keywords": ["trending", "viral", "popular"],
                "geo": geo,
                "time_range": "now 1-d",
                "categories": ["all"]
            }
            
            result = await self._make_request("/api/discover", data=data)
            
            if result.get("status") == "success":
                logger.info(f"✅ Real trends fetched from MCP server: {len(result.get('data', []))} trends")
                return result
            else:
                # Fallback to trends endpoint
                logger.info("⚠️ Discovery endpoint failed, trying trends endpoint...")
                trends_result = await self._make_request("/api/trends", data={"geo": geo, "limit": limit})
                return trends_result
                
        except Exception as e:
            logger.error(f"❌ Failed to get real trends from MCP: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }


# Convenience functions
async def discover_trends_mcp(
    seed_keywords: List[str] = None,
    categories: List[str] = None
) -> Dict[str, Any]:
    """Convenience function for trend discovery"""
    client = GoogleMCPClient()
    try:
        return await client.discover_trends(seed_keywords, categories)
    finally:
        await client.close()


async def get_google_trends_mcp(query: str) -> Dict[str, Any]:
    """Convenience function for Google Trends data"""
    client = GoogleMCPClient()
    try:
        return await client.get_google_trends(query)
    finally:
        await client.close()


async def scan_social_media_mcp(keywords: List[str]) -> Dict[str, Any]:
    """Convenience function for social media scanning"""
    client = GoogleMCPClient()
    try:
        return await client.scan_social_media(keywords)
    finally:
        await client.close()
