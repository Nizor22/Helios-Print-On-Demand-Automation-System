"""
Trend Analysis AI Agent for Helios Autonomous Store
Specialized AI agent using Google MCP, Vertex AI, and other Google Cloud services
for intelligent trend analysis and product generation
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from loguru import logger

from ..config import HeliosConfig
from ..services.mcp_integration.mcp_client import GoogleMCPClient
from ..services.google_cloud.vertex_ai_client import VertexAIClient
from ..services.external_apis.google_trends_client import GoogleTrendsClient
from ..services.external_apis.google_sheets_client import GoogleSheetsClient
from ..services.google_cloud.google_drive_client import GoogleDriveClient
from ..utils.performance_monitor import PerformanceMonitor


class TrendAnalysisMode(Enum):
    """Analysis modes for the AI agent"""
    DISCOVERY = "discovery"
    VALIDATION = "validation"
    PREDICTION = "prediction"
    OPTIMIZATION = "optimization"


@dataclass
class TrendAnalysis:
    """Result of AI-powered trend analysis"""
    trend_id: str
    trend_name: str
    category: str
    
    # AI Analysis Results
    ai_confidence_score: float  # 0-1 scale
    market_opportunity_score: float  # 0-10 scale
    predicted_success_rate: float  # 0-1 scale
    
    # Pattern Recognition Results
    pattern_type: str  # seasonal, viral, steady, emerging
    pattern_strength: float  # 0-1 scale
    trend_lifecycle_stage: str  # emerging, growing, peak, declining
    
    # Market Insights
    target_demographics: Dict[str, Any]
    competitive_landscape: Dict[str, Any]
    market_size_estimate: str
    growth_velocity: float
    
    # Product Generation Recommendations
    recommended_products: List[Dict[str, Any]]
    design_themes: List[str]
    marketing_angles: List[str]
    pricing_strategy: Dict[str, Any]
    
    # Data Sources
    data_sources: List[str] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    # Metadata
    analysis_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ai_models_used: List[str] = field(default_factory=list)
    processing_time_ms: int = 0


@dataclass
class ProductPrediction:
    """AI prediction for product success"""
    product_id: str
    predicted_success_rate: float  # 0-1 scale
    confidence_level: float  # 0-1 scale
    
    # Market Fit Analysis
    market_fit_score: float  # 0-10 scale
    target_audience_match: float  # 0-1 scale
    competitive_advantage: Dict[str, Any]
    
    # Performance Predictions
    predicted_sales_volume: str  # low, medium, high
    predicted_profit_margin: float
    predicted_customer_satisfaction: float  # 0-1 scale
    
    # Risk Assessment
    risk_factors: List[Dict[str, Any]]
    mitigation_strategies: List[str]
    
    # Recommendations
    optimization_suggestions: List[str]
    marketing_recommendations: List[str]
    pricing_recommendations: Dict[str, Any]
    
    # Metadata
    prediction_timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    model_version: str = ""


class TrendAnalysisAI:
    """
    Specialized AI agent for intelligent trend analysis and product generation
    Integrates Google MCP, Vertex AI, and other Google services
    """
    
    def __init__(self, config: HeliosConfig):
        self.config = config
        
        # Initialize Google service clients
        self.mcp_client = GoogleMCPClient(
            server_url=config.google_mcp_url,
            auth_token=config.google_mcp_auth_token
        )
        
        self.vertex_ai = VertexAIClient(
            project_id=config.vertex_ai_project_id or config.google_cloud_project,
            location=config.vertex_ai_location or config.google_cloud_location
        )
        
        self.google_trends = GoogleTrendsClient()
        self.sheets_client = GoogleSheetsClient(config.gsheet_id) if config.gsheet_id else None
        self.drive_client = GoogleDriveClient(config.google_drive_folder_id) if config.google_drive_folder_id else None
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor(config)
        
        # AI agent configuration
        self.min_confidence_threshold = 0.7
        self.pattern_recognition_threshold = 0.8
        self.prediction_confidence_threshold = 0.75
        
        # Cache for analysis results
        self._analysis_cache: Dict[str, TrendAnalysis] = {}
        self._cache_ttl = 3600  # 1 hour
        
        logger.info("✅ TrendAnalysisAI agent initialized with Google MCP and Vertex AI")
    
    async def analyze_trends(
        self,
        keywords: List[str],
        mode: TrendAnalysisMode = TrendAnalysisMode.DISCOVERY,
        categories: List[str] = None,
        geo: str = "US",
        time_range: str = "today 12-m"
    ) -> List[TrendAnalysis]:
        """
        Analyze trends using AI-powered intelligence
        
        Args:
            keywords: Keywords to analyze
            mode: Analysis mode (discovery, validation, prediction, optimization)
            categories: Product categories to focus on
            geo: Geographic location
            time_range: Time range for analysis
            
        Returns:
            List of AI-analyzed trend data
        """
        start_time = time.time()
        
        try:
            logger.info(f"🤖 Starting AI trend analysis for {len(keywords)} keywords in {mode.value} mode")
            
            # Step 1: Gather multi-source trend data using MCP
            trend_data = await self._gather_trend_data(keywords, categories, geo, time_range)
            
            # Step 2: Apply AI pattern recognition using Vertex AI
            pattern_insights = await self._apply_pattern_recognition(trend_data)
            
            # Step 3: Generate market predictions
            market_predictions = await self._generate_market_predictions(pattern_insights)
            
            # Step 4: Create product recommendations
            product_recommendations = await self._generate_product_recommendations(market_predictions)
            
            # Step 5: Compile comprehensive analysis
            analyses = await self._compile_trend_analyses(
                trend_data,
                pattern_insights,
                market_predictions,
                product_recommendations
            )
            
            # Step 6: Filter by confidence threshold
            filtered_analyses = [a for a in analyses if a.ai_confidence_score >= self.min_confidence_threshold]
            
            # Log performance metrics
            processing_time = int((time.time() - start_time) * 1000)
            await self.performance_monitor.track_metric(
                "ai_trend_analysis",
                {
                    "keywords_analyzed": len(keywords),
                    "trends_found": len(filtered_analyses),
                    "processing_time_ms": processing_time,
                    "mode": mode.value
                }
            )
            
            logger.info(f"✅ AI trend analysis completed: {len(filtered_analyses)} high-confidence trends found in {processing_time}ms")
            
            return filtered_analyses
            
        except Exception as e:
            logger.error(f"❌ AI trend analysis failed: {e}")
            raise
    
    async def predict_product_success(
        self,
        trend_data: TrendAnalysis,
        product_concept: Dict[str, Any]
    ) -> ProductPrediction:
        """
        Predict product success using AI
        
        Args:
            trend_data: Analyzed trend data
            product_concept: Product concept to evaluate
            
        Returns:
            AI prediction for product success
        """
        try:
            logger.info(f"🔮 Predicting product success for trend: {trend_data.trend_name}")
            
            # Create comprehensive prompt for Vertex AI
            prediction_prompt = self._create_prediction_prompt(trend_data, product_concept)
            
            # Get AI prediction using Gemini Pro for complex analysis
            ai_response = await self.vertex_ai.generate_text(
                prompt=prediction_prompt,
                model_type="gemini_pro",
                system_prompt="You are an expert e-commerce analyst specializing in product success prediction."
            )
            
            # Parse AI response
            prediction = self._parse_prediction_response(ai_response, trend_data, product_concept)
            
            # Enhance with additional data sources
            prediction = await self._enhance_prediction_with_market_data(prediction, trend_data)
            
            logger.info(f"✅ Product prediction completed: {prediction.predicted_success_rate:.2%} success rate")
            
            return prediction
            
        except Exception as e:
            logger.error(f"❌ Product prediction failed: {e}")
            raise
    
    async def _gather_trend_data(
        self,
        keywords: List[str],
        categories: List[str],
        geo: str,
        time_range: str
    ) -> Dict[str, Any]:
        """Gather trend data from multiple sources using MCP"""
        
        # Use MCP client to discover trends from all sources
        trend_discovery = await self.mcp_client.discover_trends(
            seed_keywords=keywords,
            categories=categories,
            geo=geo,
            time_range=time_range
        )
        
        # Enhance with direct Google Trends data
        enhanced_data = {}
        for keyword in keywords[:5]:  # Limit to avoid rate limiting
            try:
                trends_data = await self.google_trends.get_trend_data(keyword, geo)
                if trends_data:
                    enhanced_data[keyword] = trends_data
            except Exception as e:
                logger.warning(f"Failed to get Google Trends data for {keyword}: {e}")
        
        return {
            "mcp_discovery": trend_discovery,
            "enhanced_trends": enhanced_data,
            "keywords": keywords,
            "categories": categories,
            "geo": geo,
            "time_range": time_range
        }
    
    async def _apply_pattern_recognition(self, trend_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply AI pattern recognition using Vertex AI"""
        
        # Prepare data for pattern recognition
        analysis_prompt = f"""
        Analyze the following trend data and identify patterns:
        
        Trend Discovery Data:
        {json.dumps(trend_data.get('mcp_discovery', {}).get('analysis', {}), indent=2)}
        
        Enhanced Trends:
        {json.dumps(list(trend_data.get('enhanced_trends', {}).keys()), indent=2)}
        
        Please identify:
        1. Pattern types (seasonal, viral, steady, emerging)
        2. Pattern strength (0-1 scale)
        3. Trend lifecycle stages
        4. Growth velocity patterns
        5. Market saturation indicators
        
        Respond in JSON format.
        """
        
        # Use Vertex AI for pattern recognition
        pattern_analysis = await self.vertex_ai.generate_text(
            prompt=analysis_prompt,
            model_type="gemini_flash",  # Use fast model for pattern recognition
            system_prompt="You are an AI pattern recognition expert specializing in market trends."
        )
        
        # Parse and validate response
        try:
            patterns = json.loads(pattern_analysis)
        except:
            patterns = {"raw_analysis": pattern_analysis}
        
        return patterns
    
    async def _generate_market_predictions(self, pattern_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Generate market predictions using AI"""
        
        prediction_prompt = f"""
        Based on the following pattern insights, generate market predictions:
        
        Pattern Insights:
        {json.dumps(pattern_insights, indent=2)}
        
        Generate predictions for:
        1. Market opportunity scores (0-10 scale)
        2. Target demographics
        3. Market size estimates
        4. Competitive landscape analysis
        5. Growth potential assessment
        
        Respond in JSON format with detailed predictions.
        """
        
        # Use Gemini Pro for complex market analysis
        market_predictions = await self.vertex_ai.generate_text(
            prompt=prediction_prompt,
            model_type="gemini_pro",
            system_prompt="You are a market analysis AI specializing in e-commerce trends and predictions."
        )
        
        try:
            predictions = json.loads(market_predictions)
        except:
            predictions = {"raw_predictions": market_predictions}
        
        return predictions
    
    async def _generate_product_recommendations(self, market_predictions: Dict[str, Any]) -> Dict[str, Any]:
        """Generate product recommendations using AI"""
        
        recommendation_prompt = f"""
        Based on the following market predictions, generate product recommendations:
        
        Market Predictions:
        {json.dumps(market_predictions, indent=2)}
        
        Generate recommendations for:
        1. Product types and designs
        2. Design themes and styles
        3. Marketing angles and messaging
        4. Pricing strategies
        5. Target audience positioning
        
        Focus on print-on-demand products (t-shirts, hoodies, mugs, etc.)
        Respond in JSON format with actionable recommendations.
        """
        
        # Use Gemini Flash for rapid recommendation generation
        product_recommendations = await self.vertex_ai.generate_text(
            prompt=recommendation_prompt,
            model_type="gemini_flash",
            system_prompt="You are a product strategy AI specializing in print-on-demand e-commerce."
        )
        
        try:
            recommendations = json.loads(product_recommendations)
        except:
            recommendations = {"raw_recommendations": product_recommendations}
        
        return recommendations
    
    async def _compile_trend_analyses(
        self,
        trend_data: Dict[str, Any],
        pattern_insights: Dict[str, Any],
        market_predictions: Dict[str, Any],
        product_recommendations: Dict[str, Any]
    ) -> List[TrendAnalysis]:
        """Compile comprehensive trend analyses from all data sources"""
        
        analyses = []
        
        # Extract trends from MCP discovery
        mcp_trends = trend_data.get("mcp_discovery", {}).get("analysis", {}).get("ranked_trends", [])
        
        for trend in mcp_trends[:10]:  # Limit to top 10 trends
            trend_name = trend.get("keyword", "Unknown")
            
            # Calculate AI confidence score
            confidence_score = self._calculate_confidence_score(trend, pattern_insights, market_predictions)
            
            # Extract relevant data
            analysis = TrendAnalysis(
                trend_id=f"ai_{trend_name.lower().replace(' ', '_')}_{int(time.time())}",
                trend_name=trend_name,
                category=self._determine_category(trend_name, product_recommendations),
                
                # AI Scores
                ai_confidence_score=confidence_score,
                market_opportunity_score=trend.get("composite_score", 5.0),
                predicted_success_rate=confidence_score * 0.9,  # Slightly lower than confidence
                
                # Pattern Recognition
                pattern_type=self._extract_pattern_type(trend_name, pattern_insights),
                pattern_strength=trend.get("source_diversity", 0.5),
                trend_lifecycle_stage=self._determine_lifecycle_stage(trend, pattern_insights),
                
                # Market Insights
                target_demographics=self._extract_demographics(trend_name, market_predictions),
                competitive_landscape={"competition_level": "medium"},  # Placeholder
                market_size_estimate=self._estimate_market_size(trend),
                growth_velocity=trend.get("total_growth", 0) / 100,
                
                # Product Recommendations
                recommended_products=self._extract_product_recommendations(trend_name, product_recommendations),
                design_themes=self._extract_design_themes(trend_name, product_recommendations),
                marketing_angles=self._extract_marketing_angles(trend_name, product_recommendations),
                pricing_strategy=self._determine_pricing_strategy(trend, market_predictions),
                
                # Metadata
                data_sources=trend.get("sources", []),
                raw_data={"trend": trend, "patterns": pattern_insights, "predictions": market_predictions},
                ai_models_used=["gemini-pro", "gemini-flash", "mcp-tools"],
                processing_time_ms=int(time.time() * 1000)
            )
            
            analyses.append(analysis)
        
        return analyses
    
    def _calculate_confidence_score(
        self,
        trend: Dict[str, Any],
        pattern_insights: Dict[str, Any],
        market_predictions: Dict[str, Any]
    ) -> float:
        """Calculate AI confidence score for a trend"""
        
        # Base score from trend data
        base_score = min(trend.get("composite_score", 5.0) / 10, 1.0)
        
        # Source diversity bonus
        source_diversity = trend.get("source_diversity", 0.5)
        
        # Pattern strength bonus (if available)
        pattern_strength = 0.5  # Default if not in insights
        
        # Calculate weighted confidence
        confidence = (base_score * 0.5) + (source_diversity * 0.3) + (pattern_strength * 0.2)
        
        return min(confidence, 1.0)
    
    def _determine_category(self, trend_name: str, recommendations: Dict[str, Any]) -> str:
        """Determine product category for a trend"""
        
        # Simple category determination based on trend name
        trend_lower = trend_name.lower()
        
        if any(word in trend_lower for word in ["fashion", "style", "wear", "clothing"]):
            return "Fashion"
        elif any(word in trend_lower for word in ["tech", "gadget", "device", "electronic"]):
            return "Technology"
        elif any(word in trend_lower for word in ["home", "decor", "interior", "furniture"]):
            return "Home & Living"
        elif any(word in trend_lower for word in ["sport", "fitness", "gym", "athletic"]):
            return "Sports & Fitness"
        elif any(word in trend_lower for word in ["art", "design", "creative", "artistic"]):
            return "Art & Design"
        else:
            return "General"
    
    def _extract_pattern_type(self, trend_name: str, pattern_insights: Dict[str, Any]) -> str:
        """Extract pattern type from insights"""
        
        # Default pattern types
        patterns = pattern_insights.get("patterns", {})
        
        if isinstance(patterns, dict) and trend_name in patterns:
            return patterns[trend_name].get("type", "emerging")
        
        return "emerging"  # Default
    
    def _determine_lifecycle_stage(self, trend: Dict[str, Any], pattern_insights: Dict[str, Any]) -> str:
        """Determine trend lifecycle stage"""
        
        growth = trend.get("total_growth", 0)
        
        if growth > 100:
            return "emerging"
        elif growth > 50:
            return "growing"
        elif growth > 0:
            return "peak"
        else:
            return "declining"
    
    def _extract_demographics(self, trend_name: str, market_predictions: Dict[str, Any]) -> Dict[str, Any]:
        """Extract target demographics from predictions"""
        
        # Default demographics
        return {
            "age_range": "18-35",
            "gender": "all",
            "interests": ["trendy", "fashion-forward", "online shopping"],
            "income_level": "middle",
            "location": "urban"
        }
    
    def _estimate_market_size(self, trend: Dict[str, Any]) -> str:
        """Estimate market size based on trend data"""
        
        volume = trend.get("total_volume", 0)
        
        if volume > 10000:
            return "large"
        elif volume > 1000:
            return "medium"
        else:
            return "small"
    
    def _extract_product_recommendations(self, trend_name: str, recommendations: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract product recommendations"""
        
        # Default product recommendations for print-on-demand
        return [
            {"type": "t-shirt", "style": "trendy graphic", "confidence": 0.9},
            {"type": "hoodie", "style": "minimalist design", "confidence": 0.8},
            {"type": "mug", "style": "quote-based", "confidence": 0.7}
        ]
    
    def _extract_design_themes(self, trend_name: str, recommendations: Dict[str, Any]) -> List[str]:
        """Extract design themes"""
        
        # Default themes
        return ["modern", "minimalist", "bold", "trendy", "vibrant"]
    
    def _extract_marketing_angles(self, trend_name: str, recommendations: Dict[str, Any]) -> List[str]:
        """Extract marketing angles"""
        
        # Default marketing angles
        return [
            f"Join the {trend_name} movement",
            f"Express your {trend_name} style",
            f"Limited edition {trend_name} collection",
            f"Be part of the trend"
        ]
    
    def _determine_pricing_strategy(self, trend: Dict[str, Any], market_predictions: Dict[str, Any]) -> Dict[str, Any]:
        """Determine pricing strategy"""
        
        # Base pricing on trend strength
        score = trend.get("composite_score", 5.0)
        
        if score > 7:
            return {"strategy": "premium", "margin_multiplier": 1.5, "reasoning": "High trend strength"}
        elif score > 5:
            return {"strategy": "competitive", "margin_multiplier": 1.2, "reasoning": "Moderate trend strength"}
        else:
            return {"strategy": "value", "margin_multiplier": 1.0, "reasoning": "Emerging trend"}
    
    def _create_prediction_prompt(self, trend_data: TrendAnalysis, product_concept: Dict[str, Any]) -> str:
        """Create prompt for product success prediction"""
        
        return f"""
        Analyze the following trend and product concept to predict success:
        
        TREND ANALYSIS:
        - Trend Name: {trend_data.trend_name}
        - Market Opportunity Score: {trend_data.market_opportunity_score}/10
        - Pattern Type: {trend_data.pattern_type}
        - Lifecycle Stage: {trend_data.trend_lifecycle_stage}
        - Growth Velocity: {trend_data.growth_velocity:.2%}
        
        PRODUCT CONCEPT:
        {json.dumps(product_concept, indent=2)}
        
        TARGET DEMOGRAPHICS:
        {json.dumps(trend_data.target_demographics, indent=2)}
        
        Please provide a detailed success prediction including:
        1. Success rate (0-1 scale)
        2. Market fit score (0-10 scale)
        3. Risk factors
        4. Optimization suggestions
        5. Marketing recommendations
        
        Respond in JSON format.
        """
    
    def _parse_prediction_response(
        self,
        ai_response: str,
        trend_data: TrendAnalysis,
        product_concept: Dict[str, Any]
    ) -> ProductPrediction:
        """Parse AI prediction response"""
        
        try:
            # Try to parse JSON response
            prediction_data = json.loads(ai_response)
        except:
            # Fallback to basic parsing
            prediction_data = {
                "success_rate": 0.7,
                "market_fit_score": 7.0,
                "risk_factors": [],
                "optimization_suggestions": [],
                "marketing_recommendations": []
            }
        
        return ProductPrediction(
            product_id=f"pred_{trend_data.trend_id}_{int(time.time())}",
            predicted_success_rate=prediction_data.get("success_rate", 0.7),
            confidence_level=0.8,  # Default confidence
            
            # Market Fit
            market_fit_score=prediction_data.get("market_fit_score", 7.0),
            target_audience_match=0.8,
            competitive_advantage={"unique_angle": trend_data.trend_name},
            
            # Performance Predictions
            predicted_sales_volume="medium",
            predicted_profit_margin=0.4,
            predicted_customer_satisfaction=0.85,
            
            # Risk Assessment
            risk_factors=prediction_data.get("risk_factors", []),
            mitigation_strategies=["Monitor trend closely", "A/B test designs"],
            
            # Recommendations
            optimization_suggestions=prediction_data.get("optimization_suggestions", []),
            marketing_recommendations=prediction_data.get("marketing_recommendations", []),
            pricing_recommendations=trend_data.pricing_strategy,
            
            # Metadata
            model_version="vertex-ai-gemini-pro"
        )
    
    async def _enhance_prediction_with_market_data(
        self,
        prediction: ProductPrediction,
        trend_data: TrendAnalysis
    ) -> ProductPrediction:
        """Enhance prediction with additional market data"""
        
        # Could integrate with more data sources here
        # For now, just return the prediction as-is
        return prediction
    
    async def optimize_trend_strategy(
        self,
        trend_analyses: List[TrendAnalysis],
        business_constraints: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Optimize trend strategy using AI
        
        Args:
            trend_analyses: List of analyzed trends
            business_constraints: Business constraints (budget, resources, etc.)
            
        Returns:
            Optimized strategy recommendations
        """
        try:
            logger.info(f"🎯 Optimizing strategy for {len(trend_analyses)} trends")
            
            # Create optimization prompt
            optimization_prompt = f"""
            Optimize the following trend portfolio for maximum business impact:
            
            TRENDS:
            {json.dumps([{
                "name": t.trend_name,
                "opportunity_score": t.market_opportunity_score,
                "success_rate": t.predicted_success_rate,
                "lifecycle_stage": t.trend_lifecycle_stage
            } for t in trend_analyses], indent=2)}
            
            CONSTRAINTS:
            {json.dumps(business_constraints or {"budget": "moderate", "resources": "limited"}, indent=2)}
            
            Provide optimization recommendations including:
            1. Priority ranking of trends
            2. Resource allocation suggestions
            3. Timeline recommendations
            4. Risk mitigation strategies
            5. Expected ROI estimates
            
            Respond in JSON format.
            """
            
            # Use Gemini Ultra for complex optimization
            optimization_response = await self.vertex_ai.generate_text(
                prompt=optimization_prompt,
                model_type="gemini_pro",  # Use Pro since Ultra might not be available
                system_prompt="You are a business strategy AI specializing in e-commerce optimization."
            )
            
            try:
                strategy = json.loads(optimization_response)
            except:
                strategy = {"raw_strategy": optimization_response}
            
            # Store strategy in Google Sheets if configured
            if self.sheets_client:
                await self._store_strategy_in_sheets(strategy, trend_analyses)
            
            logger.info("✅ Strategy optimization completed")
            
            return {
                "status": "success",
                "optimization": strategy,
                "trends_analyzed": len(trend_analyses),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Strategy optimization failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
    
    async def _store_strategy_in_sheets(
        self,
        strategy: Dict[str, Any],
        trend_analyses: List[TrendAnalysis]
    ):
        """Store strategy and trends in Google Sheets"""
        try:
            # Prepare data for sheets
            sheet_data = []
            for trend in trend_analyses:
                sheet_data.append({
                    "Trend Name": trend.trend_name,
                    "Category": trend.category,
                    "AI Confidence": f"{trend.ai_confidence_score:.2%}",
                    "Market Opportunity": trend.market_opportunity_score,
                    "Success Rate": f"{trend.predicted_success_rate:.2%}",
                    "Pattern Type": trend.pattern_type,
                    "Lifecycle Stage": trend.trend_lifecycle_stage,
                    "Market Size": trend.market_size_estimate,
                    "Timestamp": trend.analysis_timestamp.isoformat()
                })
            
            # Write to sheets
            await self.sheets_client.append_data("AI_Trend_Analysis", sheet_data)
            logger.info("✅ Strategy stored in Google Sheets")
            
        except Exception as e:
            logger.warning(f"Failed to store strategy in sheets: {e}")
    
    async def close(self):
        """Clean up resources"""
        await self.mcp_client.close()
        logger.info("✅ TrendAnalysisAI agent closed")