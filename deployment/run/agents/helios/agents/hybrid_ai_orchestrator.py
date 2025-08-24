"""
Hybrid AI Orchestrator - Simplified Predictable AI System
Combines structured AI analysis with traditional pipeline for reliability
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field
from loguru import logger

from ..config import HeliosConfig
from ..services.automated_trend_discovery import AutomatedTrendDiscovery
from ..agents.trend_analyst_ai import TrendAnalystAI, create_trend_analyst_ai


class HybridOrchestrationResult(BaseModel):
    """Structured result from hybrid orchestration"""
    status: str = Field(..., pattern="^(success|failed|partial)$")
    session_id: str
    opportunities: List[Dict[str, Any]] = Field(default_factory=list)
    total_analyzed: int = Field(ge=0)
    ai_validated: int = Field(ge=0)
    traditional_validated: int = Field(ge=0)
    execution_summary: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str
    error_message: Optional[str] = None


class HybridAIOrchestrator:
    """
    Hybrid AI Orchestrator combining:
    1. Traditional trend discovery pipeline (reliable baseline)
    2. AI-powered analysis and validation (intelligent enhancement)
    3. Structured outputs with Pydantic validation (predictable results)
    """
    
    def __init__(self, config: HeliosConfig):
        self.config = config
        
        # Traditional pipeline (reliable baseline)
        self.traditional_discovery = AutomatedTrendDiscovery(config)
        
        # AI enhancement components
        self.ai_trend_analyst: Optional[TrendAnalystAI] = None
        
        # Configuration
        self.max_trends_to_analyze = 10
        self.ai_confidence_threshold = 0.7
        self.hybrid_score_weight = 0.6  # 60% AI, 40% traditional
        
        logger.info("🔀 Hybrid AI Orchestrator initialized - Traditional reliability + AI intelligence")
    
    async def orchestrate_trend_discovery(self, seed_keywords: List[str]) -> Dict[str, Any]:
        """
        Hybrid orchestration: Traditional discovery + AI enhancement
        """
        session_id = f"hybrid_{int(time.time())}"
        start_time = time.time()
        
        logger.info(f"🔀 Starting hybrid orchestration session: {session_id}")
        
        try:
            # PHASE 1: Traditional trend discovery (reliable baseline)
            logger.info("📊 Phase 1: Traditional trend discovery...")
            traditional_result = await self.traditional_discovery.run_discovery_pipeline(seed_keywords)
            
            if traditional_result.get("status") != "success":
                logger.warning("⚠️ Traditional discovery failed, continuing with AI-only analysis")
                traditional_opportunities = []
            else:
                traditional_opportunities = traditional_result.get("opportunities", [])
                
            logger.info(f"📊 Traditional discovery found {len(traditional_opportunities)} opportunities")
            
            # PHASE 2: AI-powered analysis and validation
            logger.info("🧠 Phase 2: AI-powered analysis and validation...")
            ai_validated_opportunities = await self._ai_validate_opportunities(traditional_opportunities)
            
            # PHASE 3: Hybrid scoring and final selection
            logger.info("🔀 Phase 3: Hybrid scoring and final selection...")
            final_opportunities = self._apply_hybrid_scoring(traditional_opportunities, ai_validated_opportunities)
            
            # Compile structured results
            execution_time = time.time() - start_time
            result = HybridOrchestrationResult(
                status="success",
                session_id=session_id,
                opportunities=final_opportunities,
                total_analyzed=len(traditional_opportunities),
                ai_validated=len(ai_validated_opportunities),
                traditional_validated=len(traditional_opportunities),
                execution_summary={
                    "execution_time_seconds": round(execution_time, 2),
                    "traditional_pipeline_status": traditional_result.get("status", "failed"),
                    "ai_analysis_completed": len(ai_validated_opportunities),
                    "final_opportunities_selected": len(final_opportunities),
                    "hybrid_scoring_applied": True
                },
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"✅ Hybrid orchestration completed: {len(final_opportunities)} final opportunities")
            return result.dict()
            
        except Exception as e:
            logger.error(f"❌ Hybrid orchestration failed: {e}")
            return HybridOrchestrationResult(
                status="failed",
                session_id=session_id,
                error_message=str(e),
                execution_summary={"error_occurred_at": "orchestration"},
                timestamp=datetime.now().isoformat(),
                total_analyzed=0,
                ai_validated=0,
                traditional_validated=0
            ).dict()
    
    async def _ai_validate_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use AI to validate and enhance traditional opportunities"""
        
        if not opportunities:
            logger.info("🧠 No opportunities to validate with AI")
            return []
        
        # Initialize AI analyst if needed
        if self.ai_trend_analyst is None:
            try:
                self.ai_trend_analyst = await create_trend_analyst_ai(self.config)
                logger.info("🧠 AI Trend Analyst initialized")
            except Exception as e:
                logger.warning(f"⚠️ Failed to initialize AI analyst: {e}")
                return []
        
        validated_opportunities = []
        
        # Limit analysis to top opportunities for performance
        top_opportunities = opportunities[:self.max_trends_to_analyze]
        
        try:
            # Convert opportunities to format expected by AI analyst
            trends_data = []
            for opp in top_opportunities:
                trend_data = {
                    "trend_name": opp.get("trend_name", "Unknown"),
                    "keywords": opp.get("related_keywords", []),
                    "opportunity_score": opp.get("opportunity_score", 0),
                    "confidence_level": opp.get("confidence_level", 0),
                    "velocity": opp.get("velocity", "stable"),
                    "competition_level": opp.get("competition_level", "unknown"),
                    "source": "traditional_discovery"
                }
                trends_data.append(trend_data)
            
            # Get AI analysis
            ai_analyses = await self.ai_trend_analyst.analyze_trends(trends_data, max_trends=self.max_trends_to_analyze)
            
            # Convert AI analyses back to opportunity format
            for analysis in ai_analyses:
                if analysis.confidence >= self.ai_confidence_threshold:
                    validated_opp = {
                        "trend_name": analysis.trend_name,
                        "opportunity_score": analysis.opportunity_score,
                        "confidence_level": analysis.confidence,
                        "ai_recommended_action": analysis.recommended_action,
                        "ai_reasoning": analysis.reasoning,
                        "commercial_viability": analysis.commercial_viability,
                        "market_timing": analysis.market_timing,
                        "target_demographics": analysis.target_demographics,
                        "product_categories": analysis.product_categories,
                        "competitive_landscape": analysis.competitive_landscape,
                        "viral_potential": analysis.viral_potential,
                        "validation_source": "ai_analysis"
                    }
                    validated_opportunities.append(validated_opp)
                    
            logger.info(f"🧠 AI validated {len(validated_opportunities)} opportunities")
            return validated_opportunities
            
        except Exception as e:
            logger.error(f"❌ AI validation failed: {e}")
            return []
    
    def _apply_hybrid_scoring(self, traditional_opps: List[Dict[str, Any]], ai_opps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Apply hybrid scoring combining traditional and AI insights"""
        
        hybrid_opportunities = []
        
        # Create lookup for AI validations
        ai_lookup = {opp.get("trend_name", ""): opp for opp in ai_opps}
        
        for trad_opp in traditional_opps:
            trend_name = trad_opp.get("trend_name", "")
            
            # Check if AI also validated this trend
            ai_opp = ai_lookup.get(trend_name)
            
            if ai_opp:
                # Hybrid scoring: combine traditional and AI scores
                trad_score = trad_opp.get("opportunity_score", 0)
                ai_score = ai_opp.get("opportunity_score", 0)
                
                hybrid_score = (ai_score * self.hybrid_score_weight) + (trad_score * (1 - self.hybrid_score_weight))
                
                # Enhanced opportunity with both traditional and AI insights
                hybrid_opp = {
                    **trad_opp,  # Start with traditional data
                    "opportunity_score": hybrid_score,
                    "hybrid_score": True,
                    "traditional_score": trad_score,
                    "ai_score": ai_score,
                    "ai_confidence": ai_opp.get("confidence_level", 0),
                    "ai_recommended_action": ai_opp.get("ai_recommended_action", "unknown"),
                    "ai_reasoning": ai_opp.get("ai_reasoning", ""),
                    "commercial_viability": ai_opp.get("commercial_viability", "unknown"),
                    "market_timing": ai_opp.get("market_timing", "unknown"),
                    "validation_status": "hybrid_validated"
                }
                hybrid_opportunities.append(hybrid_opp)
                
            elif trad_opp.get("opportunity_score", 0) >= self.config.min_opportunity_score:
                # Traditional-only opportunity that meets threshold
                traditional_only_opp = {
                    **trad_opp,
                    "hybrid_score": False,
                    "validation_status": "traditional_only"
                }
                hybrid_opportunities.append(traditional_only_opp)
        
        # Sort by hybrid score (or traditional score for traditional-only)
        hybrid_opportunities.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
        
        # Apply final filtering
        final_opportunities = []
        for opp in hybrid_opportunities:
            if opp.get("opportunity_score", 0) >= self.config.min_opportunity_score:
                final_opportunities.append(opp)
        
        logger.info(f"🔀 Hybrid scoring produced {len(final_opportunities)} final opportunities")
        return final_opportunities


async def create_hybrid_ai_orchestrator(config: HeliosConfig) -> HybridAIOrchestrator:
    """Create and initialize hybrid AI orchestrator"""
    return HybridAIOrchestrator(config)

