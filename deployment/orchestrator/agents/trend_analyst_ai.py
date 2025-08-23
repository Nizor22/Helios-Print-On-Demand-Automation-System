"""
AI-Powered Trend Analysis Agent
Uses Google Vertex AI, Gemini, and MCP to intelligently analyze trends
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from loguru import logger

from ..config import HeliosConfig
from ..services.mcp_integration.mcp_client import GoogleMCPClient
from ..services.google_cloud.vertex_ai_client import VertexAIClient


@dataclass
class TrendAnalysis:
    """AI-powered trend analysis result"""
    trend_name: str
    opportunity_score: float  # 0-10 scale
    commercial_viability: str  # "high", "medium", "low"
    market_timing: str  # "immediate", "soon", "wait", "missed"
    target_demographics: List[str]
    product_categories: List[str]
    competitive_landscape: str
    viral_potential: float  # 0-1 scale
    risk_assessment: str
    reasoning: str
    confidence: float  # 0-1 scale
    recommended_action: str  # "proceed", "investigate", "monitor", "reject"


class TrendAnalystAI:
    """
    Specialized AI agent that uses Google's advanced AI services to analyze trends
    Much more intelligent than algorithmic scoring
    """
    
    def __init__(self, config: HeliosConfig):
        self.config = config
        
        # Initialize Google AI services
        self.vertex_ai = VertexAIClient(
            project_id=config.google_cloud_project,
            location=config.google_cloud_location
        )
        
        self.mcp_client = GoogleMCPClient(
            server_url=config.google_mcp_url,
            auth_token=config.google_mcp_auth_token
        )
        
        # AI analysis prompts
        self.analysis_prompt = self._create_analysis_prompt()
        
        logger.info("🧠 AI Trend Analyst initialized with Google Vertex AI and MCP")
    
    async def analyze_trends(self, raw_trends: List[Dict[str, Any]], max_trends: int = 10) -> List[TrendAnalysis]:
        """
        Use AI to intelligently analyze trends instead of algorithmic scoring
        """
        logger.info(f"🧠 AI analyzing {len(raw_trends)} trends with Google Vertex AI...")
        
        analyses = []
        
        for trend_data in raw_trends[:max_trends]:
            try:
                analysis = await self._analyze_single_trend(trend_data)
                if analysis and analysis.opportunity_score >= 5.0:  # AI-determined threshold
                    analyses.append(analysis)
                    logger.info(f"✅ AI approved: {analysis.trend_name} (Score: {analysis.opportunity_score:.1f})")
                else:
                    logger.debug(f"❌ AI rejected: {trend_data.get('trend_name', 'Unknown')} - Low AI score")
                    
            except Exception as e:
                logger.error(f"❌ AI analysis failed for {trend_data.get('trend_name', 'Unknown')}: {e}")
                continue
        
        # Sort by AI-determined opportunity score
        analyses.sort(key=lambda x: x.opportunity_score, reverse=True)
        
        logger.info(f"🧠 AI analysis complete: {len(analyses)} high-potential trends identified")
        return analyses
    
    async def _analyze_single_trend(self, trend_data: Dict[str, Any]) -> Optional[TrendAnalysis]:
        """Analyze a single trend using AI"""
        trend_name = trend_data.get('trend_name', 'Unknown')
        
        # Gather additional context using MCP
        enhanced_context = await self._gather_trend_context(trend_data)
        
        # Create AI analysis prompt
        prompt = self._create_trend_analysis_prompt(trend_data, enhanced_context)
        
        # Get AI analysis from Vertex AI
        ai_response = await self.vertex_ai.generate_text(
            prompt=prompt,
            model_name=self.config.gemini_pro_model,
            max_tokens=1000,
            temperature=0.3  # Lower temperature for more consistent analysis
        )
        
        if not ai_response:
            logger.warning(f"No AI response for trend: {trend_name}")
            return None
        
        # Parse AI response
        analysis = self._parse_ai_analysis(ai_response, trend_name)
        return analysis
    
    async def _gather_trend_context(self, trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """Gather additional context about the trend using MCP"""
        context = {}
        
        try:
            keywords = trend_data.get('keywords', [])
            if keywords:
                # Get market intelligence
                market_data = await self.mcp_client.get_competitor_intelligence(
                    keywords=keywords[:3],
                    competitors=["etsy", "amazon", "redbubble"]
                )
                context['market_intelligence'] = market_data
                
                # Get social sentiment
                social_data = await self.mcp_client.scan_social_media(
                    keywords=keywords[:3],
                    platforms=["twitter", "reddit"],
                    timeframe="24h"
                )
                context['social_sentiment'] = social_data
                
                # Get search trends
                search_data = await self.mcp_client.get_google_trends(
                    query=" ".join(keywords[:2]),
                    geo="US",
                    timeframe="now 7-d"
                )
                context['search_trends'] = search_data
                
        except Exception as e:
            logger.warning(f"Failed to gather context: {e}")
            
        return context
    
    def _create_analysis_prompt(self) -> str:
        """Create the main analysis prompt template"""
        return """
