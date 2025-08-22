"""
Competitor Intelligence Service for Helios Autonomous Store
Integrates with Google MCP to analyze competitor data and market positioning
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

from google.cloud import aiplatform
from google.cloud import firestore
from google.cloud import storage

from ..google_cloud.vertex_ai_client import VertexAIClient
from ..google_cloud.firestore_client import FirestoreClient
from ..google_cloud.storage_client import CloudStorageClient
from .mcp_client import GoogleMCPClient

logger = logging.getLogger(__name__)


class CompetitorIntelligenceService:
    """
    Service for analyzing competitor intelligence using Google MCP and Vertex AI
    """
    
    def __init__(self, project_id: str, location: str = "us-central1"):
        self.project_id = project_id
        self.location = location
        
        # Initialize clients
        self.vertex_ai_client = VertexAIClient(project_id, location)
        self.firestore_client = FirestoreClient(project_id)
        self.storage_client = CloudStorageClient(project_id, "trend-analysis-data")
        self.mcp_client = GoogleMCPClient()
        
        # Initialize Vertex AI
        aiplatform.init(project=project_id, location=location)
        
    async def analyze_competitor_landscape(
        self, 
        product_category: str,
        target_market: str = "global",
        analysis_depth: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Analyze competitor landscape for a given product category
        
        Args:
            product_category: The product category to analyze
            target_market: Target market (global, US, EU, etc.)
            analysis_depth: Analysis depth (quick, standard, comprehensive)
            
        Returns:
            Dictionary containing competitor analysis results
        """
        try:
            logger.info(f"Starting competitor analysis for {product_category} in {target_market}")
            
            # Get competitor data from MCP
            competitor_data = await self._gather_competitor_data(product_category, target_market)
            
            # Analyze with Vertex AI
            analysis_result = await self._analyze_with_ai(competitor_data, analysis_depth)
            
            # Store results
            await self._store_analysis_results(product_category, analysis_result)
            
            return {
                "status": "success",
                "product_category": product_category,
                "target_market": target_market,
                "analysis_depth": analysis_depth,
                "timestamp": datetime.utcnow().isoformat(),
                "competitor_count": len(competitor_data.get("competitors", [])),
                "analysis_summary": analysis_result.get("summary", {}),
                "recommendations": analysis_result.get("recommendations", []),
                "risk_assessment": analysis_result.get("risk_assessment", {}),
                "opportunity_score": analysis_result.get("opportunity_score", 0.0)
            }
            
        except Exception as e:
            logger.error(f"Error in competitor analysis: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _gather_competitor_data(
        self, 
        product_category: str, 
        target_market: str
    ) -> Dict[str, Any]:
        """Gather competitor data from various MCP sources"""
        
        competitor_data = {
            "product_category": product_category,
            "target_market": target_market,
            "competitors": [],
            "market_trends": [],
            "pricing_data": [],
            "social_sentiment": []
        }
        
        try:
            # Get Google Trends data for competitors
            trends_data = await self.mcp_client.get_google_trends(
                query=product_category,
                geo=target_market,
                time_range="12m"
            )
            
            if trends_data.get("status") == "success":
                competitor_data["market_trends"] = trends_data.get("data", [])
            
            # Get social media mentions and sentiment
            social_data = await self.mcp_client.scan_social_media(
                keywords=[product_category],
                platforms=["twitter", "reddit", "youtube"],
                time_range="7d"
            )
            
            if social_data.get("status") == "success":
                competitor_data["social_sentiment"] = social_data.get("data", [])
            
            # Get news analysis for market context
            news_data = await self.mcp_client.analyze_news(
                query=product_category,
                time_range="30d"
            )
            
            if news_data.get("status") == "success":
                competitor_data["news_context"] = news_data.get("data", [])
            
            # Identify potential competitors from trends and social data
            competitors = await self._identify_competitors(
                product_category, 
                competitor_data["market_trends"],
                competitor_data["social_sentiment"]
            )
            
            competitor_data["competitors"] = competitors
            
            return competitor_data
            
        except Exception as e:
            logger.error(f"Error gathering competitor data: {str(e)}")
            return competitor_data
    
    async def _identify_competitors(
        self, 
        product_category: str, 
        trends_data: List[Dict], 
        social_data: List[Dict]
    ) -> List[Dict]:
        """Identify potential competitors from trends and social data"""
        
        competitors = []
        
        try:
            # Ensure data is in the correct format
            if isinstance(trends_data, str):
                trends_data = []
            elif not isinstance(trends_data, list):
                trends_data = []
                
            if isinstance(social_data, str):
                social_data = []
            elif not isinstance(social_data, list):
                social_data = []
            
            # Extract brand mentions from social data
            brand_mentions = set()
            for post in social_data:
                if not isinstance(post, dict):
                    continue
                # Extract potential brand names (simplified)
                text = post.get("text", "").lower()
                # This is a simplified approach - in production, use NLP for better extraction
                if any(word in text for word in ["brand", "company", "store", "shop"]):
                    # Extract potential brand names
                    pass
            
            # Analyze trends data for competitor insights
            for trend in trends_data:
                if not isinstance(trend, dict):
                    continue
                if trend.get("type") == "rising":
                    competitors.append({
                        "name": trend.get("query", "Unknown"),
                        "trend_score": trend.get("value", 0),
                        "growth_rate": trend.get("growth_rate", 0),
                        "source": "google_trends",
                        "last_updated": datetime.utcnow().isoformat()
                    })
            
            # Remove duplicates and sort by trend score
            unique_competitors = {}
            for comp in competitors:
                name = comp["name"].lower()
                if name not in unique_competitors or comp["trend_score"] > unique_competitors[name]["trend_score"]:
                    unique_competitors[name] = comp
            
            return sorted(
                list(unique_competitors.values()), 
                key=lambda x: x["trend_score"], 
                reverse=True
            )[:20]  # Top 20 competitors
            
        except Exception as e:
            logger.error(f"Error identifying competitors: {str(e)}")
            return competitors
    
    async def _analyze_with_ai(
        self, 
        competitor_data: Dict[str, Any], 
        analysis_depth: str
    ) -> Dict[str, Any]:
        """Analyze competitor data using Vertex AI Gemini"""
        
        try:
            # Prepare prompt based on analysis depth
            if analysis_depth == "quick":
                prompt = self._create_quick_analysis_prompt(competitor_data)
            elif analysis_depth == "comprehensive":
                prompt = self._create_comprehensive_analysis_prompt(competitor_data)
            else:
                prompt = self._create_standard_analysis_prompt(competitor_data)
            
            # Get AI analysis
            response = await self.vertex_ai_client.generate_text(
                prompt=prompt,
                model="gemini-1.5-pro",
                max_tokens=4096,
                temperature=0.3
            )
            
            # Parse AI response
            analysis_result = self._parse_ai_response(response)
            
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error in AI analysis: {str(e)}")
            return {
                "summary": {"error": str(e)},
                "recommendations": [],
                "risk_assessment": {},
                "opportunity_score": 0.0
            }
    
    def _create_quick_analysis_prompt(self, competitor_data: Dict[str, Any]) -> str:
        """Create prompt for quick competitor analysis"""
        
        return f"""
        Analyze the competitor landscape for {competitor_data['product_category']} in {competitor_data['target_market']}.
        
        Competitor data:
        - Number of competitors: {len(competitor_data.get('competitors', []))}
        - Market trends: {len(competitor_data.get('market_trends', []))} trends identified
        - Social sentiment: {len(competitor_data.get('social_sentiment', []))} social posts analyzed
        
        Provide a quick analysis with:
        1. Key competitors (top 5)
        2. Market opportunity score (0-10)
        3. Main risks
        4. Quick recommendations
        
        Format as JSON with keys: summary, opportunity_score, risks, recommendations
        """
    
    def _create_standard_analysis_prompt(self, competitor_data: Dict[str, Any]) -> str:
        """Create prompt for standard competitor analysis"""
        
        return f"""
        Conduct a standard competitor analysis for {competitor_data['product_category']} in {competitor_data['target_market']}.
        
        Available data:
        - Competitors: {json.dumps(competitor_data.get('competitors', [])[:10], indent=2)}
        - Market trends: {json.dumps(competitor_data.get('market_trends', [])[:5], indent=2)}
        - Social sentiment: {len(competitor_data.get('social_sentiment', []))} posts
        
        Provide analysis with:
        1. Market overview
        2. Competitor positioning matrix
        3. Opportunity assessment
        4. Risk analysis
        5. Strategic recommendations
        
        Format as JSON with keys: summary, competitor_matrix, opportunity_assessment, risk_analysis, recommendations
        """
    
    def _create_comprehensive_analysis_prompt(self, competitor_data: Dict[str, Any]) -> str:
        """Create prompt for comprehensive competitor analysis"""
        
        return f"""
        Conduct a comprehensive competitor intelligence analysis for {competitor_data['product_category']} in {competitor_data['target_market']}.
        
        Full dataset:
        - Competitors: {json.dumps(competitor_data.get('competitors', []), indent=2)}
        - Market trends: {json.dumps(competitor_data.get('market_trends', []), indent=2)}
        - Social sentiment: {json.dumps(competitor_data.get('social_sentiment', []), indent=2)}
        - News context: {json.dumps(competitor_data.get('news_context', []), indent=2)}
        
        Provide comprehensive analysis including:
        1. Executive summary
        2. Market landscape analysis
        3. Competitor profiling and positioning
        4. SWOT analysis for top competitors
        5. Market opportunity assessment with scoring
        6. Risk assessment and mitigation strategies
        7. Strategic recommendations with priority levels
        8. Implementation roadmap
        
        Format as JSON with keys: executive_summary, market_landscape, competitor_profiles, swot_analysis, opportunity_assessment, risk_assessment, strategic_recommendations, implementation_roadmap
        """
    
    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response into structured format"""
        
        try:
            # Try to extract JSON from response
            if "```json" in ai_response:
                json_start = ai_response.find("```json") + 7
                json_end = ai_response.find("```", json_start)
                json_str = ai_response[json_start:json_end].strip()
                return json.loads(json_str)
            elif "{" in ai_response and "}" in ai_response:
                # Try to find JSON in the response
                start = ai_response.find("{")
                end = ai_response.rfind("}") + 1
                json_str = ai_response[start:end]
                return json.loads(json_str)
            else:
                # Fallback: create structured response from text
                return {
                    "summary": {"analysis": ai_response},
                    "recommendations": [],
                    "risk_assessment": {},
                    "opportunity_score": 0.0
                }
                
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {str(e)}")
            return {
                "summary": {"raw_response": ai_response},
                "recommendations": [],
                "risk_assessment": {},
                "opportunity_score": 0.0
            }
    
    async def _store_analysis_results(
        self, 
        product_category: str, 
        analysis_result: Dict[str, Any]
    ) -> None:
        """Store analysis results in Firestore"""
        
        try:
            collection_name = "competitor_analyses"
            document_id = f"{product_category}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
            
            document_data = {
                "product_category": product_category,
                "timestamp": datetime.utcnow(),
                "analysis_result": analysis_result,
                "status": "completed"
            }
            
            await self.firestore_client.create_document(collection_name, document_data, document_id)
            logger.info(f"Stored competitor analysis results for {product_category}")
            
        except Exception as e:
            logger.error(f"Error storing analysis results: {str(e)}")
    
    async def get_competitor_insights(
        self, 
        product_category: str, 
        days_back: int = 30
    ) -> List[Dict[str, Any]]:
        """Get historical competitor insights from Firestore"""
        
        try:
            collection_name = "competitor_analyses"
            
            # Query for recent analyses
            query = self.firestore_client.db.collection(collection_name).where(
                "product_category", "==", product_category
            ).where(
                "timestamp", ">=", datetime.utcnow() - timedelta(days=days_back)
            ).order_by("timestamp", direction="descending")
            
            docs = query.stream()
            
            insights = []
            for doc in docs:
                doc_data = doc.to_dict()
                insights.append({
                    "id": doc.id,
                    "timestamp": doc_data.get("timestamp"),
                    "opportunity_score": doc_data.get("analysis_result", {}).get("opportunity_score", 0.0),
                    "summary": doc_data.get("analysis_result", {}).get("summary", {})
                })
            
            return insights
            
        except Exception as e:
            logger.error(f"Error getting competitor insights: {str(e)}")
            return []
    
    async def analyze_competitor_trends(
        self,
        competitors: List[str],
        categories: List[str],
        time_window: str = "30d"
    ) -> Dict[str, Any]:
        """Analyze competitor trends and identify trending products"""
        try:
            logger.info(f"Analyzing competitor trends for {len(competitors)} competitors in categories: {categories}")
            
            trending_products = []
            
            # Analyze each competitor
            for competitor in competitors:
                try:
                    # Get competitor landscape analysis
                    landscape = await self.analyze_competitor_landscape(
                        product_category=", ".join(categories),
                        target_market="global",
                        analysis_depth="quick"
                    )
                    
                    if landscape.get("status") == "success":
                        # Extract trending insights
                        analysis_summary = landscape.get("analysis_summary", {})
                        
                        # Ensure analysis_summary is a dictionary
                        if isinstance(analysis_summary, str):
                            analysis_summary = {"analysis": analysis_summary}
                        elif not isinstance(analysis_summary, dict):
                            analysis_summary = {}
                        
                        # Create trending product entry
                        trending_product = {
                            "product_name": f"{competitor} Trending Product",
                            "competitor": competitor,
                            "trend_score": landscape.get("opportunity_score", 0) / 10.0,  # Normalize to 0-1
                            "sales_velocity": "medium",  # Placeholder
                            "category": categories[0] if categories else "general",
                            "market_position": analysis_summary.get("position", "unknown"),
                            "strengths": analysis_summary.get("strengths", []),
                            "weaknesses": analysis_summary.get("weaknesses", []),
                            "last_updated": datetime.utcnow().isoformat()
                        }
                        
                        trending_products.append(trending_product)
                        
                except Exception as e:
                    logger.warning(f"Failed to analyze competitor {competitor}: {e}")
                    continue
            
            # Sort by trend score
            trending_products.sort(key=lambda x: x.get("trend_score", 0), reverse=True)
            
            return {
                "status": "success",
                "trending_products": trending_products,
                "competitors_analyzed": len(competitors),
                "categories": categories,
                "time_window": time_window,
                "total_products": len(trending_products),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing competitor trends: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "trending_products": [],
                "competitors_analyzed": 0,
                "categories": categories,
                "time_window": time_window
            }

    async def monitor_competitor_changes(
        self, 
        product_category: str,
        alert_threshold: float = 0.3
    ) -> Dict[str, Any]:
        """Monitor for significant competitor changes and alert if needed"""
        
        try:
            # Get recent insights
            recent_insights = await self.get_competitor_insights(product_category, days_back=7)
            
            if len(recent_insights) < 2:
                return {"status": "insufficient_data", "message": "Need at least 2 data points for comparison"}
            
            # Compare latest with previous
            latest = recent_insights[0]
            previous = recent_insights[1]
            
            latest_score = latest.get("opportunity_score", 0.0)
            previous_score = previous.get("opportunity_score", 0.0)
            
            change = latest_score - previous_score
            change_percentage = (change / previous_score * 100) if previous_score > 0 else 0
            
            alert_triggered = abs(change) >= alert_threshold
            
            return {
                "status": "monitoring_complete",
                "product_category": product_category,
                "latest_score": latest_score,
                "previous_score": previous_score,
                "change": change,
                "change_percentage": change_percentage,
                "alert_threshold": alert_threshold,
                "alert_triggered": alert_triggered,
                "recommendation": "Investigate changes" if alert_triggered else "Continue monitoring"
            }
            
        except Exception as e:
            logger.error(f"Error monitoring competitor changes: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def close(self):
        """Clean up resources and close connections"""
        try:
            logger.info("🧹 Cleaning up CompetitorIntelligenceService...")
            
            # Close Vertex AI client
            if hasattr(self, 'vertex_ai_client') and hasattr(self.vertex_ai_client, 'close'):
                await self.vertex_ai_client.close()
            
            # Close Firestore client
            if hasattr(self, 'firestore_client') and hasattr(self.firestore_client, 'close'):
                await self.firestore_client.close()
            
            # Close Storage client
            if hasattr(self, 'storage_client') and hasattr(self.storage_client, 'close'):
                await self.storage_client.close()
            
            # Close MCP client
            if hasattr(self, 'mcp_client') and hasattr(self.mcp_client, 'close'):
                await self.mcp_client.close()
            
            logger.info("✅ CompetitorIntelligenceService cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Error during CompetitorIntelligenceService cleanup: {str(e)}")


# Example usage
async def main():
    """Example usage of the CompetitorIntelligenceService"""
    
    service = CompetitorIntelligenceService("helios-autonomous-store")
    
    # Quick analysis
    result = await service.analyze_competitor_landscape(
        product_category="sustainable fashion",
        target_market="US",
        analysis_depth="quick"
    )
    
    print(f"Analysis result: {result}")
    
    # Monitor changes
    changes = await service.monitor_competitor_changes("sustainable fashion")
    print(f"Changes detected: {changes}")


if __name__ == "__main__":
    asyncio.run(main())
