"""
Autonomous Trend Discoverer Agent

Discovers trends through multi-source analysis without seed words or hardcoded data.
Uses real-time data gathering and AI analysis for trend discovery.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from helios.services.real_time_data_gatherer import RealTimeDataGatherer
from helios.services.google_cloud.vertex_ai_client import VertexAIClient

logger = logging.getLogger(__name__)


class AutonomousTrendDiscoverer:
    """Autonomously discovers trends without seed words or hardcoded data"""
    
    def __init__(self):
        self.data_gatherer = RealTimeDataGatherer()
        self.ai_analyzer = VertexAIClient()
        
    async def discover_trends(self, time_range: str = "30 days", regions: str = "US", categories: str = "all") -> List[Dict[str, Any]]:
        """Discover trends through multi-source analysis"""
        try:
            logger.info(f"Starting autonomous trend discovery for {categories} in {regions} over {time_range}")
            
            # Phase 1: Gather data from all sources
            async with self.data_gatherer as gatherer:
                all_data = await gatherer.gather_all_sources()
            
            # Phase 2: AI analysis to identify genuine trends
            trends = await self.analyze_cross_source_signals(all_data, time_range, regions, categories)
            
            logger.info(f"Discovered {len(trends)} trends through autonomous analysis")
            return trends
            
        except Exception as e:
            logger.error(f"Autonomous trend discovery failed: {e}")
            raise RuntimeError(f"Trend discovery completely failed: {e}")
    
    async def analyze_cross_source_signals(self, data_sources: Dict[str, Any], time_range: str, regions: str, categories: str) -> List[Dict[str, Any]]:
        """AI analysis to find genuine trends across multiple data sources"""
        try:
            # Prepare analysis prompt
            analysis_prompt = f"""
            AUTONOMOUS TREND ANALYSIS:
            
            Analyze these multi-source data streams to identify genuine emerging trends.
            Time Range: {time_range}
            Regions: {regions}
            Categories: {categories}
            
            Data Sources Available:
            - Social Media: {list(data_sources.get('social', {}).keys())}
            - Search Trends: {data_sources.get('search', {}).get('source', 'N/A')}
            - News: {data_sources.get('news', {}).get('source', 'N/A')}
            - Cultural: {data_sources.get('cultural', {}).get('source', 'N/A')}
            
            ANALYSIS REQUIREMENTS:
            1. Look for signals that appear across multiple sources with growing momentum
            2. Filter out noise and identify commercially viable trends
            3. Focus on trends with psychological appeal and emotional drivers
            4. Identify trends suitable for print-on-demand products
            5. Score trends based on cross-source validation
            
            OUTPUT FORMAT:
            For each discovered trend, provide:
            - Trend Name: [specific trend name in quotes]
            - Cross-Source Validation: [which sources confirm this trend]
            - Momentum Score: [1-10 based on growth across sources]
            - Commercial Viability: [1-10 for print-on-demand]
            - Emotional Driver: [primary psychological motivation]
            - Target Audience: [demographic and psychographic profile]
            - Product Opportunities: [specific product types]
            
            IMPORTANT: Only identify trends that appear in multiple data sources.
            Do not use any seed words or assumptions - only real discovered trends.
            """
            
            # Execute AI analysis
            response = await self.ai_analyzer.generate_text(
                prompt=analysis_prompt,
                model_type="gemini_flash",
                max_tokens=8192,
                temperature=0.7
            )
            
            # Parse AI response to extract trends
            trends = self._parse_trend_analysis(response.text if hasattr(response, 'text') else str(response))
            
            return trends
            
        except Exception as e:
            logger.error(f"Cross-source signal analysis failed: {e}")
            raise RuntimeError(f"Trend analysis failed: {e}")
    
    def _parse_trend_analysis(self, ai_response: str) -> List[Dict[str, Any]]:
        """Parse AI response to extract structured trend data"""
        trends = []
        
        # Split response into sections
        sections = ai_response.split('**')
        
        for section in sections:
            if 'TREND' in section.upper() and ':' in section:
                trend_data = self._extract_trend_from_section(section)
                if trend_data:
                    trends.append(trend_data)
        
        return trends
    
    def _extract_trend_from_section(self, section: str) -> Optional[Dict[str, Any]]:
        """Extract trend data from a single section"""
        try:
            lines = section.split('\n')
            trend_data = {}
            
            for line in lines:
                line = line.strip()
                
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if 'trend name' in key:
                        # Extract trend name from quotes
                        if '"' in value:
                            trend_name = value.split('"')[1]
                            trend_data['name'] = trend_name
                    elif 'cross-source validation' in key:
                        trend_data['validation'] = value
                    elif 'momentum score' in key:
                        try:
                            trend_data['momentum'] = float(value)
                        except:
                            trend_data['momentum'] = 5.0
                    elif 'commercial viability' in key:
                        try:
                            trend_data['viability'] = float(value)
                        except:
                            trend_data['viability'] = 5.0
                    elif 'emotional driver' in key:
                        trend_data['emotion'] = value
                    elif 'target audience' in key:
                        trend_data['audience'] = value
                    elif 'product opportunities' in key:
                        trend_data['products'] = value
            
            # Only return if we have a valid trend name
            if 'name' in trend_data and trend_data['name']:
                return trend_data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to extract trend from section: {e}")
            return None
    
    async def get_trend_summary(self, trends: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate summary of discovered trends"""
        try:
            if not trends:
                return {"summary": "No trends discovered", "count": 0}
            
            # Calculate aggregate metrics
            total_trends = len(trends)
            avg_momentum = sum(t.get('momentum', 5.0) for t in trends) / total_trends
            avg_viability = sum(t.get('viability', 5.0) for t in trends) / total_trends
            
            # Group by emotional driver
            emotion_groups = {}
            for trend in trends:
                emotion = trend.get('emotion', 'unknown')
                if emotion not in emotion_groups:
                    emotion_groups[emotion] = []
                emotion_groups[emotion].append(trend['name'])
            
            return {
                "summary": f"Discovered {total_trends} trends through autonomous analysis",
                "count": total_trends,
                "average_momentum": round(avg_momentum, 2),
                "average_viability": round(avg_viability, 2),
                "emotional_distribution": emotion_groups,
                "timestamp": datetime.utcnow().isoformat(),
                "method": "autonomous_multi_source_analysis"
            }
            
        except Exception as e:
            logger.error(f"Failed to generate trend summary: {e}")
            return {"summary": "Summary generation failed", "error": str(e)}
