from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal, Dict, List, Any
from ..config import load_config
# MCPClient removed - using services version instead


@dataclass
class EthicsResult:
    status: Literal["approved", "moderate", "high_risk", "critical"]
    notes: str
    risk_factors: list[str]
    mcp_model_used: str
    execution_time_ms: int


class EthicalGuardianAgent:
    """Advanced ethical guardian agent with continuous learning and adaptive screening."""
    
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
        self.risk_patterns = self._load_risk_patterns()
        self.approval_history = []
        
    def _load_risk_patterns(self) -> Dict[str, List[str]]:
        """Load risk patterns for pattern-based screening"""
        return {
            "high_risk": [
                "offensive", "discriminatory", "violent", "harmful", "dangerous",
                "controversial", "inappropriate", "unethical", "illegal"
            ],
            "moderate_risk": [
                "sensitive", "political", "religious", "cultural", "age_restricted",
                "potentially_controversial", "requires_context"
            ],
            "low_risk": [
                "safe", "appropriate", "benign", "harmless", "innocuous",
                "family_friendly", "professional", "educational"
            ]
        }
    
    async def screen_content(self, content: str, context: Dict[str, Any] = None) -> EthicsResult:
        """Screen content with enhanced ethical analysis"""
        start_time = time.time()
        
        try:
            if self.mcp_client:
                # Use Google MCP ethics_ai for primary screening
                mcp_response = await self.mcp_client.ethics_ai(content, context.get("keywords", []) if context else [])
                
                if "response" in mcp_response and mcp_response["response"]:
                    ai_analysis = mcp_response["response"]
                    model_used = mcp_response.get("model", "gemini-2.0-flash-exp")
                    
                    # Enhanced parsing with pattern matching
                    status, notes, risk_factors = self._enhanced_ethics_parsing(ai_analysis, content, context)
                    
                    execution_time_ms = int((time.time() - start_time) * 1000)
                    
                    # Record decision for learning
                    self._record_decision(content, status, risk_factors, context)
                    
                    return EthicsResult(
                        status=status,
                        notes=notes,
                        risk_factors=risk_factors,
                        mcp_model_used=model_used,
                        execution_time_ms=execution_time_ms
                    )
            
            # Fallback to pattern-based screening
            return self._pattern_based_screening(content, context, start_time)
            
        except Exception as e:
            print(f"Error in ethical guardian screening: {e}")
            return self._pattern_based_screening(content, context, start_time)
    
    def _enhanced_ethics_parsing(self, ai_text: str, content: str, context: Dict[str, Any] = None) -> tuple[str, str, list[str]]:
        """Enhanced parsing with context awareness and pattern matching"""
        status = "approved"
        notes = "AI analysis completed with enhanced screening"
        risk_factors = []
        
        ai_lower = ai_text.lower()
        content_lower = content.lower()
        
        # Check for explicit risk indicators with context
        if any(risk in ai_lower for risk in self.risk_patterns["high_risk"]):
            status = "high_risk"
            notes = "AI identified high-risk content patterns"
            risk_factors = [risk for risk in self.risk_patterns["high_risk"] if risk in ai_lower]
        elif any(risk in ai_lower for risk in self.risk_patterns["moderate_risk"]):
            status = "moderate"
            notes = "AI identified moderate-risk content requiring review"
            risk_factors = [risk for risk in self.risk_patterns["moderate_risk"] if risk in ai_lower]
        else:
            status = "approved"
            notes = "Content passed ethical screening"
            risk_factors = []
        
        # Context-aware adjustments
        if context and context.get("audience_age") == "minors":
            if any(risk in content_lower for risk in ["alcohol", "gambling", "adult_content"]):
                status = "high_risk"
                notes += " - Content inappropriate for minor audience"
                risk_factors.append("minor_audience_inappropriate")
        
        return status, notes, risk_factors
    
    def _pattern_based_screening(self, content: str, context: Dict[str, Any] = None, start_time: float = None) -> EthicsResult:
        """Pattern-based screening as fallback"""
        if start_time is None:
            start_time = time.time()
            
        content_lower = content.lower()
        risk_factors = []
        
        # Check for high-risk patterns
        for risk in self.risk_patterns["high_risk"]:
            if risk in content_lower:
                risk_factors.append(risk)
        
        # Determine status based on risk factors
        if len(risk_factors) > 2:
            status = "high_risk"
        elif len(risk_factors) > 0:
            status = "moderate"
        else:
            status = "approved"
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return EthicsResult(
            status=status,
            notes=f"Pattern-based screening: {status}",
            risk_factors=risk_factors,
            mcp_model_used="pattern_based",
            execution_time_ms=execution_time_ms
        )
    
    def _record_decision(self, content: str, status: str, risk_factors: List[str], context: Dict[str, Any] = None):
        """Record decision for continuous learning"""
        decision_record = {
            "content_preview": content[:100] + "..." if len(content) > 100 else content,
            "status": status,
            "risk_factors": risk_factors,
            "context": context,
            "timestamp": time.time(),
            "model_used": "ethical_guardian"
        }
        
        self.approval_history.append(decision_record)
        
        # Keep only recent history (last 1000 decisions)
        if len(self.approval_history) > 1000:
            self.approval_history = self.approval_history[-1000:]
    
    def get_approval_stats(self) -> Dict[str, Any]:
        """Get approval statistics for monitoring"""
        if not self.approval_history:
            return {"total": 0, "approved": 0, "moderate": 0, "high_risk": 0, "critical": 0}
        
        total = len(self.approval_history)
        approved = len([d for d in self.approval_history if d["status"] == "approved"])
        moderate = len([d for d in self.approval_history if d["status"] == "moderate"])
        high_risk = len([d for d in self.approval_history if d["status"] == "high_risk"])
        critical = len([d for d in self.approval_history if d["status"] == "critical"])
        
        return {
            "total": total,
            "approved": approved,
            "moderate": moderate,
            "high_risk": high_risk,
            "critical": critical,
            "approval_rate": approved / total if total > 0 else 0,
            "risk_rate": (high_risk + critical) / total if total > 0 else 0
        }


