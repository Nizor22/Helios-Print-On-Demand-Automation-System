#!/usr/bin/env python3
"""
Zeitgeist Finder Module
Live trend analysis and discovery using MCP integration
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger
import httpx

from ..config import HeliosConfig
from ..services.google_cloud.vertex_ai_client import VertexAIClient


@dataclass
class TrendData:
    """Trend information with metadata"""
    keyword: str
    category: str
    source: str
    confidence_score: float
    engagement_metrics: Dict[str, Any]
    timestamp: float
    geo_location: str
    market_potential: str


@dataclass
class TrendAnalysis:
    """Comprehensive trend analysis"""
    primary_trend: TrendData
    related_trends: List[TrendData]
    market_opportunity: str
    design_inspiration: str
    target_audience: str
    seasonal_factors: List[str]


class ZeitgeistFinder:
    """AI-powered trend discovery and analysis"""
    
    def __init__(self, config: HeliosConfig):
        self.config = config
        self.vertex_ai = VertexAIClient(config)
        self.mcp_base_url = config.google_mcp_url.rstrip('/')
        self.trend_cache: Dict[str, TrendData] = {}
        self.cache_ttl = 1800  # 30 minutes cache
        
    async def discover_current_trends(self, categories: Optional[List[str]] = None, 
                                    geo_locations: Optional[List[str]] = None) -> TrendAnalysis:
        """Discover current trends using multiple sources"""
        
        if categories is None:
            categories = ["technology", "lifestyle", "health", "business", "entertainment"]
        
        if geo_locations is None:
            geo_locations = ["US", "GB", "CA"]
        
        logger.info(f"🔍 Discovering trends for categories: {categories}, locations: {geo_locations}")
        
        try:
            # Try MCP server first (most reliable)
            trends = await self._get_mcp_trends(categories, geo_locations)
            
            if trends:
                logger.info(f"✅ MCP trends found: {len(trends)} trends")
                return await self._analyze_trends_ai(trends, categories, geo_locations)
            
            # Fallback to AI-generated trends
            logger.warning("⚠️ MCP trends failed, using AI fallback")
            trends = await self._generate_ai_trends(categories, geo_locations)
            
            if trends:
                logger.info(f"✅ AI fallback trends generated: {len(trends)} trends")
                return await self._analyze_trends_ai(trends, categories, geo_locations)
            
            # Emergency fallback
            logger.error("❌ All trend discovery methods failed")
            return await self._emergency_fallback_trends()
            
        except Exception as e:
            logger.error(f"❌ Trend discovery failed: {e}")
            return await self._emergency_fallback_trends()
    
    async def _get_mcp_trends(self, categories: List[str], geo_locations: List[str]) -> List[TrendData]:
        """Get trends from MCP server"""
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Try multiple MCP endpoints
                endpoints = [
                    f"{self.mcp_base_url}/mcp/google-trends",
                    f"{self.mcp_base_url}/mcp/social-trends",
                    f"{self.mcp_base_url}/mcp/news"
                ]
                
                all_trends = []
                
                for endpoint in endpoints:
                    try:
                        response = await client.get(endpoint, params={
                            'categories': ','.join(categories),
                            'geo_locations': ','.join(geo_locations),
                            'limit': 5
                        })
                        
                        if response.status_code == 200:
                            data = response.json()
                            trends = self._parse_mcp_response(data, endpoint)
                            all_trends.extend(trends)
                            logger.info(f"✅ MCP endpoint {endpoint}: {len(trends)} trends")
                        else:
                            logger.warning(f"⚠️ MCP endpoint {endpoint} failed: {response.status_code}")
                            
                    except Exception as e:
                        logger.warning(f"⚠️ MCP endpoint {endpoint} error: {e}")
                        continue
                
                # Remove duplicates and return top trends
                unique_trends = self._deduplicate_trends(all_trends)
                return unique_trends[:10]  # Top 10 trends
                
        except Exception as e:
            logger.error(f"❌ MCP trends failed: {e}")
            return []
    
    def _parse_mcp_response(self, data: Dict, endpoint: str) -> List[TrendData]:
        """Parse MCP response into TrendData objects"""
        
        trends = []
        
        try:
            if endpoint.endswith('google-trends'):
                trends_data = data.get('trends', [])
                for trend in trends_data:
                    trend_obj = TrendData(
                        keyword=trend.get('keyword', ''),
                        category=trend.get('category', 'general'),
                        source='Google Trends',
                        confidence_score=float(trend.get('score', 0.8)),
                        engagement_metrics=trend.get('metrics', {}),
                        timestamp=time.time(),
                        geo_location=trend.get('location', 'US'),
                        market_potential=trend.get('potential', 'Good')
                    )
                    trends.append(trend_obj)
                    
            elif endpoint.endswith('social-trends'):
                trends_data = data.get('social_trends', [])
                for trend in trends_data:
                    trend_obj = TrendData(
                        keyword=trend.get('hashtag', trend.get('topic', '')),
                        category=trend.get('category', 'social'),
                        source='Social Media',
                        confidence_score=float(trend.get('engagement', 0.7)),
                        engagement_metrics={'mentions': trend.get('mentions', 0)},
                        timestamp=time.time(),
                        geo_location=trend.get('location', 'US'),
                        market_potential=trend.get('potential', 'Good')
                    )
                    trends.append(trend_obj)
                    
            elif endpoint.endswith('news'):
                trends_data = data.get('news_trends', [])
                for trend in trends_data:
                    trend_obj = TrendData(
                        keyword=trend.get('topic', ''),
                        category=trend.get('category', 'news'),
                        source='News Analysis',
                        confidence_score=float(trend.get('relevance', 0.8)),
                        engagement_metrics={'articles': trend.get('article_count', 0)},
                        timestamp=time.time(),
                        geo_location=trend.get('location', 'US'),
                        market_potential=trend.get('potential', 'Good')
                    )
                    trends.append(trend_obj)
                    
        except Exception as e:
            logger.warning(f"⚠️ Failed to parse MCP response from {endpoint}: {e}")
        
        return trends
    
    async def _generate_ai_trends(self, categories: List[str], geo_locations: List[str]) -> List[TrendData]:
        """Generate trends using AI when MCP is unavailable"""
        
        try:
            prompt = f"""