You are an expert trend analyst and e-commerce strategist specializing in print-on-demand products.

Your task is to analyze trends and determine their commercial viability for creating profitable products on platforms like Etsy, Printify, and Amazon.

Consider these factors:
1. **Market Timing**: Is this trend at the right stage for entry?
2. **Commercial Viability**: Can this translate into sellable products?
3. **Competition**: How saturated is this market?
4. **Viral Potential**: Will this trend continue growing?
5. **Target Demographics**: Who would buy products based on this trend?
6. **Product Categories**: What types of products would work?
7. **Risk Assessment**: What are the potential downsides?

Provide a comprehensive analysis with specific, actionable insights.
"""
    
    def _create_trend_analysis_prompt(self, trend_data: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Create specific analysis prompt for a trend"""
        trend_name = trend_data.get('trend_name', 'Unknown')
        keywords = trend_data.get('keywords', [])
        source = trend_data.get('source', 'unknown')
        
        context_summary = ""
        if context.get('market_intelligence'):
            context_summary += f"Market Intelligence: {json.dumps(context['market_intelligence'], indent=2)}\n"
        if context.get('social_sentiment'):
            context_summary += f"Social Data: {json.dumps(context['social_sentiment'], indent=2)}\n"
        if context.get('search_trends'):
            context_summary += f"Search Trends: {json.dumps(context['search_trends'], indent=2)}\n"
        
        return f"""
{self.analysis_prompt}

**TREND TO ANALYZE:**
- Name: {trend_name}
- Keywords: {', '.join(keywords)}
- Source: {source}
- Raw Data: {json.dumps(trend_data, indent=2)}

**ADDITIONAL CONTEXT:**
{context_summary}

**REQUIRED OUTPUT FORMAT (JSON):**
{{
    "opportunity_score": 8.5,
    "commercial_viability": "high",
    "market_timing": "immediate",
    "target_demographics": ["millennials", "gen-z", "fitness enthusiasts"],
    "product_categories": ["apparel", "accessories", "home-decor"],
    "competitive_landscape": "moderate competition with room for differentiation",
    "viral_potential": 0.85,
    "risk_assessment": "low risk - established trend with clear demand",
    "reasoning": "This trend shows strong commercial potential because...",
    "confidence": 0.90,
    "recommended_action": "proceed"
}}

Analyze this trend and provide your expert assessment:
"""
    
    def _parse_ai_analysis(self, ai_response: str, trend_name: str) -> Optional[TrendAnalysis]:
        """Parse AI response into TrendAnalysis object"""
        try:
            # Try to extract JSON from AI response
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = ai_response[json_start:json_end]
                analysis_data = json.loads(json_str)
                
                return TrendAnalysis(
                    trend_name=trend_name,
                    opportunity_score=float(analysis_data.get('opportunity_score', 5.0)),
                    commercial_viability=analysis_data.get('commercial_viability', 'medium'),
                    market_timing=analysis_data.get('market_timing', 'soon'),
                    target_demographics=analysis_data.get('target_demographics', []),
                    product_categories=analysis_data.get('product_categories', []),
                    competitive_landscape=analysis_data.get('competitive_landscape', 'unknown'),
                    viral_potential=float(analysis_data.get('viral_potential', 0.5)),
                    risk_assessment=analysis_data.get('risk_assessment', 'medium risk'),
                    reasoning=analysis_data.get('reasoning', 'AI analysis completed'),
                    confidence=float(analysis_data.get('confidence', 0.7)),
                    recommended_action=analysis_data.get('recommended_action', 'investigate')
                )
            else:
                # Fallback: create analysis from text response
                return self._create_fallback_analysis(ai_response, trend_name)
                
        except Exception as e:
            logger.error(f"Failed to parse AI analysis: {e}")
            return self._create_fallback_analysis(ai_response, trend_name)
    
    def _create_fallback_analysis(self, ai_response: str, trend_name: str) -> TrendAnalysis:
        """Create fallback analysis when JSON parsing fails"""
        # Simple scoring based on positive/negative words in AI response
        positive_words = ['good', 'excellent', 'high potential', 'profitable', 'trending', 'popular', 'growing']
        negative_words = ['poor', 'low', 'declining', 'saturated', 'risky', 'difficult']
        
        text_lower = ai_response.lower()
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        # Calculate basic score
        score = 5.0 + (positive_count * 0.5) - (negative_count * 0.7)
        score = max(0, min(10, score))
        
        return TrendAnalysis(
            trend_name=trend_name,
            opportunity_score=score,
            commercial_viability="medium" if score >= 5.0 else "low",
            market_timing="soon",
            target_demographics=["general"],
            product_categories=["apparel"],
            competitive_landscape="unknown",
            viral_potential=0.6,
            risk_assessment="medium risk",
            reasoning=ai_response[:500] + "..." if len(ai_response) > 500 else ai_response,
            confidence=0.6,
            recommended_action="investigate" if score >= 5.0 else "monitor"
        )


async def create_trend_analyst_ai(config: HeliosConfig) -> TrendAnalystAI:
    """Factory function to create AI trend analyst"""
    return TrendAnalystAI(config)
