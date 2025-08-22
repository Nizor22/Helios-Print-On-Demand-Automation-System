"""
AI-Powered Trend Discovery Service
Uses Gemini/Vertex AI to intelligently discover, analyze, and predict trends
"""

import asyncio
import json
import time
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime, timedelta
from loguru import logger

from .google_cloud.vertex_ai_client import VertexAIClient
from ..config import HeliosConfig


@dataclass
class TrendAnalysis:
    """Trend analysis result from AI"""
    keyword: str
    category: str
    engagement_score: float
    market_potential: float
    competition_level: str
    product_opportunity: str
    target_audience: str
    confidence: float
    reasoning: str
    timestamp: datetime


@dataclass
class TrendDiscoveryRequest:
    """Request for AI trend discovery"""
    categories: List[str]
    geo_locations: List[str]
    time_range: str
    market_focus: str
    product_type: str
    max_trends: int = 20


@dataclass
class NotebookCell:
    """Notebook-style cell for trend analysis"""
    id: str
    type: str  # 'analysis', 'query', 'visualization'
    content: str
    outputs: List[Dict[str, Any]]
    execution_time: Optional[float] = None
    status: str = 'pending'  # 'pending', 'running', 'completed', 'error'


class TrendAnalysisNotebook:
    """
    Interactive notebook environment for trend analysis
    Inspired by Jupyter-style notebooks with persistent state
    """
    
    def __init__(self):
        self.cells: List[NotebookCell] = []
        self.persistent_scope: Dict[str, Any] = {}
        self.execution_history: List[Dict[str, Any]] = []
        self.cell_counter = 0
        
    def add_cell(self, content: str, cell_type: str = 'analysis') -> str:
        """Add a new cell to the notebook"""
        cell_id = f"cell_{self.cell_counter}"
        self.cell_counter += 1
        
        cell = NotebookCell(
            id=cell_id,
            type=cell_type,
            content=content,
            outputs=[],
            status='pending'
        )
        
        self.cells.append(cell)
        return cell_id
    
    async def execute_cell(self, cell_id: str, ai_service: 'AITrendDiscoveryService') -> Dict[str, Any]:
        """Execute a cell and return results"""
        cell = next((c for c in self.cells if c.id == cell_id), None)
        if not cell:
            return {"error": "Cell not found"}
        
        start_time = time.time()
        cell.status = 'running'
        
        try:
            # Execute based on cell type
            if cell.type == 'analysis':
                result = await self._execute_analysis_cell(cell, ai_service)
            elif cell.type == 'query':
                result = await self._execute_query_cell(cell, ai_service)
            elif cell.type == 'visualization':
                result = await self._execute_visualization_cell(cell, ai_service)
            else:
                result = {"error": f"Unknown cell type: {cell.type}"}
            
            # Update cell with results
            cell.outputs.append(result)
            cell.status = 'completed'
            cell.execution_time = time.time() - start_time
            
            # Store in execution history
            self.execution_history.append({
                "cell_id": cell_id,
                "timestamp": datetime.now(),
                "execution_time": cell.execution_time,
                "result": result
            })
            
            return result
            
        except Exception as e:
            error_result = {"error": str(e), "type": "error"}
            cell.outputs.append(error_result)
            cell.status = 'error'
            cell.execution_time = time.time() - start_time
            return error_result
    
    async def _execute_analysis_cell(self, cell: NotebookCell, ai_service: 'AITrendDiscoveryService') -> Dict[str, Any]:
        """Execute an analysis cell"""
        # Parse the content as a trend analysis request
        try:
            # Extract parameters from cell content (could be JSON or natural language)
            if cell.content.strip().startswith('{'):
                # JSON format
                params = json.loads(cell.content)
            else:
                # Natural language - use AI to parse
                params = await self._parse_natural_language_request(cell.content, ai_service)
            
            # Create trend discovery request
            request = TrendDiscoveryRequest(
                categories=params.get('categories', ['technology', 'lifestyle', 'health']),
                geo_locations=params.get('geo_locations', ['US']),
                time_range=params.get('time_range', '1d'),
                market_focus=params.get('market_focus', 'e-commerce'),
                product_type=params.get('product_type', 'print-on-demand'),
                max_trends=params.get('max_trends', 20)
            )
            
            # Execute AI trend discovery
            result = await ai_service.get_trend_recommendations(request)
            
            # Store results in persistent scope for other cells to use
            self.persistent_scope['last_trend_analysis'] = result
            self.persistent_scope['trends_count'] = len(result.get('top_trends', []))
            
            return {
                "type": "trend_analysis",
                "data": result,
                "summary": f"Analyzed {len(result.get('top_trends', []))} trends",
                "persistent_vars": ["last_trend_analysis", "trends_count"]
            }
            
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}", "type": "error"}
    
    async def _execute_query_cell(self, cell: NotebookCell, ai_service: 'AITrendDiscoveryService') -> Dict[str, Any]:
        """Execute a query cell"""
        try:
            # Use AI to answer the query using context from persistent scope
            context = f"Context: {json.dumps(self.persistent_scope, default=str)}\n\nQuery: {cell.content}"
            
            # Get AI response
            response = await ai_service._get_ai_analysis(context)
            
            if response:
                return {
                    "type": "query_response",
                    "data": response,
                    "query": cell.content,
                    "context_used": list(self.persistent_scope.keys())
                }
            else:
                return {"error": "Failed to get AI response", "type": "error"}
                
        except Exception as e:
            return {"error": f"Query failed: {str(e)}", "type": "error"}
    
    async def _execute_visualization_cell(self, cell: NotebookCell, ai_service: 'AITrendDiscoveryService') -> Dict[str, Any]:
        """Execute a visualization cell"""
        try:
            # Generate visualization data based on cell content and persistent scope
            if 'last_trend_analysis' in self.persistent_scope:
                trends_data = self.persistent_scope['last_trend_analysis']
                
                # Create visualization data
                viz_data = {
                    "trends_by_category": {},
                    "engagement_distribution": [],
                    "market_potential_ranking": []
                }
                
                for trend in trends_data.get('top_trends', []):
                    category = trend.category
                    if category not in viz_data["trends_by_category"]:
                        viz_data["trends_by_category"][category] = []
                    viz_data["trends_by_category"][category].append(trend.keyword)
                    
                    viz_data["engagement_distribution"].append({
                        "trend": trend.keyword,
                        "score": trend.engagement_score
                    })
                    
                    viz_data["market_potential_ranking"].append({
                        "trend": trend.keyword,
                        "potential": trend.market_potential
                    })
                
                # Sort by scores
                viz_data["engagement_distribution"].sort(key=lambda x: x["score"], reverse=True)
                viz_data["market_potential_ranking"].sort(key=lambda x: x["potential"], reverse=True)
                
                return {
                    "type": "visualization_data",
                    "data": viz_data,
                    "description": f"Generated visualization for {len(trends_data.get('top_trends', []))} trends",
                    "chart_types": ["bar_chart", "pie_chart", "ranking"]
                }
            else:
                return {"error": "No trend analysis data available. Run an analysis cell first.", "type": "error"}
                
        except Exception as e:
            return {"error": f"Visualization failed: {str(e)}", "type": "error"}
    
    async def _parse_natural_language_request(self, content: str, ai_service: 'AITrendDiscoveryService') -> Dict[str, Any]:
        """Parse natural language request into structured parameters"""
        prompt = f"""
        Parse this natural language request into JSON parameters for trend analysis:
        
        Request: {content}
        
        Return JSON with these fields:
        - categories: list of trend categories
        - geo_locations: list of geographic locations  
        - time_range: time period for analysis
        - market_focus: target market focus
        - product_type: type of products
        - max_trends: maximum number of trends to analyze
        
        JSON only, no other text.
        """
        
        response = await ai_service._get_ai_analysis(prompt)
        if response:
            try:
                # Extract JSON from response
                json_start = response.find('{')
                json_end = response.rfind('}') + 1
                if json_start != -1 and json_end != -1:
                    return json.loads(response[json_start:json_end])
            except:
                pass
        
        # Fallback to default parameters
        return {
            "categories": ["technology", "lifestyle", "health"],
            "geo_locations": ["US"],
            "time_range": "1d",
            "market_focus": "e-commerce",
            "product_type": "print-on-demand",
            "max_trends": 20
        }
    
    def get_notebook_summary(self) -> Dict[str, Any]:
        """Get summary of notebook execution"""
        completed_cells = [c for c in self.cells if c.status == 'completed']
        error_cells = [c for c in self.cells if c.status == 'error']
        
        return {
            "total_cells": len(self.cells),
            "completed_cells": len(completed_cells),
            "error_cells": len(error_cells),
            "pending_cells": len([c for c in self.cells if c.status == 'pending']),
            "total_execution_time": sum(c.execution_time or 0 for c in completed_cells),
            "persistent_variables": list(self.persistent_scope.keys()),
            "last_execution": self.execution_history[-1] if self.execution_history else None
        }
    
    def export_notebook(self) -> str:
        """Export notebook as executable Python code"""
        code_lines = [
            "# Helios Trend Analysis Notebook",
            "# Generated on:", datetime.now().isoformat(),
            "",
            "from helios.services.ai_trend_discovery import AITrendDiscoveryService",
            "from helios.config import load_config",
            "",
            "async def run_notebook():",
            "    config = load_config()",
            "    ai_service = AITrendDiscoveryService(config)",
            "    ",
        ]
        
        for cell in self.cells:
            if cell.status == 'completed':
                code_lines.append(f"    # Cell {cell.id}: {cell.type}")
                code_lines.append(f"    # {cell.content}")
                code_lines.append(f"    result_{cell.id} = await ai_service._execute_{cell.type}_cell(cell_{cell.id})")
                code_lines.append("    ")
        
        code_lines.extend([
            "    return {",
            "        'status': 'completed',",
            "        'cells_executed': len([c for c in self.cells if c.status == 'completed'])",
            "    }",
            "",
            "# Run the notebook",
            "# asyncio.run(run_notebook())"
        ])
        
        return "\n".join(code_lines)