async def screen_ethics(trend_name: str, keywords: list[str], dry_run: bool = False) -> EthicsResult:
    """Screen trend for ethical concerns using Google MCP ethics_ai"""
    import time
    start_time = time.time()
    
    if dry_run:
        return EthicsResult(
            status="approved",
            notes="Dry run - ethics screening bypassed",
            risk_factors=[],
            mcp_model_used="dry_run",
            execution_time_ms=0
        )
    
    config = load_config()
    mcp_client = MCPClient.from_env(config.google_mcp_url, config.google_mcp_auth_token)
    
    try:
        if mcp_client:
            # Use Google MCP ethics_ai (Gemini 2.0 Flash for fast ethical analysis)
            mcp_response = await mcp_client.ethics_ai(trend_name, keywords)
            
            if "response" in mcp_response and mcp_response["response"]:
                ai_analysis = mcp_response["response"]
                model_used = mcp_response.get("model", "gemini-2.0-flash-exp")
                
                # Parse AI response for ethical assessment
                status, notes, risk_factors = _parse_ethics_ai_response(ai_analysis, trend_name, keywords)
                
                execution_time_ms = int((time.time() - start_time) * 1000)
                
                return EthicsResult(
                    status=status,
                    notes=notes,
                    risk_factors=risk_factors,
                    mcp_model_used=model_used,
                    execution_time_ms=execution_time_ms
                )
        
        # Fallback to basic screening if MCP not available
        return _basic_ethics_screening(trend_name, keywords, start_time)
        
    except Exception as e:
        print(f"Error in ethics screening: {e}")
        return _basic_ethics_screening(trend_name, keywords, start_time)


def _parse_ethics_ai_response(ai_text: str, trend_name: str, keywords: list[str]) -> tuple[str, str, list[str]]:
    """Parse AI response for ethical assessment"""
    # Default values
    status = "approved"
    notes = "AI analysis completed"
    risk_factors = []
    
    # Simple parsing - in production you'd want more sophisticated NLP
    ai_lower = ai_text.lower()
    
    # Check for explicit approval indicators first
    approval_indicators = [
        "approved", "safe", "appropriate", "ethical", "acceptable", 
        "no concerns", "no risks", "low risk", "minimal risk",
        "suitable", "benign", "harmless", "innocuous"
    ]
    
    # Check for explicit risk indicators
    risk_indicators = [
        "offensive", "inappropriate", "controversial", "harmful", 
        "discriminatory", "violent", "dangerous", "risky",
        "concerning", "problematic", "unethical", "inappropriate"
    ]
    
    # Check for negation patterns (e.g., "not offensive", "no harmful content")
    negation_patterns = [
        "not offensive", "not harmful", "not inappropriate", "not controversial",
        "no offensive", "no harmful", "no inappropriate", "no controversial",
        "doesn't contain", "does not contain", "free of", "lacks"
    ]
    
    # Check if AI explicitly approves
    if any(indicator in ai_lower for indicator in approval_indicators):
        status = "approved"
        notes = "AI explicitly approved this trend as safe and appropriate"
        risk_factors = []
    # Check if AI explicitly identifies risks
    elif any(indicator in ai_lower for indicator in risk_indicators):
        # But first check for negations
        has_negation = any(negation in ai_lower for negation in negation_patterns)
        
        if has_negation:
            status = "approved"
            notes = "AI found no significant ethical concerns"
            risk_factors = []
        else:
            status = "high_risk"
            detected_risks = [indicator for indicator in risk_indicators if indicator in ai_lower]
            risk_factors = detected_risks[:3]  # Limit to top 3
            notes = f"AI detected potential risk factors: {', '.join(risk_factors)}"
    else:
        # Default to approved if no clear indicators
        status = "approved"
        notes = "AI analysis found no significant ethical concerns"
        risk_factors = []
    
    return status, notes, risk_factors


def _basic_ethics_screening(trend_name: str, keywords: list[str], start_time: float) -> EthicsResult:
    """Basic ethical screening as fallback"""
    import time
    
    # Simple keyword-based screening
    risk_keywords = ["offensive", "inappropriate", "controversial", "harmful"]
    trend_lower = trend_name.lower()
    keywords_lower = [k.lower() for k in keywords]
    
    all_text = f"{trend_lower} {' '.join(keywords_lower)}"
    
    risk_factors = []
    for risk_word in risk_keywords:
        if risk_word in all_text:
            risk_factors.append(risk_word)
    
    if risk_factors:
        status = "high_risk"
        notes = f"Basic screening detected risk factors: {', '.join(risk_factors)}"
    else:
        status = "approved"
        notes = "Basic screening completed - no obvious risks detected"
    
    execution_time_ms = int((time.time() - start_time) * 1000)
    
    return EthicsResult(
        status=status,
        notes=notes,
        risk_factors=risk_factors,
        mcp_model_used="fallback",
        execution_time_ms=execution_time_ms
    )