You are a trend analysis expert. Generate 5 current trending topics that would be excellent for print-on-demand products.

CATEGORIES: {', '.join(categories)}
GEO LOCATIONS: {', '.join(geo_locations)}
CURRENT TIME: {time.strftime('%Y-%m-%d %H:%M:%S')}

REQUIREMENTS:
1. Focus on topics with high visual appeal potential
2. Consider seasonal and cultural factors
3. Ensure topics are suitable for print-on-demand
4. Include diverse categories and interests
5. Provide realistic engagement scores

RESPONSE FORMAT (JSON only):
{{
    "trends": [
        {{
            "keyword": "trending topic",
            "category": "category name",
            "source": "AI Generated",
            "confidence_score": 0.85,
            "engagement_metrics": {{"estimated_mentions": 10000}},
            "geo_location": "US",
            "market_potential": "High - trending on social media"
        }}
    ]
}}

Generate trends that are currently popular and would make compelling designs.
"""
            
            response = await self.vertex_ai.generate_text(
                prompt=prompt,
                model="gemini-1.5-flash",
                max_tokens=1500,
                temperature=0.7
            )
            
            # Parse AI response
            if isinstance(response, dict):
                response_text = response.get('text', '')
            else:
                response_text = str(response)
            
            # Extract JSON
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in AI response")
            
            json_str = response_text[start_idx:end_idx]
            data = json.loads(json_str)
            
            trends = []
            for trend_data in data.get('trends', []):
                trend = TrendData(
                    keyword=trend_data['keyword'],
                    category=trend_data['category'],
                    source=trend_data['source'],
                    confidence_score=float(trend_data['confidence_score']),
                    engagement_metrics=trend_data['engagement_metrics'],
                    timestamp=time.time(),
                    geo_location=trend_data['geo_location'],
                    market_potential=trend_data['market_potential']
                )
                trends.append(trend)
            
            return trends
            
        except Exception as e:
            logger.error(f"❌ AI trend generation failed: {e}")
            return []
    
    async def _analyze_trends_ai(self, trends: List[TrendData], categories: List[str], 
                                 geo_locations: List[str]) -> TrendAnalysis:
        """Analyze trends using AI to find the best opportunity"""
        
        try:
            # Sort trends by confidence score
            sorted_trends = sorted(trends, key=lambda x: x.confidence_score, reverse=True)
            primary_trend = sorted_trends[0]
            related_trends = sorted_trends[1:4]  # Top 3 related trends
            
            # Create analysis prompt
            prompt = f"""
You are a market analysis expert for print-on-demand products. Analyze these trending topics and provide strategic insights.

PRIMARY TREND: {primary_trend.keyword}
CATEGORY: {primary_trend.category}
SOURCE: {primary_trend.source}
CONFIDENCE: {primary_trend.confidence_score}

RELATED TRENDS: {[t.keyword for t in related_trends]}
CATEGORIES: {categories}
LOCATIONS: {geo_locations}

ANALYSIS REQUIREMENTS:
1. Identify the market opportunity for the primary trend
2. Provide design inspiration ideas
3. Define the target audience
4. Consider seasonal factors
5. Assess print-on-demand suitability

RESPONSE FORMAT (JSON only):
{{
    "market_opportunity": "Detailed market opportunity description",
    "design_inspiration": "Creative design concepts and ideas",
    "target_audience": "Specific target demographic and interests",
    "seasonal_factors": ["factor1", "factor2", "factor3"],
    "print_on_demand_potential": "High/Medium/Low with reasoning"
}}