class AITrendDiscoveryService:
    """
    AI-powered trend discovery using Gemini/Vertex AI
    Intelligently discovers and analyzes trends for product opportunities
    """

    def __init__(self, config: HeliosConfig):
        self.config = config
        self.vertex_ai_client = VertexAIClient(config)
        self.gemini_model = config.gemini_model or "gemini-1.5-flash"
        self.notebook = TrendAnalysisNotebook()

        # AI analysis prompts
        self.trend_discovery_prompt = """
        You are an expert trend analyst and market researcher. Your task is to discover and analyze current trends that present product opportunities.

        CONTEXT:
        - Target market: {market_focus}
        - Product type: {product_type}
        - Geographic focus: {geo_locations}
        - Categories: {categories}
        - Time range: {time_range}

        TASK:
        Analyze current trends and identify {max_trends} high-potential opportunities. For each trend:

        1. TREND ANALYSIS:
           - Keyword/phrase that represents the trend
           - Category classification
           - Current engagement level (1-10 scale)
           - Market potential (1-10 scale)
           - Competition level (low/medium/high)
           - Target audience description

        2. PRODUCT OPPORTUNITY:
           - Specific product idea based on the trend
           - Why this trend is valuable for products
           - Market timing assessment

        3. CONFIDENCE & REASONING:
           - Confidence level (1-10 scale)
           - Detailed reasoning for the analysis

        RESPONSE FORMAT:
        Return a JSON array with this structure:
        [
          {{
            "keyword": "trend keyword",
            "category": "category name",
            "engagement_score": 8.5,
            "market_potential": 9.0,
            "competition_level": "medium",
            "product_opportunity": "specific product idea",
            "target_audience": "target audience description",
            "confidence": 8.0,
            "reasoning": "detailed analysis reasoning"
          }}
        ]

        Focus on trends that are:
        - Currently gaining momentum
        - Have clear product applications
        - Show market demand
        - Have manageable competition
        - Align with current consumer behavior
        """

        self.trend_analysis_prompt = """
        You are an expert market analyst. Analyze this trend for product opportunities:

        TREND: {keyword}
        CATEGORY: {category}
        CURRENT CONTEXT: {context}

        Provide a detailed analysis including:
        1. Trend strength and momentum
        2. Market opportunity size
        3. Competition analysis
        4. Product application ideas
        5. Target audience insights
        6. Risk assessment
        7. Recommended next steps

        Format as structured analysis with clear sections.
        """

    async def create_trend_notebook(self, initial_analysis: bool = True) -> TrendAnalysisNotebook:
        """
        Create a new trend analysis notebook with optional initial analysis
        
        Args:
            initial_analysis: Whether to add an initial analysis cell
            
        Returns:
            Configured notebook instance
        """
        notebook = TrendAnalysisNotebook()
        
        if initial_analysis:
            # Add initial analysis cell
            initial_cell_content = """
            Analyze current trends in technology, lifestyle, and health categories.
            Focus on US market with e-commerce and print-on-demand opportunities.
            Generate 15 high-potential trends with detailed analysis.
            """
            notebook.add_cell(initial_cell_content, 'analysis')
        
        return notebook

    async def run_notebook_analysis(self, notebook: TrendAnalysisNotebook) -> Dict[str, Any]:
        """
        Execute all cells in a notebook and return comprehensive results
        
        Args:
            notebook: Notebook to execute
            
        Returns:
            Execution results and summary
        """
        logger.info(f"🧠 Executing notebook with {len(notebook.cells)} cells...")
        
        results = []
        for cell in notebook.cells:
            if cell.status == 'pending':
                logger.info(f"📝 Executing cell {cell.id}: {cell.type}")
                result = await notebook.execute_cell(cell.id, self)
                results.append({
                    "cell_id": cell.id,
                    "type": cell.type,
                    "result": result
                })
        
        summary = notebook.get_notebook_summary()
        
        return {
            "status": "completed",
            "cells_executed": len(results),
            "results": results,
            "summary": summary,
            "notebook_export": notebook.export_notebook()
        }

    async def discover_trends_ai(self, request: TrendDiscoveryRequest) -> List[TrendAnalysis]:
        """
        Use AI to intelligently discover and analyze trends

        Args:
            request: Trend discovery request with parameters

        Returns:
            List of AI-analyzed trends with detailed insights
        """
        try:
            logger.info("🧠 Starting AI-powered trend discovery...")

            # Format the prompt with request parameters
            formatted_prompt = self.trend_discovery_prompt.format(
                market_focus=request.market_focus,
                product_type=request.product_type,
                geo_locations=", ".join(request.geo_locations),
                categories=", ".join(request.categories),
                time_range=request.time_range,
                max_trends=request.max_trends
            )

            # Get AI analysis from Gemini/Vertex AI
            logger.info("🤖 Requesting AI trend analysis...")
            ai_response = await self._get_ai_analysis(formatted_prompt)

            if not ai_response:
                logger.warning("⚠️ AI analysis failed, using fallback trend discovery")
                return await self._fallback_trend_discovery(request)

            # Parse AI response
            trends = self._parse_ai_trends(ai_response)

            if trends:
                logger.info(f"✅ AI discovered {len(trends)} high-potential trends")
                return trends
            else:
                logger.warning("⚠️ AI response parsing failed, using fallback")
                return await self._fallback_trend_discovery(request)

        except Exception as e:
            logger.error(f"❌ AI trend discovery failed: {e}")
            return await self._fallback_trend_discovery(request)

    async def analyze_trend_deep(self, trend: str, category: str, context: str = "") -> Optional[TrendAnalysis]:
        """
        Perform deep AI analysis of a specific trend

        Args:
            trend: Trend keyword to analyze
            category: Trend category
            context: Additional context for analysis

        Returns:
            Detailed trend analysis or None if failed
        """
        try:
            logger.info(f"🔍 Performing deep AI analysis of trend: {trend}")

            # Format analysis prompt
            formatted_prompt = self.trend_analysis_prompt.format(
                keyword=trend,
                category=category,
                context=context or "General market context"
            )

            # Get AI analysis
            ai_response = await self._get_ai_analysis(formatted_prompt)

            if ai_response:
                # Parse the analysis and create TrendAnalysis object
                analysis = self._parse_single_trend_analysis(trend, category, ai_response)
                if analysis:
                    logger.info(f"✅ Deep analysis completed for: {trend}")
                    return analysis

            logger.warning(f"⚠️ Deep analysis failed for: {trend}")
            return None

        except Exception as e:
            logger.error(f"❌ Deep trend analysis failed: {e}")
            return None

    async def _get_ai_analysis(self, prompt: str) -> Optional[str]:
        """Get AI analysis from Gemini/Vertex AI"""
        try:
            # Try Gemini first (faster for text analysis)
            if self.gemini_model and "gemini" in self.gemini_model.lower():
                response = await self.vertex_ai_client.generate_text(
                    prompt=prompt,
                    model=self.gemini_model,
                    max_tokens=4000,
                    temperature=0.7
                )

                if isinstance(response, dict) and response.get("success"):
                    return response.get("text", "")
                elif isinstance(response, str):
                    return response

            # Fallback to other models
            response = await self.vertex_ai_client.generate_text(
                prompt=prompt,
                model="gemini-1.5-flash",
                max_tokens=4000,
                temperature=0.7
            )

            if isinstance(response, dict) and response.get("success"):
                return response.get("text", "")
            elif isinstance(response, str):
                return response

            logger.warning("⚠️ All AI models failed for text generation")
            return None

        except Exception as e:
            logger.error(f"❌ AI analysis request failed: {e}")
            return None

    def _parse_ai_trends(self, ai_response: str) -> List[TrendAnalysis]:
        """Parse AI response into TrendAnalysis objects"""
        try:
            # Try to extract JSON from the response
            json_start = ai_response.find('[')
            json_end = ai_response.rfind(']') + 1

            if json_start != -1 and json_end != -1:
                json_str = ai_response[json_start:json_end]
                trends_data = json.loads(json_str)

                trends = []
                for trend_data in trends_data:
                    try:
                        trend = TrendAnalysis(
                            keyword=trend_data.get("keyword", ""),
                            category=trend_data.get("category", "general"),
                            engagement_score=float(trend_data.get("engagement_score", 5.0)),
                            market_potential=float(trend_data.get("market_potential", 5.0)),
                            competition_level=trend_data.get("competition_level", "medium"),
                            product_opportunity=trend_data.get("product_opportunity", ""),
                            target_audience=trend_data.get("target_audience", ""),
                            confidence=float(trend_data.get("confidence", 5.0)),
                            reasoning=trend_data.get("reasoning", ""),
                            timestamp=datetime.now()
                        )
                        trends.append(trend)
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to parse trend data: {e}")
                        continue

                return trends

            logger.warning("⚠️ No valid JSON found in AI response")
            return []

        except Exception as e:
            logger.error(f"❌ Failed to parse AI trends: {e}")
            return []

    def _parse_single_trend_analysis(self, trend: str, category: str, ai_response: str) -> Optional[TrendAnalysis]:
        """Parse single trend analysis from AI response"""
        try:
            # Create a basic analysis from the AI response
            # In a full implementation, this would parse the structured analysis
            return TrendAnalysis(
                keyword=trend,
                category=category,
                engagement_score=7.5,  # Default score
                market_potential=7.0,  # Default score
                competition_level="medium",
                product_opportunity=f"Product based on {trend} trend",
                target_audience="General audience",
                confidence=7.0,
                reasoning=ai_response[:500] + "..." if len(ai_response) > 500 else ai_response,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"❌ Failed to parse single trend analysis: {e}")
            return None

    async def _fallback_trend_discovery(self, request: TrendDiscoveryRequest) -> List[TrendAnalysis]:
        """Fallback trend discovery when AI fails"""
        try:
            logger.info("🔄 Using fallback trend discovery...")

            # Generate some intelligent fallback trends based on request parameters
            fallback_trends = []

            # Create trends based on categories and market focus
            for category in request.categories:
                if category.lower() == "technology":
                    fallback_trends.extend([
                        "AI-powered productivity tools",
                        "Sustainable tech solutions",
                        "Remote work optimization",
                        "Digital wellness apps",
                        "Smart home automation"
                    ])
                elif category.lower() == "health":
                    fallback_trends.extend([
                        "Mental health awareness",
                        "Fitness technology",
                        "Nutrition optimization",
                        "Sleep improvement",
                        "Stress management tools"
                    ])
                elif category.lower() == "lifestyle":
                    fallback_trends.extend([
                        "Minimalist living",
                        "Sustainable fashion",
                        "Digital detox",
                        "Work-life balance",
                        "Personal development"
                    ])

            # Convert to TrendAnalysis objects
            trends = []
            for i, keyword in enumerate(fallback_trends[:request.max_trends]):
                trend = TrendAnalysis(
                    keyword=keyword,
                    category="fallback",
                    engagement_score=max(6.0, 9.0 - (i * 0.3)),
                    market_potential=max(6.0, 8.5 - (i * 0.3)),
                    competition_level="medium",
                    product_opportunity=f"Product leveraging {keyword}",
                    target_audience="General market",
                    confidence=6.0,
                    reasoning="Fallback trend based on category analysis",
                    timestamp=datetime.now()
                )
                trends.append(trend)

            logger.info(f"✅ Fallback discovery generated {len(trends)} trends")
            return trends

        except Exception as e:
            logger.error(f"❌ Fallback trend discovery failed: {e}")
            return []

    async def get_trend_recommendations(self, request: TrendDiscoveryRequest) -> Dict[str, Any]:
        """
        Get comprehensive trend recommendations with AI analysis

        Args:
            request: Trend discovery request

        Returns:
            Comprehensive trend recommendations
        """
        try:
            logger.info("🎯 Getting AI-powered trend recommendations...")

            # Discover trends using AI
            trends = await self.discover_trends_ai(request)

            if not trends:
                return {
                    "success": False,
                    "error": "No trends discovered",
                    "trends": []
                }

            # Sort trends by potential (engagement + market potential)
            sorted_trends = sorted(
                trends,
                key=lambda x: (x.engagement_score + x.market_potential) / 2,
                reverse=True
            )

            # Categorize trends
            categorized_trends = {}
            for trend in sorted_trends:
                if trend.category not in categorized_trends:
                    categorized_trends[trend.category] = []
                categorized_trends[trend.category].append(trend)

            # Generate summary insights
            total_trends = len(trends)
            avg_engagement = sum(t.engagement_score for t in trends) / total_trends
            avg_potential = sum(t.market_potential for t in trends) / total_trends

            recommendations = {
                "success": True,
                "summary": {
                    "total_trends": total_trends,
                    "average_engagement": round(avg_engagement, 2),
                    "average_market_potential": round(avg_potential, 2),
                    "top_categories": list(categorized_trends.keys())[:5]
                },
                "top_trends": sorted_trends[:10],
                "categorized_trends": categorized_trends,
                "recommendations": {
                    "high_potential": [t for t in trends if t.market_potential >= 8.0],
                    "low_competition": [t for t in trends if t.competition_level == "low"],
                    "emerging_trends": [t for t in trends if t.engagement_score >= 8.0]
                }
            }

            logger.info(f"✅ Generated recommendations for {total_trends} trends")
            return recommendations

        except Exception as e:
            logger.error(f"❌ Failed to get trend recommendations: {e}")
            return {
                "success": False,
                "error": str(e),
                "trends": []
            }
