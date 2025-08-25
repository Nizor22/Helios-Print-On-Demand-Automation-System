"""
Psychology Integrator Agent

Integrates all 8 sales psychology principles with real discovered data.
No hardcoded psychology patterns - only AI-driven analysis.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional

from helios.services.google_cloud.vertex_ai_client import VertexAIClient

logger = logging.getLogger(__name__)


class PsychologyIntegrator:
    """Integrates psychology principles with real discovered data"""
    
    def __init__(self):
        self.ai_analyzer = VertexAIClient()
        
    async def apply_psychology_principles(self, trend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply all 8 psychology principles to discovered trends"""
        try:
            logger.info(f"Applying psychology principles to {len(trend_data)} trends")
            
            principles = [
                ("emotion_over_logic", self._apply_emotion_over_logic),
                ("trust_building", self._apply_trust_building),
                ("clarity", self._apply_clarity),
                ("visual_simplicity", self._apply_visual_simplicity),
                ("scarcity_urgency", self._apply_scarcity_urgency),
                ("social_proof", self._apply_social_proof),
                ("consistency", self._apply_consistency),
                ("authority", self._apply_authority)
            ]
            
            results = {}
            for principle_name, principle_func in principles:
                try:
                    principle_result = await principle_func(trend_data)
                    results[principle_name] = principle_result
                    logger.info(f"Applied {principle_name} successfully")
                except Exception as e:
                    logger.error(f"Failed to apply {principle_name}: {e}")
                    results[principle_name] = {"error": str(e)}
            
            return results
            
        except Exception as e:
            logger.error(f"Psychology principles application failed: {e}")
            raise RuntimeError(f"Psychology integration failed: {e}")
    
    async def _apply_emotion_over_logic(self, trend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply emotion over logic principle to trend data"""
        try:
            analysis_prompt = f"""
            PSYCHOLOGY PRINCIPLE #1: EMOTION > LOGIC
            
            Analyze these discovered trends to identify emotional drivers and psychological motivations.
            
            Trends: {[t.get('name', 'Unknown') for t in trend_data]}
            
            ANALYSIS REQUIREMENTS:
            1. Identify the PRIMARY EMOTIONAL DRIVER for each trend
            2. Determine the PSYCHOLOGICAL MOTIVATION behind adoption
            3. Find the CORE HUMAN NEED being fulfilled
            4. Identify the IDENTITY STATEMENT each trend represents
            
            EMOTIONAL DRIVER CATEGORIES:
            - DESIRE: Aspiration, luxury, exclusivity, achievement, self-improvement
            - FEAR: Anxiety, protection, security, safety, FOMO
            - PRIDE: Status, recognition, accomplishment, self-worth, belonging
            - NOSTALGIA: Memory, childhood, heritage, comfort, tradition
            - BELONGING: Community, identity, acceptance, connection, social proof
            - EXPRESSION: Creativity, individuality, self-actualization, authenticity
            
            OUTPUT FORMAT:
            For each trend, provide:
            - Trend Name: [name]
            - Primary Emotional Driver: [category from above]
            - Psychological Motivation: [detailed explanation]
            - Core Human Need: [what need is fulfilled]
            - Identity Statement: [what it says about the person]
            - Emotional Intensity: [1-10 scale]
            
            Focus on emotional appeals over logical ones.
            """
            
            response = await self.ai_analyzer.generate_text(
                prompt=analysis_prompt,
                model_type="gemini_flash",
                max_tokens=8192,
                temperature=0.7
            )
            
            return self._parse_emotion_analysis(response.text if hasattr(response, 'text') else str(response))
            
        except Exception as e:
            logger.error(f"Emotion over logic analysis failed: {e}")
            return {"error": str(e)}
    
    async def _apply_trust_building(self, trend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply trust building principle to trend data"""
        try:
            analysis_prompt = f"""
            PSYCHOLOGY PRINCIPLE #2: BUILD TRUST BY UNDERSTANDING NEEDS
            
            Analyze these trends to identify trust-building elements and audience understanding.
            
            Trends: {[t.get('name', 'Unknown') for t in trend_data]}
            
            ANALYSIS REQUIREMENTS:
            1. Identify the TARGET AUDIENCE for each trend
            2. Determine their PAIN POINTS and DESIRES
            3. Find TRUST-BUILDING ELEMENTS
            4. Identify IN-GROUP LANGUAGE and SLANG
            5. Determine CORE IDENTITY STATEMENTS
            6. Find TRUSTED AUTHORITIES within the community
            
            OUTPUT FORMAT:
            For each trend, provide:
            - Trend Name: [name]
            - Target Audience: [demographic and psychographic profile]
            - Pain Points: [what problems they face]
            - Desires: [what they want to achieve]
            - Trust Building Elements: [how to build trust]
            - In-Group Language: [community-specific terms]
            - Core Identity: [what defines this group]
            - Trusted Authorities: [who they look up to]
            
            Focus on understanding the audience deeply to build trust.
            """
            
            response = await self.ai_analyzer.generate_text(
                prompt=analysis_prompt,
                model_type="gemini_flash",
                max_tokens=8192,
                temperature=0.7
            )
            
            return self._parse_trust_analysis(response.text if hasattr(response, 'text') else str(response))
            
        except Exception as e:
            logger.error(f"Trust building analysis failed: {e}")
            return {"error": str(e)}
    
    async def _apply_clarity(self, trend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply clarity principle to trend data"""
        try:
            analysis_prompt = f"""
            PSYCHOLOGY PRINCIPLE #3: CLARITY OVER CLEVERNESS
            
            Analyze these trends to ensure messaging is clear and understandable.
            
            Trends: {[t.get('name', 'Unknown') for t in trend_data]}
            
            ANALYSIS REQUIREMENTS:
            1. Simplify complex trend concepts into clear messages
            2. Identify the CORE VALUE PROPOSITION for each trend
            3. Create CLEAR BENEFIT STATEMENTS
            4. Ensure UNDERSTANDABLE LANGUAGE
            5. Focus on CLARITY over clever wordplay
            
            OUTPUT FORMAT:
            For each trend, provide:
            - Trend Name: [name]
            - Core Value Proposition: [clear, simple statement]
            - Primary Benefit: [what customers get]
            - Secondary Benefits: [additional value]
            - Clear Messaging: [simple, direct language]
            - Avoid Complexity: [what to avoid]
            
            Keep everything clear and simple.
            """
            
            response = await self.ai_analyzer.generate_text(
                prompt=analysis_prompt,
                model_type="gemini_flash",
                max_tokens=8192,
                temperature=0.7
            )
            
            return self._parse_clarity_analysis(response.text if hasattr(response, 'text') else str(response))
            
        except Exception as e:
            logger.error(f"Clarity analysis failed: {e}")
            return {"error": str(e)}
    
    async def _apply_visual_simplicity(self, trend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply visual simplicity principle to trend data"""
        try:
            analysis_prompt = f"""
            PSYCHOLOGY PRINCIPLE #4: VISUAL SIMPLICITY
            
            Analyze these trends for visual design and simplicity requirements.
            
            Trends: {[t.get('name', 'Unknown') for t in trend_data]}
            
            ANALYSIS REQUIREMENTS:
            1. Identify VISUAL ELEMENTS that represent each trend
            2. Determine SIMPLE DESIGN CONCEPTS
            3. Find RECOGNIZABLE PATTERNS
            4. Identify COLOR PALETTES
            5. Determine TYPOGRAPHY STYLES
            6. Focus on SIMPLICITY over complexity
            
            OUTPUT FORMAT:
            For each trend, provide:
            - Trend Name: [name]
            - Visual Elements: [key visual components]
            - Simple Design: [clean, minimal approach]
            - Recognizable Patterns: [what makes it identifiable]
            - Color Palette: [simple color scheme]
            - Typography: [clean, readable fonts]
            - Design Philosophy: [simplicity principles]
            
            Focus on visual simplicity and recognition.
            """
            
            response = await self.ai_analyzer.generate_text(
                prompt=analysis_prompt,
                model_type="gemini_flash",
                max_tokens=8192,
                temperature=0.7
            )
            
            return self._parse_visual_analysis(response.text if hasattr(response, 'text') else str(response))
            
        except Exception as e:
            logger.error(f"Visual simplicity analysis failed: {e}")
            return {"error": str(e)}
    
    async def _apply_scarcity_urgency(self, trend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply scarcity and urgency principle to trend data"""
        try:
            analysis_prompt = f"""
            PSYCHOLOGY PRINCIPLE #5: SCARCITY & URGENCY
            
            Analyze these trends to identify scarcity and urgency opportunities.
            
            Trends: {[t.get('name', 'Unknown') for t in trend_data]}
            
            ANALYSIS REQUIREMENTS:
            1. Identify NATURAL SCARCITY in each trend
            2. Determine URGENCY FACTORS
            3. Find LIMITED AVAILABILITY angles
            4. Identify TIME-SENSITIVE elements
            5. Determine EXCLUSIVITY opportunities
            6. Focus on AUTHENTIC scarcity, not fake urgency
            
            OUTPUT FORMAT:
            For each trend, provide:
            - Trend Name: [name]
            - Natural Scarcity: [what makes it naturally limited]
            - Urgency Factors: [time-sensitive elements]
            - Limited Availability: [supply constraints]
            - Time Sensitivity: [seasonal or trend timing]
            - Exclusivity: [how to make it exclusive]
            - Authentic Approach: [genuine scarcity angles]
            
            Focus on authentic scarcity and urgency.
            """
            
            response = await self.ai_analyzer.generate_text(
                prompt=analysis_prompt,
                model_type="gemini_flash",
                max_tokens=8192,
                temperature=0.7
            )
            
            return self._parse_scarcity_analysis(response.text if hasattr(response, 'text') else str(response))
            
        except Exception as e:
            logger.error(f"Scarcity urgency analysis failed: {e}")
            return {"error": str(e)}
    
    async def _apply_social_proof(self, trend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply social proof principle to trend data"""
        try:
            analysis_prompt = f"""
            PSYCHOLOGY PRINCIPLE #6: SOCIAL PROOF
            
            Analyze these trends to identify social proof opportunities.
            
            Trends: {[t.get('name', 'Unknown') for t in trend_data]}
            
            ANALYSIS REQUIREMENTS:
            1. Identify SOCIAL VALIDATION elements
            2. Determine COMMUNITY SIGNALS
            3. Find INFLUENCER OPPORTUNITIES
            4. Identify USER-GENERATED CONTENT potential
            5. Determine SOCIAL SHARING angles
            6. Focus on AUTHENTIC social proof
            
            OUTPUT FORMAT:
            For each trend, provide:
            - Trend Name: [name]
            - Social Validation: [how it provides belonging]
            - Community Signals: [group membership indicators]
            - Influencer Opportunities: [who can promote it]
            - UGC Potential: [user-generated content ideas]
            - Social Sharing: [viral sharing elements]
            - Authentic Proof: [genuine social validation]
            
            Focus on authentic social proof and community.
            """
            
            response = await self.ai_analyzer.generate_text(
                prompt=analysis_prompt,
                model_type="gemini_flash",
                max_tokens=8192,
                temperature=0.7
            )
            
            return self._parse_social_proof_analysis(response.text if hasattr(response, 'text') else str(response))
            
        except Exception as e:
            logger.error(f"Social proof analysis failed: {e}")
            return {"error": str(e)}
    
    async def _apply_consistency(self, trend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply consistency principle to trend data"""
        try:
            analysis_prompt = f"""
            PSYCHOLOGY PRINCIPLE #7: CONSISTENCY & COMMITMENT
            
            Analyze these trends to identify consistency and commitment opportunities.
            
            Trends: {[t.get('name', 'Unknown') for t in trend_data]}
            
            ANALYSIS REQUIREMENTS:
            1. Identify COLLECTION OPPORTUNITIES
            2. Determine BRAND CONSISTENCY elements
            3. Find COMMITMENT BUILDING strategies
            4. Identify REPEAT PURCHASE angles
            5. Determine LIFESTYLE INTEGRATION
            6. Focus on LONG-TERM engagement
            
            OUTPUT FORMAT:
            For each trend, provide:
            - Trend Name: [name]
            - Collection Strategy: [product line opportunities]
            - Brand Consistency: [unified brand elements]
            - Commitment Building: [how to build loyalty]
            - Repeat Purchase: [ongoing engagement]
            - Lifestyle Integration: [daily life connection]
            - Long-term Strategy: [sustained engagement]
            
            Focus on consistency and long-term commitment.
            """
            
            response = await self.ai_analyzer.generate_text(
                prompt=analysis_prompt,
                model_type="gemini_flash",
                max_tokens=8192,
                temperature=0.7
            )
            
            return self._parse_consistency_analysis(response.text if hasattr(response, 'text') else str(response))
            
        except Exception as e:
            logger.error(f"Consistency analysis failed: {e}")
            return {"error": str(e)}
    
    async def _apply_authority(self, trend_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Apply authority principle to trend data"""
        try:
            analysis_prompt = f"""
            PSYCHOLOGY PRINCIPLE #8: AUTHORITY & SOCIAL PROOF
            
            Analyze these trends to identify authority and credibility opportunities.
            
            Trends: {[t.get('name', 'Unknown') for t in trend_data]}
            
            ANALYSIS REQUIREMENTS:
            1. Identify AUTHORITY FIGURES in each trend
            2. Determine CREDIBILITY BUILDING elements
            3. Find EXPERT ENDORSEMENT opportunities
            4. Identify TRUST SIGNALS
            5. Determine AUTHORITY POSITIONING
            6. Focus on AUTHENTIC authority
            
            OUTPUT FORMAT:
            For each trend, provide:
            - Trend Name: [name]
            - Authority Figures: [who represents this trend]
            - Credibility Elements: [trust-building factors]
            - Expert Endorsements: [who can validate it]
            - Trust Signals: [credibility indicators]
            - Authority Positioning: [how to position as expert]
            - Authentic Authority: [genuine expertise areas]
            
            Focus on authentic authority and credibility.
            """
            
            response = await self.ai_analyzer.generate_text(
                prompt=analysis_prompt,
                model_type="gemini_flash",
                max_tokens=8192,
                temperature=0.7
            )
            
            return self._parse_authority_analysis(response.text if hasattr(response, 'text') else str(response))
            
        except Exception as e:
            logger.error(f"Authority analysis failed: {e}")
            return {"error": str(e)}
    
    # Parse methods for each principle (simplified for brevity)
    def _parse_emotion_analysis(self, response: str) -> Dict[str, Any]:
        """Parse emotion analysis response"""
        return {"analysis": response, "principle": "emotion_over_logic"}
    
    def _parse_trust_analysis(self, response: str) -> Dict[str, Any]:
        """Parse trust analysis response"""
        return {"analysis": response, "principle": "trust_building"}
    
    def _parse_clarity_analysis(self, response: str) -> Dict[str, Any]:
        """Parse clarity analysis response"""
        return {"analysis": response, "principle": "clarity"}
    
    def _parse_visual_analysis(self, response: str) -> Dict[str, Any]:
        """Parse visual analysis response"""
        return {"analysis": response, "principle": "visual_simplicity"}
    
    def _parse_scarcity_analysis(self, response: str) -> Dict[str, Any]:
        """Parse scarcity analysis response"""
        return {"analysis": response, "principle": "scarcity_urgency"}
    
    def _parse_social_proof_analysis(self, response: str) -> Dict[str, Any]:
        """Parse social proof analysis response"""
        return {"analysis": response, "principle": "social_proof"}
    
    def _parse_consistency_analysis(self, response: str) -> Dict[str, Any]:
        """Parse consistency analysis response"""
        return {"analysis": response, "principle": "consistency"}
    
    def _parse_authority_analysis(self, response: str) -> Dict[str, Any]:
        """Parse authority analysis response"""
        return {"analysis": response, "principle": "authority"}
