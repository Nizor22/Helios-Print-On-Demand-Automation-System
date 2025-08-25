from __future__ import annotations

import random
import time
from typing import Any, Dict, List, Tuple, Optional
from ..config import load_config
# MCPClient removed - using services version instead


class ZeitgeistAgent:
    """Enhanced trend detection agent using Google MCP and Gemini 2.0 Flash for fast analysis with psychological marketing framework."""

    def __init__(self) -> None:
        self.config = load_config()
        # Initialize MCP client conditionally to avoid import issues
        try:
            from ..services.mcp_integration.mcp_client import GoogleMCPClient
            self.mcp_client = GoogleMCPClient(
                server_url=self.config.google_mcp_url,
                auth_token=self.config.google_mcp_auth_token
            ) if self.config.google_mcp_url else None
        except ImportError:
            self.mcp_client = None
        self.start_time = None

    async def run(self, seed: Optional[str] = None) -> Dict[str, Any]:
        """Run enhanced trend analysis preferring unified MCP trend_research, using seed as a hint."""
        
        self.start_time = time.time()
        
        # Use provided seed or generate one
        if not seed:
            seed = self._generate_seed()
        
        try:
            # Initialize trend data
            ai_keywords = []
            google_trends_keywords = []
            mcp_model_used = "none"
            ai_analysis = ""
            
            # Prefer unified MCP trend_research (merges trends, social, news)
            if self.mcp_client:
                try:
                    unified = await self.mcp_client.trend_research(geo="US", top_n=20, seed=seed)
                    if unified and "data" in unified:
                        # Use combined keywords as primary set
                        google_trends_keywords = list(unified["data"].get("keywords", []))
                        # Retain model used (from trends call) for reporting
                        mcp_model_used = unified.get("model", "gemini-2.0-flash-exp")
                        print(f"MCP trend_research: {len(google_trends_keywords)} keywords combined")
                except Exception as e:
                    print(f"MCP trend_research failed: {e}")
            
            # Fallback to direct Google Trends if MCP not available
            if not google_trends_keywords and not self.mcp_client:
                try:
                    from ..trends.google_trends import fetch_trends
                    google_trends_keywords = fetch_trends(seed, "US", "now 7-d", 10)
                    print(f"Direct Google Trends fallback: {len(google_trends_keywords)} keywords")
                except Exception as e:
                    print(f"Direct Google Trends fallback failed: {e}")
            
            # Enhanced psychological analysis
            emotional_driver = self._identify_emotional_driver(seed, ai_analysis, google_trends_keywords)
            psychological_insights = self._analyze_psychological_factors(seed, emotional_driver, google_trends_keywords)
            
            # Combine and deduplicate keywords with priority weighting
            combined_keywords = self._combine_keywords_with_priority(
                ai_keywords, 
                google_trends_keywords, 
                seed
            )
            
            # Calculate enhanced metrics using psychological framework
            opportunity_score = self._calculate_enhanced_opportunity_score(
                combined_keywords, seed, google_trends_keywords, emotional_driver, psychological_insights
            )
            velocity = self._assess_velocity(seed, combined_keywords, google_trends_keywords)
            urgency_level = self._assess_urgency(seed, combined_keywords, google_trends_keywords)
            confidence_level = self._calculate_confidence_level(ai_keywords, google_trends_keywords, seed)
            
            # Calculate execution time
            execution_time_ms = int((time.time() - self.start_time) * 1000)
            
            return {
                "status": "approved",
                "trend_name": seed,
                "keywords": combined_keywords,
                "opportunity_score": opportunity_score,
                "velocity": velocity,
                "urgency_level": urgency_level,
                "ethical_status": "approved",  # Will be screened by ethics agent
                "confidence_level": confidence_level,
                "mcp_model_used": mcp_model_used,
                "google_trends": google_trends_keywords,
                "ai_keywords": ai_keywords,
                "ai_analysis": ai_analysis,
                "emotional_driver": emotional_driver,
                "psychological_insights": psychological_insights,
                "trend_sources": {
                    "mcp_ai": len(ai_keywords) > 0,
                    "google_trends": len(google_trends_keywords) > 0,
                    "fallback": len(ai_keywords) == 0 and len(google_trends_keywords) == 0
                },
                "execution_time_ms": execution_time_ms,
                "priority": "HIGH" if urgency_level == "high" and opportunity_score >= 8.0 else "MEDIUM"
            }
            
        except Exception as e:
            print(f"Error in trend analysis: {e}")
            return self._generate_mock_trend(seed)

    def _extract_keywords_from_ai(self, ai_text: str) -> List[str]:
        """Extract keywords from AI response"""
        # Simple keyword extraction - in production you'd want more sophisticated parsing
        words = ai_text.split()
        keywords = []
        for word in words:
            word = word.strip(".,!?\"':;()[]{}").lower()
            if len(word) >= 3 and word not in ["the", "and", "for", "with", "this", "that", "are", "was", "were", "have", "has", "had"]:
                keywords.append(word)
        return keywords[:10]  # Limit to top 10

    def _combine_keywords_with_priority(self, ai_keywords: List[str], google_trends: List[str], seed: str) -> List[str]:
        """Combine keywords with priority weighting"""
        combined = []
        
        # Add seed-related keywords first
        seed_words = [word.lower() for word in seed.split() if len(word) >= 3]
        combined.extend(seed_words)
        
        # Add Google Trends keywords (high priority - real-time data)
        for keyword in google_trends[:8]:  # Top 8 trending
            if keyword.lower() not in [kw.lower() for kw in combined]:
                combined.append(keyword)
        
        # Add AI-generated keywords (medium priority)
        for keyword in ai_keywords[:6]:  # Top 6 AI-generated
            if keyword.lower() not in [kw.lower() for kw in combined]:
                combined.append(keyword)
        
        # Add category-specific keywords
        category_keywords = self._get_category_keywords(seed)
        for keyword in category_keywords:
            if keyword.lower() not in [kw.lower() for kw in combined]:
                combined.append(keyword)
        
        return combined[:15]  # Limit to top 15

    def _get_category_keywords(self, seed: str) -> List[str]:
        """Get category-specific keywords based on seed"""
        seed_lower = seed.lower()
        
        if any(term in seed_lower for term in ["vintage", "retro", "nostalgic"]):
            return ["vintage", "retro", "nostalgic", "classic", "timeless", "heritage"]
        elif any(term in seed_lower for term in ["minimalist", "simple", "clean"]):
            return ["minimalist", "simple", "clean", "modern", "elegant", "sophisticated"]
        elif any(term in seed_lower for term in ["aesthetic", "style", "fashion"]):
            return ["aesthetic", "style", "fashion", "trendy", "chic", "vogue"]
        elif any(term in seed_lower for term in ["gaming", "gamer", "video"]):
            return ["gaming", "gamer", "video", "esports", "streaming", "competitive"]
        elif any(term in seed_lower for term in ["quote", "inspirational", "motivational"]):
            return ["quote", "inspirational", "motivational", "positive", "uplifting", "empowering"]
        else:
            return ["trending", "popular", "viral", "buzz", "momentum", "hot"]

    def _calculate_opportunity_score(self, keywords: List[str], seed: str, google_trends: List[str]) -> float:
        """Calculate opportunity score based on keywords, seed, and Google Trends data"""
        base_score = 6.0
        
        # Boost for Google Trends keywords (real-time trending data)
        trending_boost = min(len(google_trends) * 0.3, 2.0)
        
        # Boost for AI-generated keywords (insightful analysis)
        ai_boost = min(len([k for k in keywords if k in seed.lower()]) * 0.2, 1.0)
        
        # Boost for specific high-value categories
        high_value_terms = ["vintage", "retro", "minimalist", "aesthetic", "trendy", "viral", "popular", "gaming"]
        category_boost = sum(0.2 for term in high_value_terms if term in seed.lower())
        
        # Boost for keyword diversity
        diversity_boost = min(len(set(keywords)) * 0.1, 1.0)
        
        final_score = base_score + trending_boost + ai_boost + category_boost + diversity_boost
        return min(final_score, 10.0)

    def _calculate_confidence_level(self, ai_keywords: List[str], google_trends: List[str], seed: str) -> float:
        """Calculate confidence level based on data sources and quality"""
        base_confidence = 0.5
        
        # Boost for having both AI and Google Trends data
        if len(ai_keywords) > 0 and len(google_trends) > 0:
            base_confidence += 0.3
        elif len(ai_keywords) > 0 or len(google_trends) > 0:
            base_confidence += 0.2
        
        # Boost for keyword quantity and quality
        total_keywords = len(ai_keywords) + len(google_trends)
        if total_keywords >= 10:
            base_confidence += 0.2
        elif total_keywords >= 5:
            base_confidence += 0.1
        
        # Boost for seed relevance
        seed_relevance = sum(1 for keyword in ai_keywords + google_trends if any(word in keyword.lower() for word in seed.lower().split()))
        if seed_relevance >= 3:
            base_confidence += 0.1
        
        return min(base_confidence, 0.95)

    def _assess_velocity(self, seed: str, keywords: List[str], google_trends: List[str]) -> str:
        """Assess trend velocity based on multiple data sources"""
        # High velocity indicators
        if len(google_trends) >= 8:
            return "accelerating"
        elif len(google_trends) >= 5:
            return "stable"
        elif len(keywords) >= 8:
            return "stable"
        else:
            return "monitor"

    def _assess_urgency(self, seed: str, keywords: List[str], google_trends: List[str]) -> str:
        """Assess urgency level based on multiple data sources"""
        urgent_terms = ["viral", "trending", "hot", "popular", "buzz", "momentum", "exploding", "surge"]
        
        # Check seed for urgency
        if any(term in seed.lower() for term in urgent_terms):
            return "high"
        
        # Check Google Trends for urgency
        if len(google_trends) >= 8:
            return "high"
        elif len(google_trends) >= 5:
            return "medium"
        elif len(keywords) >= 8:
            return "medium"
        else:
            return "low"

    def _identify_emotional_driver(self, seed: str, ai_analysis: str, google_trends: List[str]) -> Dict[str, Any]:
        """Identify core human emotion driving the trend"""
        emotional_drivers = {
            "desire": ["want", "crave", "aspire", "dream", "fantasy", "luxury", "exclusive"],
            "fear": ["anxiety", "worry", "stress", "protection", "security", "safety"],
            "pride": ["achievement", "status", "recognition", "success", "accomplishment"],
            "nostalgia": ["memory", "childhood", "retro", "vintage", "classic", "heritage"],
            "belonging": ["community", "tribe", "identity", "group", "culture", "movement"]
        }
        
        # Analyze seed and AI analysis for emotional indicators
        text_to_analyze = f"{seed} {ai_analysis}".lower()
        
        emotion_scores = {}
        for emotion, indicators in emotional_drivers.items():
            score = sum(1 for indicator in indicators if indicator in text_to_analyze)
            emotion_scores[emotion] = score
        
        # Find dominant emotion
        dominant_emotion = max(emotion_scores.items(), key=lambda x: x[1])
        
        return {
            "primary_emotion": dominant_emotion[0] if dominant_emotion[1] > 0 else "desire",
            "emotion_scores": emotion_scores,
            "confidence": min(dominant_emotion[1] / 3.0, 1.0)  # Normalize to 0-1
        }

    def _analyze_psychological_factors(self, seed: str, emotional_driver: Dict, google_trends: List[str]) -> Dict[str, Any]:
        """Analyze psychological factors for marketing optimization"""
        return {
            "identity_statements": self._extract_identity_statements(seed, google_trends),
            "authority_figures": self._identify_authority_figures(seed, google_trends),
            "trust_building_elements": self._identify_trust_elements(seed, emotional_driver),
            "social_proof_indicators": self._identify_social_proof(google_trends),
            "urgency_triggers": self._identify_urgency_triggers(seed, google_trends)
        }

    def _extract_identity_statements(self, seed: str, google_trends: List[str]) -> List[str]:
        """Extract potential identity statements from trend data"""
        identity_patterns = [
            "I am a", "I'm a", "We are", "We're", "My people", "Our community",
            "dog mom", "cat dad", "gamer", "artist", "entrepreneur", "student"
        ]
        
        statements = []
        for pattern in identity_patterns:
            if pattern.lower() in seed.lower():
                statements.append(pattern)
        
        # Add trending identity terms
        identity_terms = ["aesthetic", "lifestyle", "culture", "movement", "community"]
        for term in identity_terms:
            if term in seed.lower():
                statements.append(f"part of the {term} movement")
        
        return statements

    def _identify_authority_figures(self, seed: str, google_trends: List[str]) -> List[str]:
        """Identify potential authority figures and influencers"""
        authority_indicators = ["influencer", "expert", "guru", "master", "pro", "celebrity"]
        authorities = []
        
        for indicator in authority_indicators:
            if indicator in seed.lower():
                authorities.append(f"{indicator} in {seed.split()[0]} space")
        
        return authorities

    def _identify_trust_elements(self, seed: str, emotional_driver: Dict) -> List[str]:
        """Identify trust-building elements based on emotional driver"""
        trust_elements = {
            "desire": ["aspirational", "premium", "exclusive", "authentic"],
            "fear": ["safe", "secure", "trusted", "proven", "reliable"],
            "pride": ["prestigious", "recognized", "award-winning", "elite"],
            "nostalgia": ["timeless", "classic", "heritage", "authentic"],
            "belonging": ["community-driven", "inclusive", "authentic", "genuine"]
        }
        
        primary_emotion = emotional_driver.get("primary_emotion", "desire")
        return trust_elements.get(primary_emotion, ["authentic", "trusted"])

    def _identify_social_proof(self, google_trends: List[str]) -> List[str]:
        """Identify social proof indicators from trending data"""
        social_proof_terms = ["viral", "trending", "popular", "buzz", "momentum", "exploding"]
        indicators = []
        
        for term in social_proof_terms:
            if term in [kw.lower() for kw in google_trends]:
                indicators.append(f"Currently {term}")
        
        if len(google_trends) >= 5:
            indicators.append(f"Trending across {len(google_trends)}+ keywords")
        
        return indicators

    def _identify_urgency_triggers(self, seed: str, google_trends: List[str]) -> List[str]:
        """Identify urgency and scarcity triggers"""
        urgency_terms = ["limited", "exclusive", "seasonal", "trending", "viral", "momentum"]
        triggers = []
        
        for term in urgency_terms:
            if term in seed.lower():
                triggers.append(f"{term.title()} opportunity")
        
        if len(google_trends) >= 8:
            triggers.append("High velocity trend - act fast")
        
        return triggers

    def _calculate_enhanced_opportunity_score(self, keywords: List[str], seed: str, google_trends: List[str], 
                                           emotional_driver: Dict, psychological_insights: Dict) -> float:
        """Calculate enhanced opportunity score using psychological framework"""
        base_score = 6.0
        
        # Social velocity (30% weight)
        social_velocity_score = min(len(google_trends) * 0.3, 2.0)
        
        # Search growth (25% weight) - based on keyword diversity
        search_growth_score = min(len(set(keywords)) * 0.25, 2.0)
        
        # Influencer adoption (20% weight) - based on authority figures identified
        influencer_score = min(len(psychological_insights.get("authority_figures", [])) * 0.4, 2.0)
        
        # Product potential (15% weight) - based on identity statements
        product_potential_score = min(len(psychological_insights.get("identity_statements", [])) * 0.3, 1.5)
        
        # Timing factor (10% weight) - based on urgency
        urgency_score = min(len(psychological_insights.get("urgency_triggers", [])) * 0.2, 1.0)
        
        # Emotional driver bonus
        emotional_bonus = emotional_driver.get("confidence", 0.0) * 0.5
        
        final_score = (base_score + social_velocity_score + search_growth_score + 
                      influencer_score + product_potential_score + urgency_score + emotional_bonus)
        
        return min(final_score, 10.0)

    def _generate_seed(self) -> str:
        """Generate a seed trend if none provided"""
        seeds = [
            "vintage gaming aesthetic",
            "minimalist quote designs",
            "retro pixel art",
            "positive vibes quotes",
            "summer aesthetic trends",
            "cozy fall vibes",
            "cyberpunk aesthetic",
            "cottagecore aesthetic",
            "dark academia style",
            "light academia aesthetic"
        ]
        return random.choice(seeds)

    def _generate_mock_trend(self, seed: str) -> Dict[str, Any]:
        """Generate mock trend data as fallback"""
        mock_keywords = [
            seed.replace(" ", "_"),
            "trending",
            "viral",
            "aesthetic",
            "design",
            "style",
            "fashion",
            "trend"
        ]
        
        return {
            "status": "approved",
            "trend_name": seed,
            "keywords": mock_keywords,
            "opportunity_score": 7.5,
            "velocity": "stable",
            "urgency_level": "medium",
            "ethical_status": "approved",
            "confidence_level": 0.75,
            "mcp_model_used": "fallback",
            "google_trends": [],
            "ai_analysis": "Mock analysis - MCP not available"
        }
