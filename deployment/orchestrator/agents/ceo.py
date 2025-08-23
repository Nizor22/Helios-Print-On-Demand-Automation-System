from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import os
from ..config import load_config
from ..services.mcp_integration.mcp_client import GoogleMCPClient
try:
    import google.generativeai as genai
except Exception:
    genai = None


class Priority(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class QualityGateStatus(Enum):
    PASSED = "passed"
    FAILED = "failed"
    PENDING = "pending"


@dataclass
class QualityGateResult:
    gate_name: str
    status: QualityGateStatus
    score: float
    threshold: float
    details: str
    execution_time_ms: int


@dataclass
class TrendDecision:
    approved: bool
    trend_name: str
    keywords: List[str]
    opportunity_score: float
    velocity: str
    urgency_level: str
    ethical_status: str
    confidence_level: float
    mcp_model_used: str
    execution_time_ms: int
    priority: Priority
    quality_gates: Dict[str, QualityGateResult]
    optimization_recommendations: List[str]
    reasoning: str = ""  # Added missing reasoning attribute


class HeliosCEO:
    """Enhanced Priority Controller implementing decision framework with quality gates and parallel processing."""

    def __init__(self, min_opportunity: float = 7.0, min_confidence: float = 0.7):
        self.min_opportunity = min_opportunity
        self.min_confidence = min_confidence
        cfg = load_config()
        
        # Load configuration
        self.config = cfg
        self.min_opportunity_score = cfg.min_opportunity_score
        self.min_audience_confidence = cfg.min_audience_confidence
        self.min_profit_margin = cfg.min_profit_margin
        self.max_execution_time = cfg.max_execution_time
        
        # Quality gate thresholds
        self.quality_gates = {
            "ethical_approval": {"required": True, "threshold": 1.0},
            "audience_confidence": {"required": True, "threshold": self.min_audience_confidence},
            "trend_opportunity": {"required": True, "threshold": self.min_opportunity_score},
            "profit_margin": {"required": False, "threshold": self.min_profit_margin},
            "design_audience_alignment": {"required": False, "threshold": 8.0}
        }
        
        # Priority framework
        self.priority_framework = {
            Priority.HIGH: ["trend_discovery", "ethical_screening"],
            Priority.MEDIUM: ["audience_analysis", "product_strategy"],
            Priority.LOW: ["creative_execution", "publication"]
        }
        
        # Initialize Google MCP client if configured
        self.mcp_client = GoogleMCPClient(cfg.google_mcp_url, cfg.google_mcp_auth_token) if cfg.google_mcp_url else None
        
        # Fallback to direct Gemini if MCP not available
        self.gemini_key = cfg.google_api_key
        self.gemini_model_name = cfg.gemini_model or "gemini-2.0-flash-exp"
        if genai and self.gemini_key and not self.mcp_client:
            genai.configure(api_key=self.gemini_key)
            try:
                self.model = genai.GenerativeModel(self.gemini_model_name)
            except Exception:
                self.model = None
        else:
            self.model = None

    async def validate_trend(self, zeitgeist_payload: Dict[str, Any]) -> TrendDecision:
        """Validate trend using enhanced quality gates and priority framework"""
        start_time = time.time()
        
        # Extract trend data
        status = str(zeitgeist_payload.get("status", "rejected"))
        trend_name = str(zeitgeist_payload.get("trend_name", "unspecified_trend"))
        keywords = list(zeitgeist_payload.get("keywords", []))
        opportunity_score = float(zeitgeist_payload.get("opportunity_score", 0))
        confidence_level = float(zeitgeist_payload.get("confidence_level", 0))
        ethical_status = str(zeitgeist_payload.get("ethical_status", "approved"))
        velocity = str(zeitgeist_payload.get("velocity", "stable"))
        urgency_level = str(zeitgeist_payload.get("urgency_level", "monitor"))
        
        # Determine priority based on urgency and opportunity
        priority = self._determine_priority(urgency_level, opportunity_score, velocity)
        
        # Run quality gates
        quality_gates = await self._run_quality_gates(zeitgeist_payload)
        
        # Check if all required quality gates passed
        required_gates = [gate for gate, config in self.quality_gates.items() if config["required"]]
        all_required_passed = all(
            quality_gates[gate].status == QualityGateStatus.PASSED 
            for gate in required_gates 
            if gate in quality_gates
        )
        
        # Final approval decision
        approved = all_required_passed
        
        # Generate optimization recommendations
        optimization_recommendations = self._generate_optimization_recommendations(
            quality_gates, zeitgeist_payload, priority
        )
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Generate reasoning based on quality gate results
        reasoning_parts = []
        if approved:
            reasoning_parts.append(f"Approved: All required quality gates passed.")
        else:
            failed_gates = [gate for gate, result in quality_gates.items() 
                          if result.status == QualityGateStatus.FAILED and self.quality_gates.get(gate, {}).get("required")]
            reasoning_parts.append(f"Rejected: Failed required gates: {', '.join(failed_gates)}")
        
        reasoning_parts.append(f"Opportunity score: {opportunity_score:.2f} (threshold: {self.min_opportunity_score})")
        reasoning_parts.append(f"Confidence: {confidence_level:.2f} (threshold: {self.min_audience_confidence})")
        reasoning = " ".join(reasoning_parts)
        
        return TrendDecision(
            approved=approved,
            trend_name=trend_name,
            keywords=keywords,
            opportunity_score=opportunity_score,
            velocity=velocity,
            urgency_level=urgency_level,
            ethical_status=ethical_status,
            confidence_level=confidence_level,
            mcp_model_used=zeitgeist_payload.get("mcp_model_used", "none"),
            execution_time_ms=execution_time_ms,
            priority=priority,
            quality_gates=quality_gates,
            optimization_recommendations=optimization_recommendations,
            reasoning=reasoning
        )

    async def prepare_validation(self) -> Dict[str, Any]:
        """Prepare CEO agent for validation (pre-load models, warm up connections)"""
        start_time = time.time()
        
        # Pre-load quality gate configurations
        quality_gate_configs = {}
        for gate_name, config in self.quality_gates.items():
            quality_gate_configs[gate_name] = {
                "required": config["required"],
                "threshold": config["threshold"],
                "status": "ready"
            }
        
        # Pre-warm MCP connections if available
        mcp_status = "ready"
        if self.mcp_client:
            try:
                # Test MCP connection
                await self.mcp_client.call("health_check", {}, timeout_s=5.0)
                mcp_status = "connected"
            except Exception:
                mcp_status = "disconnected"
        
        # Pre-load Gemini model if available
        gemini_status = "ready"
        if self.model:
            try:
                # Test model with simple prompt
                response = await self._test_gemini_model()
                gemini_status = "loaded"
            except Exception:
                gemini_status = "error"
        
        preparation_time_ms = int((time.time() - start_time) * 1000)
        
        return {
            "status": "ready",
            "quality_gates": quality_gate_configs,
            "mcp_status": mcp_status,
            "gemini_status": gemini_status,
            "preparation_time_ms": preparation_time_ms,
            "priority_framework": self.priority_framework
        }

    async def _test_gemini_model(self) -> str:
        """Test Gemini model with simple prompt"""
        if not self.model:
            return "Model not available"
        
        try:
            response = self.model.generate_content("Test")
            return response.text if response.text else "Model responded"
        except Exception as e:
            return f"Model error: {str(e)}"

    def _determine_priority(self, urgency_level: str, opportunity_score: float, velocity: str) -> Priority:
        """Determine priority based on urgency, opportunity score, and velocity"""
        if urgency_level == "high" and opportunity_score >= 8.0:
            return Priority.HIGH
        elif urgency_level == "high" or opportunity_score >= 7.5 or velocity == "accelerating":
            return Priority.MEDIUM
        else:
            return Priority.LOW

    async def _run_quality_gates(self, zeitgeist_payload: Dict[str, Any]) -> Dict[str, QualityGateResult]:
        """Run all quality gates in parallel for efficiency"""
        gates_to_run = []
        
        for gate_name, gate_config in self.quality_gates.items():
            if gate_name == "ethical_approval":
                gates_to_run.append(self._run_ethical_gate(zeitgeist_payload))
            elif gate_name == "audience_confidence":
                gates_to_run.append(self._run_audience_confidence_gate(zeitgeist_payload))
            elif gate_name == "trend_opportunity":
                gates_to_run.append(self._run_trend_opportunity_gate(zeitgeist_payload))
            elif gate_name == "profit_margin":
                gates_to_run.append(self._run_profit_margin_gate(zeitgeist_payload))
            elif gate_name == "design_audience_alignment":
                gates_to_run.append(self._run_design_alignment_gate(zeitgeist_payload))
        
        # Run gates in parallel if enabled
        if self.config.enable_parallel_processing:
            results = await asyncio.gather(*gates_to_run, return_exceptions=True)
        else:
            results = []
            for gate in gates_to_run:
                try:
                    result = await gate
                    results.append(result)
                except Exception as e:
                    results.append(self._create_failed_gate_result(gate_name, str(e)))
        
        # Compile results
        quality_gates = {}
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                gate_name = list(self.quality_gates.keys())[i]
                quality_gates[gate_name] = self._create_failed_gate_result(gate_name, str(result))
            else:
                quality_gates[result.gate_name] = result
        
        return quality_gates

    async def _run_ethical_gate(self, zeitgeist_payload: Dict[str, Any]) -> QualityGateResult:
        """Run ethical approval quality gate"""
        start_time = time.time()
        
        ethical_status = zeitgeist_payload.get("ethical_status", "pending")
        status = QualityGateStatus.PASSED if ethical_status == "approved" else QualityGateStatus.FAILED
        score = 1.0 if status == QualityGateStatus.PASSED else 0.0
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return QualityGateResult(
            gate_name="ethical_approval",
            status=status,
            score=score,
            threshold=1.0,
            details=f"Ethical status: {ethical_status}",
            execution_time_ms=execution_time_ms
        )

    async def _run_audience_confidence_gate(self, zeitgeist_payload: Dict[str, Any]) -> QualityGateResult:
        """Run audience confidence quality gate"""
        start_time = time.time()
        
        confidence = float(zeitgeist_payload.get("confidence_level", 0))
        threshold = self.quality_gates["audience_confidence"]["threshold"]
        status = QualityGateStatus.PASSED if confidence >= threshold else QualityGateStatus.FAILED
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return QualityGateResult(
            gate_name="audience_confidence",
            status=status,
            score=confidence,
            threshold=threshold,
            details=f"Confidence: {confidence:.2f}/{threshold}",
            execution_time_ms=execution_time_ms
        )

    async def _run_trend_opportunity_gate(self, zeitgeist_payload: Dict[str, Any]) -> QualityGateResult:
        """Run trend opportunity quality gate"""
        start_time = time.time()
        
        opportunity = float(zeitgeist_payload.get("opportunity_score", 0))
        threshold = self.quality_gates["trend_opportunity"]["threshold"]
        status = QualityGateStatus.PASSED if opportunity >= threshold else QualityGateStatus.FAILED
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return QualityGateResult(
            gate_name="trend_opportunity",
            status=status,
            score=opportunity,
            threshold=threshold,
            details=f"Opportunity: {opportunity:.1f}/{threshold}",
            execution_time_ms=execution_time_ms
        )

    async def _run_profit_margin_gate(self, zeitgeist_payload: Dict[str, Any]) -> QualityGateResult:
        """Run profit margin quality gate (optional)"""
        start_time = time.time()
        
        # This would typically come from product strategy analysis
        # For now, we'll use a default value
        profit_margin = 0.4  # Default 40% margin
        threshold = self.quality_gates["profit_margin"]["threshold"]
        status = QualityGateStatus.PASSED if profit_margin >= threshold else QualityGateStatus.FAILED
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return QualityGateResult(
            gate_name="profit_margin",
            status=status,
            score=profit_margin,
            threshold=threshold,
            details=f"Profit margin: {profit_margin:.1%}/{threshold:.1%}",
            execution_time_ms=execution_time_ms
        )

    async def _run_design_alignment_gate(self, zeitgeist_payload: Dict[str, Any]) -> QualityGateResult:
        """Run design-audience alignment quality gate (optional)"""
        start_time = time.time()
        
        # This would typically come from creative execution analysis
        # For now, we'll use a default value based on psychological insights
        psychological_insights = zeitgeist_payload.get("psychological_insights", {})
        identity_statements = len(psychological_insights.get("identity_statements", []))
        authority_figures = len(psychological_insights.get("authority_figures", []))
        
        # Calculate alignment score based on psychological factors
        alignment_score = min(10.0, 6.0 + (identity_statements * 0.5) + (authority_figures * 0.3))
        threshold = self.quality_gates["design_audience_alignment"]["threshold"]
        status = QualityGateStatus.PASSED if alignment_score >= threshold else QualityGateStatus.FAILED
        
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        return QualityGateResult(
            gate_name="design_audience_alignment",
            status=status,
            score=alignment_score,
            threshold=threshold,
            details=f"Alignment: {alignment_score:.1f}/{threshold} (identity: {identity_statements}, authority: {authority_figures})",
            execution_time_ms=execution_time_ms
        )

    def _create_failed_gate_result(self, gate_name: str, error: str) -> QualityGateResult:
        """Create a failed quality gate result for error handling"""
        return QualityGateResult(
            gate_name=gate_name,
            status=QualityGateStatus.FAILED,
            score=0.0,
            threshold=self.quality_gates[gate_name]["threshold"],
            details=f"Gate failed: {error}",
            execution_time_ms=0
        )

    def _generate_optimization_recommendations(self, quality_gates: Dict[str, QualityGateResult], 
                                            zeitgeist_payload: Dict[str, Any], priority: Priority) -> List[str]:
        """Generate optimization recommendations based on quality gate results"""
        recommendations = []
        
        # Priority-based recommendations
        if priority == Priority.HIGH:
            recommendations.append("High priority trend - allocate maximum resources")
            recommendations.append("Consider parallel processing for all stages")
        elif priority == Priority.MEDIUM:
            recommendations.append("Medium priority - standard resource allocation")
        else:
            recommendations.append("Low priority - minimal resource allocation")
        
        # Quality gate specific recommendations
        for gate_name, result in quality_gates.items():
            if result.status == QualityGateStatus.FAILED:
                if gate_name == "audience_confidence":
                    recommendations.append("Increase audience research depth")
                elif gate_name == "trend_opportunity":
                    recommendations.append("Re-evaluate trend timing and market conditions")
                elif gate_name == "profit_margin":
                    recommendations.append("Optimize pricing strategy and costs")
                elif gate_name == "design_audience_alignment":
                    recommendations.append("Enhance psychological marketing framework")
        
        # Performance optimization recommendations
        if zeitgeist_payload.get("execution_time_ms", 0) > 60000:  # > 60 seconds
            recommendations.append("Consider enabling parallel processing for faster execution")
        
        return recommendations

    async def batch_validate_trends(self, trends: List[Dict[str, Any]]) -> List[TrendDecision]:
        """Validate multiple trends in parallel using enhanced quality gates"""
        if self.config.enable_parallel_processing:
            tasks = [self.validate_trend(trend) for trend in trends]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    print(f"Trend validation failed for trend {i}: {result}")
                    # Create a default rejected decision
                    trend = trends[i]
                    processed_results.append(TrendDecision(
                        approved=False,
                        trend_name=str(trend.get("trend_name", "error")),
                        keywords=list(trend.get("keywords", [])),
                        opportunity_score=0.0,
                        velocity="unknown",
                        urgency_level="unknown",
                        ethical_status="error",
                        confidence_level=0.0,
                        mcp_model_used="error",
                        execution_time_ms=0,
                        priority=Priority.LOW,
                        quality_gates={},
                        optimization_recommendations=["Error in validation"]
                    ))
                else:
                    processed_results.append(result)
            
            return processed_results
        else:
            # Sequential processing
            results = []
            for trend in trends:
                result = await self.validate_trend(trend)
                results.append(result)
            return results

    async def coordinate_parallel_execution(self, stage: str, agents: List[str]) -> Dict[str, Any]:
        """Coordinate parallel execution for specific stages"""
        if not self.config.enable_parallel_processing:
            return {"status": "sequential", "reason": "Parallel processing disabled"}
        
        if stage not in ["analysis", "creation", "publication"]:
            return {"status": "error", "reason": f"Unknown stage: {stage}"}
        
        # Stage-specific coordination logic
        if stage == "analysis":
            return await self._coordinate_analysis_stage(agents)
        elif stage == "creation":
            return await self._coordinate_creation_stage(agents)
        elif stage == "publication":
            return await self._coordinate_publication_stage(agents)
        
        return {"status": "unknown", "reason": "Stage not implemented"}

    async def _coordinate_analysis_stage(self, agents: List[str]) -> Dict[str, Any]:
        """Coordinate parallel execution for analysis stage"""
        return {
            "status": "parallel",
            "stage": "analysis",
            "agents": agents,
            "execution_model": "parallel_processing",
            "estimated_time": "45 seconds",
            "coordination_strategy": "Independent execution with shared data"
        }

    async def _coordinate_creation_stage(self, agents: List[str]) -> Dict[str, Any]:
        """Coordinate parallel execution for creation stage"""
        return {
            "status": "parallel",
            "stage": "creation",
            "agents": agents,
            "execution_model": "batch_processing",
            "estimated_time": "90 seconds",
            "coordination_strategy": "Batch creation with shared creative assets"
        }

    async def _coordinate_publication_stage(self, agents: List[str]) -> Dict[str, Any]:
        """Coordinate parallel execution for publication stage"""
        return {
            "status": "parallel",
            "stage": "publication",
            "agents": agents,
            "execution_model": "automated_with_error_handling",
            "estimated_time": "30 seconds",
            "coordination_strategy": "Automated publishing with retry logic"
        }
