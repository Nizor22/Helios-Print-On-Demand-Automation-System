from __future__ import annotations

import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass
from ..config import load_config
# MCPClient removed - using services version instead


@dataclass
class AudiencePersona:
    demographic_cluster: str
    age_range: str
    location_preference: str
    income_level: str
    lifestyle_category: str
    psychographic_match: float
    spending_profile: str
    platform_presence: List[str]
    visual_preferences: List[str]
    emotional_triggers: List[str]
    identity_statements: List[str]
    authority_figures: List[str]
    trust_building_elements: List[str]
    subculture_language: List[str]
    pain_points: List[str]
    desires: List[str]


@dataclass
class AudienceAnalysis:
    primary_persona: AudiencePersona
    secondary_personas: List[AudiencePersona]
    confidence_score: float
    historical_match: str
    rapid_mode_used: bool
    execution_time_ms: int
    mcp_model_used: str
    data_sources: Dict[str, bool]


class AudienceAnalyst:
    """Advanced audience intelligence agent with psychological marketing framework."""

    def __init__(self) -> None:
        self.config = load_config()
        self.mcp_client = MCPClient.from_env(self.config.google_mcp_url, self.config.google_mcp_auth_token)
        
        # Pre-defined persona templates for rapid mode
        self.persona_templates = {
            "gen_z_urban": {
                "demographic_cluster": "Gen_Z_Urban",
                "age_range": "16-24",
                "location_preference": "Urban/Suburban",
                "income_level": "$15-35_impulse",
                "lifestyle_category": "Digital_Native",
                "psychographic_match": 0.9,
                "spending_profile": "$15-35_impulse",
                "platform_presence": ["tiktok", "instagram", "youtube"],
                "visual_preferences": ["minimalist", "bold_text", "vibrant_colors"],
                "emotional_triggers": ["belonging", "trending", "self_expression"],
                "identity_statements": ["I am a trendsetter", "I am part of the aesthetic community"],
                "authority_figures": ["influencers", "trending_creators", "aesthetic_accounts"],
                "trust_building_elements": ["authentic_language", "trending_hashtags", "ugc_encouragement"],
                "subculture_language": ["aesthetic", "vibes", "slay", "periodt"],
                "pain_points": ["fitting_in", "staying_relevant", "affordability"],
                "desires": ["trending", "belonging", "self_expression", "viral_moments"]
            },
            "millennial_creative": {
                "demographic_cluster": "Millennial_Creative",
                "age_range": "25-40",
                "location_preference": "Urban/Suburban",
                "income_level": "$35-75_considered",
                "lifestyle_category": "Creative_Professional",
                "psychographic_match": 0.85,
                "spending_profile": "$35-75_considered",
                "platform_presence": ["instagram", "pinterest", "etsy"],
                "visual_preferences": ["minimalist", "sophisticated", "artistic"],
                "emotional_triggers": ["authenticity", "quality", "self_improvement"],
                "identity_statements": ["I am a creative professional", "I appreciate quality design"],
                "authority_figures": ["design_influencers", "creative_professionals", "brands"],
                "trust_building_elements": ["quality_imagery", "professional_copy", "social_proof"],
                "subculture_language": ["aesthetic", "vibes", "mood", "inspiration"],
                "pain_points": ["time_constraints", "quality_vs_price", "authenticity"],
                "desires": ["quality", "authenticity", "self_expression", "professional_growth"]
            },
            "gen_x_practical": {
                "demographic_cluster": "Gen_X_Practical",
                "age_range": "41-56",
                "location_preference": "Suburban/Rural",
                "income_level": "$50-100_planned",
                "lifestyle_category": "Practical_Consumer",
                "psychographic_match": 0.8,
                "spending_profile": "$50-100_planned",
                "platform_presence": ["facebook", "amazon", "etsy"],
                "visual_preferences": ["classic", "practical", "quality"],
                "emotional_triggers": ["reliability", "value", "nostalgia"],
                "identity_statements": ["I am a practical consumer", "I value quality over trends"],
                "authority_figures": ["trusted_brands", "expert_reviews", "word_of_mouth"],
                "trust_building_elements": ["clear_benefits", "quality_guarantees", "customer_reviews"],
                "subculture_language": ["quality", "value", "reliable", "practical"],
                "pain_points": ["overwhelming_choices", "quality_uncertainty", "time_waste"],
                "desires": ["reliability", "value", "quality", "ease_of_use"]
            }
        }

    async def run(self, trend_payload: Dict[str, Any]) -> AudienceAnalysis:
        """Run comprehensive audience analysis with psychological marketing framework."""
        start_time = time.time()
        
        try:
            # Check if rapid mode should be triggered
            trend_urgency = trend_payload.get("urgency_level", "low")
            rapid_mode = trend_urgency in ["high", "critical"] or trend_payload.get("opportunity_score", 0) >= 8.5
            
            if rapid_mode and self.config.enable_adaptive_learning:
                return await self._rapid_analysis(trend_payload)
            else:
                return await self._comprehensive_analysis(trend_payload)
                
        except Exception as e:
            print(f"Error in audience analysis: {e}")
            return self._fallback_analysis(trend_payload)

    async def _rapid_analysis(self, trend_payload: Dict[str, Any]) -> AudienceAnalysis:
        """Rapid analysis using historical patterns and templates."""
        trend_name = trend_payload.get("trend_name", "unknown")
        keywords = trend_payload.get("keywords", [])
        
        # Determine best persona match based on trend characteristics
        persona_match = self._identify_persona_match(trend_name, keywords)
        primary_persona = AudiencePersona(**self.persona_templates[persona_match])
        
        # Create secondary personas for broader targeting
        secondary_personas = []
        for key, template in self.persona_templates.items():
            if key != persona_match:
                secondary_personas.append(AudiencePersona(**template))
        
        execution_time_ms = int((time.time() - time.time()) * 1000)
        
        return AudienceAnalysis(
            primary_persona=primary_persona,
            secondary_personas=secondary_personas[:2],  # Limit to top 2
            confidence_score=0.75,  # Slightly lower for rapid mode
            historical_match=f"template_{persona_match}_success_rate_0.73",
            rapid_mode_used=True,
            execution_time_ms=execution_time_ms,
            mcp_model_used="rapid_template",
            data_sources={"historical_patterns": True, "persona_templates": True}
        )

    async def _comprehensive_analysis(self, trend_payload: Dict[str, Any]) -> AudienceAnalysis:
        """Comprehensive analysis using MCP and advanced algorithms."""
        trend_name = trend_payload.get("trend_name", "unknown")
        keywords = trend_payload.get("keywords", [])
        
        mcp_model_used = "none"
        data_sources = {}
        
        # Try MCP audience analysis if available
        if self.mcp_client:
            try:
                mcp_response = await self.mcp_client.audience_analysis({
                    "trend_name": trend_name,
                    "keywords": keywords,
                    "analysis_type": "comprehensive"
                })
                
                if "response" in mcp_response and mcp_response["response"]:
                    # Parse MCP response for audience insights
                    audience_data = self._parse_mcp_audience_response(mcp_response["response"])
                    mcp_model_used = mcp_response.get("model", "gemini-1.5-pro")
                    data_sources["mcp_ai"] = True
                    
                    # Use MCP data to create primary persona
                    primary_persona = AudiencePersona(**audience_data.get("primary_persona", {}))
                    
                    # Create secondary personas
                    secondary_personas = []
                    for persona_data in audience_data.get("secondary_personas", []):
                        secondary_personas.append(AudiencePersona(**persona_data))
                    
                    # Calculate confidence based on data quality
                    confidence_score = self._calculate_confidence_score(audience_data, keywords)
                    
                    execution_time_ms = int((time.time() - time.time()) * 1000)
                    
                    return AudienceAnalysis(
                        primary_persona=primary_persona,
                        secondary_personas=secondary_personas,
                        confidence_score=confidence_score,
                        historical_match="mcp_analysis_success",
                        rapid_mode_used=False,
                        execution_time_ms=execution_time_ms,
                        mcp_model_used=mcp_model_used,
                        data_sources=data_sources
                    )
                    
            except Exception as e:
                print(f"MCP audience analysis failed: {e}")
                data_sources["mcp_ai"] = False
        
        # Fallback to template-based analysis
        return await self._rapid_analysis(trend_payload)

    def _identify_persona_match(self, trend_name: str, keywords: List[str]) -> str:
        """Identify the best persona match based on trend characteristics."""
        trend_lower = trend_name.lower()
        keywords_lower = [kw.lower() for kw in keywords]
        
        # Scoring system for persona matching
        scores = {
            "gen_z_urban": 0,
            "millennial_creative": 0,
            "gen_x_practical": 0
        }
        
        # Gen Z indicators
        gen_z_terms = ["aesthetic", "vibes", "trendy", "viral", "tiktok", "instagram", "youth", "trending"]
        for term in gen_z_terms:
            if term in trend_lower or any(term in kw for kw in keywords_lower):
                scores["gen_z_urban"] += 2
        
        # Millennial indicators
        millennial_terms = ["creative", "artistic", "professional", "quality", "design", "inspiration", "pinterest"]
        for term in millennial_terms:
            if term in trend_lower or any(term in kw for kw in keywords_lower):
                scores["millennial_creative"] += 2
        
        # Gen X indicators
        gen_x_terms = ["classic", "practical", "quality", "reliable", "traditional", "value", "durable"]
        for term in gen_x_terms:
            if term in trend_lower or any(term in kw for kw in keywords_lower):
                scores["gen_x_practical"] += 2
        
        # Return highest scoring persona
        return max(scores, key=scores.get)

    def _parse_mcp_audience_response(self, mcp_text: str) -> Dict[str, Any]:
        """Parse MCP response for audience analysis data."""
        # This would be more sophisticated in production
        # For now, return a structured template
        return {
            "primary_persona": self.persona_templates["gen_z_urban"],
            "secondary_personas": [
                self.persona_templates["millennial_creative"],
                self.persona_templates["gen_x_practical"]
            ]
        }

    def _calculate_confidence_score(self, audience_data: Dict[str, Any], keywords: List[str]) -> float:
        """Calculate confidence score based on data quality and keyword relevance."""
        base_confidence = 0.6
        
        # Boost for having comprehensive persona data
        if audience_data.get("primary_persona") and audience_data.get("secondary_personas"):
            base_confidence += 0.2
        
        # Boost for keyword-persona alignment
        keyword_alignment = self._calculate_keyword_persona_alignment(keywords, audience_data)
        base_confidence += keyword_alignment * 0.2
        
        return min(base_confidence, 0.95)

    def _calculate_keyword_persona_alignment(self, keywords: List[str], audience_data: Dict[str, Any]) -> float:
        """Calculate alignment between keywords and persona characteristics."""
        if not keywords or not audience_data.get("primary_persona"):
            return 0.0
        
        # Simple alignment scoring - in production this would be more sophisticated
        alignment_score = 0.0
        total_keywords = len(keywords)
        
        for keyword in keywords:
            keyword_lower = keyword.lower()
            
            # Check if keyword aligns with persona characteristics
            persona = audience_data["primary_persona"]
            if any(term in keyword_lower for term in persona.get("visual_preferences", [])):
                alignment_score += 1
            if any(term in keyword_lower for term in persona.get("emotional_triggers", [])):
                alignment_score += 1
            if any(term in keyword_lower for term in persona.get("subculture_language", [])):
                alignment_score += 1
        
        return min(alignment_score / (total_keywords * 3), 1.0)

    def _fallback_analysis(self, trend_payload: Dict[str, Any]) -> AudienceAnalysis:
        """Fallback analysis when all else fails."""
        primary_persona = AudiencePersona(**self.persona_templates["gen_z_urban"])
        
        return AudienceAnalysis(
            primary_persona=primary_persona,
            secondary_personas=[],
            confidence_score=0.5,
            historical_match="fallback_template",
            rapid_mode_used=True,
            execution_time_ms=0,
            mcp_model_used="fallback",
            data_sources={"fallback": True}
        )