Provide strategic insights that will help create compelling, marketable products.
"""
            
            response = await self.vertex_ai.generate_text(
                prompt=prompt,
                model="gemini-1.5-flash",
                max_tokens=2000,
                temperature=0.6
            )
            
            # Parse analysis
            if isinstance(response, dict):
                analysis_text = response.get('text', '')
            else:
                analysis_text = str(response)
            
            # Extract JSON
            start_idx = analysis_text.find('{')
            end_idx = analysis_text.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in analysis response")
            
            json_str = analysis_text[start_idx:end_idx]
            analysis_data = json.loads(json_str)
            
            return TrendAnalysis(
                primary_trend=primary_trend,
                related_trends=related_trends,
                market_opportunity=analysis_data.get('market_opportunity', 'Good market opportunity'),
                design_inspiration=analysis_data.get('design_inspiration', 'Creative design potential'),
                target_audience=analysis_data.get('target_audience', 'General audience'),
                seasonal_factors=analysis_data.get('seasonal_factors', [])
            )
            
        except Exception as e:
            logger.error(f"❌ Trend analysis failed: {e}")
            # Return basic analysis
            return TrendAnalysis(
                primary_trend=trends[0] if trends else self._create_default_trend(),
                related_trends=trends[1:4] if len(trends) > 1 else [],
                market_opportunity="Market opportunity analysis unavailable",
                design_inspiration="Design inspiration analysis unavailable",
                target_audience="Target audience analysis unavailable",
                seasonal_factors=[]
            )
    
    def _deduplicate_trends(self, trends: List[TrendData]) -> List[TrendData]:
        """Remove duplicate trends based on keyword similarity"""
        
        seen_keywords = set()
        unique_trends = []
        
        for trend in trends:
            # Normalize keyword for comparison
            normalized = trend.keyword.lower().strip()
            
            if normalized not in seen_keywords:
                seen_keywords.add(normalized)
                unique_trends.append(trend)
        
        return unique_trends
    
    def _create_default_trend(self) -> TrendData:
        """Create a default trend when all else fails"""
        
        return TrendData(
            keyword="AI and Technology",
            category="technology",
            source="Fallback",
            confidence_score=0.5,
            engagement_metrics={"estimated_mentions": 5000},
            timestamp=time.time(),
            geo_location="US",
            market_potential="Medium - evergreen technology topic"
        )
    
    async def _emergency_fallback_trends(self) -> TrendAnalysis:
        """Emergency fallback when all trend discovery fails"""
        
        logger.warning("🚨 Using emergency fallback trends")
        
        fallback_trend = TrendData(
            keyword="Digital Innovation",
            category="technology",
            source="Emergency Fallback",
            confidence_score=0.3,
            engagement_metrics={"estimated_mentions": 1000},
            timestamp=time.time(),
            geo_location="US",
            market_potential="Low - emergency fallback"
        )
        
        return TrendAnalysis(
            primary_trend=fallback_trend,
            related_trends=[],
            market_opportunity="Limited - emergency fallback mode",
            design_inspiration="Basic technology-themed designs",
            target_audience="General technology enthusiasts",
            seasonal_factors=[]
        )
    
    async def get_trend_for_design(self, design_concept: str) -> TrendData:
        """Get a specific trend that would work well with a design concept"""
        
        try:
            # Discover current trends
            analysis = await self.discover_current_trends()
            
            # Find the best trend for the design concept
            best_trend = analysis.primary_trend
            
            # Use AI to validate the match
            prompt = f"""
Evaluate how well this trend matches the design concept:

TREND: {best_trend.keyword}
CATEGORY: {best_trend.category}
DESIGN CONCEPT: {design_concept}

Rate the compatibility from 0-1 and provide reasoning.
RESPONSE FORMAT (JSON only):
{{
    "compatibility_score": 0.85,
    "reasoning": "Explanation of why this trend works with the design",
    "design_suggestions": "Specific design ideas that combine the trend and concept"
}}
"""
            
            response = await self.vertex_ai.generate_text(
                prompt=prompt,
                model="gemini-1.5-flash",
                max_tokens=1000,
                temperature=0.4
            )
            
            # Parse compatibility analysis
            if isinstance(response, dict):
                analysis_text = response.get('text', '')
            else:
                analysis_text = str(response)
            
            start_idx = analysis_text.find('{')
            end_idx = analysis_text.rfind('}') + 1
            
            if start_idx != -1 and end_idx > 0:
                json_str = analysis_text[start_idx:end_idx]
                compatibility_data = json.loads(json_str)
                
                # Adjust confidence score based on compatibility
                compatibility_score = float(compatibility_data.get('compatibility_score', 0.7))
                best_trend.confidence_score *= compatibility_score
                
                logger.info(f"🎯 Trend-design compatibility: {compatibility_score:.2f}")
            
            return best_trend
            
        except Exception as e:
            logger.error(f"❌ Trend-design matching failed: {e}")
            # Return the primary trend without compatibility analysis
            analysis = await self.discover_current_trends()
            return analysis.primary_trend
