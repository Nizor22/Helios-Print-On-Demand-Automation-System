"""
Hybrid AI Base Class for Helios AI Agents

Implements the 3-layer prompt architecture and cost-optimized model selection strategy.
Combines AI reasoning with deterministic business rules for accuracy and consistency.
"""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging

from ..config import HeliosConfig


class AIModelType(Enum):
    """AI Model types for cost-optimized selection"""
    GEMINI_2_5_FLASH_THINKING = "gemini-2.5-flash-thinking"
    GEMINI_2_5_FLASH_LITE = "gemini-2.5-flash-lite"
    GEMINI_2_0_FLASH_LITE = "gemini-2.0-flash-lite"


class TaskComplexity(Enum):
    """Task complexity levels for model selection"""
    BASIC = 1      # Simple data processing, basic analysis
    STANDARD = 5   # Standard operations, content generation
    STRATEGIC = 8  # Complex analysis, strategic decisions
    CRITICAL = 10  # Critical business decisions, high-stakes analysis


@dataclass
class HybridPrompt:
    """3-layer prompt structure for hybrid AI agents"""
    system_prompt: str      # Core identity and capabilities
    description_prompt: str # Current task and context
    user_agent_prompt: str  # Specific request with data


class BaseResult:
    """Base class for all result objects to provide consistent interface"""
    
    def __init__(self, data: Dict = None):
        self.data = data or {}
    
    def get(self, key: str, default=None):
        """Provide .get() method for consistent interface access"""
        return self.data.get(key, default)
    
    def __getattr__(self, name):
        """Allow attribute access to data keys"""
        if name in self.data:
            return self.data[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")


@dataclass
class HybridResult(BaseResult):
    """Result from hybrid AI processing"""
    
    def __init__(self, task: Dict[str, Any], confidence_score: float, execution_time_ms: int, 
                 usage_metadata: Dict[str, Any], ai_analysis: Any, model_used: str, 
                 quality_gates: Dict[str, Any] = None):
        # Initialize the data dictionary
        data = {
            "task": task,
            "confidence_score": confidence_score,
            "execution_time_ms": execution_time_ms,
            "usage_metadata": usage_metadata,
            "ai_analysis": ai_analysis,
            "model_used": model_used,
            "quality_gates": quality_gates or {}
        }
        super().__init__(data)
    
    @property
    def cost_metrics(self) -> Dict[str, float]:
        """Calculate cost metrics from usage metadata"""
        total_tokens = self.data.get('usage_metadata', {}).get('total_tokens', 0)
        thinking_tokens = self.data.get('usage_metadata', {}).get('thinking_tokens', 0)
        
        # Estimate costs based on token usage
        # These would be actual costs in production
        estimated_cost = {
            'total_cost': total_tokens * 0.000001,  # $0.000001 per token
            'thinking_cost': thinking_tokens * 0.000002,  # $0.000002 per thinking token
            'total_tokens': total_tokens,
            'thinking_tokens': thinking_tokens
        }
        
        return estimated_cost
    
    @property
    def ai_analysis(self) -> Any:
        """Get the AI analysis data"""
        return self.data.get('ai_analysis', {})
    
    @property
    def trends(self) -> List[str]:
        """Get trends from AI analysis data"""
        ai_data = self.data.get('ai_analysis', {})
        if isinstance(ai_data, dict):
            return ai_data.get('trends', [])
        elif hasattr(ai_data, 'trends'):
            return ai_data.trends
        return []
    
    @property
    def emotional_drivers(self) -> Dict[str, Any]:
        """Get emotional drivers from AI analysis data"""
        ai_data = self.data.get('ai_analysis', {})
        if isinstance(ai_data, dict):
            return ai_data.get('emotional_drivers', {})
        elif hasattr(ai_data, 'emotional_drivers'):
            return ai_data.emotional_drivers
        return {}
    
    @property
    def usage_metadata(self) -> Dict[str, Any]:
        """Get the usage metadata"""
        return self.data.get('usage_metadata', {})


class FallbackResultBase(BaseResult):
    """Base class for fallback result objects to provide consistent interface"""
    
    def __init__(self, data: Dict[str, Any] = None):
        super().__init__(data)


class FallbackTrendResult(FallbackResultBase):
    """Fallback trend result with consistent interface"""
    
    def __init__(self, task: Dict[str, Any]):
        # Create structured data for the fallback result
        data = {
            "trend_name": task.get("seed", "unknown"),
            "opportunity_score": 6.0,
            "emotional_driver": {
                "primary_emotion": "desire",
                "psychological_motivation": "Basic trend following",
                "identity_statement": f"I am someone who follows {task.get('seed', 'unknown')} trends",
                "social_validation": f"Join the {task.get('seed', 'unknown')} trend",
                "confidence": 0.5,
                "source": "fallback"
            },
            "keywords": [task.get("seed", "unknown"), "trending", "viral"],
            "mcp_model_used": "fallback",
            "confidence_score": 6.0,
            "execution_time_ms": 100
        }
        super().__init__(data)


class FallbackAudienceResult(FallbackResultBase):
    """Fallback audience result with consistent interface"""
    
    def __init__(self, task: Dict[str, Any]):
        # Create structured data for the fallback result
        data = {
            "primary_persona": {
                "demographic_cluster": "general",
                "age_range": "25-45",
                "location_preference": "Urban/Suburban",
                "income_level": "$35-75_considered"
            },
            "in_group_language": ["authentic", "quality", "community"],
            "core_identity_statements": [
                "I am someone who values quality",
                "I am part of a community"
            ],
            "trusted_authorities": [
                "Quality brands",
                "Community leaders"
            ],
            "trust_building_elements": [
                "Quality assurance",
                "Community validation"
            ],
            "model_used": "fallback",
            "confidence_score": 7.0,
            "execution_time_ms": 100
        }
        super().__init__(data)


class ProductStrategyResult(BaseResult):
    """Product strategy result with consistent interface"""
    
    def __init__(self, task: Dict[str, Any]):
        # Create structured data for product strategy
        data = {
            "psychological_positioning": {
                "identity_enhancement": "Enhance customer identity through product",
                "emotional_triggers": ["belonging", "achievement", "expression"],
                "social_proof_elements": ["Community membership", "Social validation"]
            },
            "collection_strategy": {
                "collection_theme": "Identity Collection",
                "cross_promotion": "Bundle related products",
                "repeat_purchase": "Encourage collection completion"
            },
            "product_recommendations": [
                "Core identity product",
                "Supporting accessories",
                "Collection expansion items"
            ],
            "model_used": "fallback",
            "confidence_score": 8.0,
            "execution_time_ms": 150
        }
        super().__init__(data)


class CreativeStrategyResult(BaseResult):
    """Creative strategy result with consistent interface"""
    
    def __init__(self, task: Dict[str, Any]):
        # Create structured data for creative strategy
        data = {
            "design_concepts": [
                {
                    "design_id": "concept_1",
                    "design_name": "Identity Design",
                    "visual_prompt": "Simple, authentic design representing identity",
                    "emotional_appeal": "Principle #1: Identity enhancement",
                    "identity_statement": "Shows your authentic self",
                    "social_proof_elements": ["Community membership"],
                    "scarcity_angle": "Limited Edition",
                    "confidence_score": 8.5
                }
            ],
            "copy_elements": {
                "title_hooks": ["Express Your Identity"],
                "emotional_leads": ["Show the world who you are"],
                "benefit_copy": ["Join a community of like-minded individuals"],
                "social_proof_elements": ["Trusted by thousands"],
                "ugc_encouragement": ["Share your story!"],
                "authority_positioning": ["Recognized by community leaders"]
            },
            "marketing_angles": {
                "scarcity_angles": ["Limited Edition"],
                "urgency_elements": ["Get it while it lasts!"],
                "collection_strategy": "Identity Collection"
            },
            "model_used": "fallback",
            "confidence_score": 8.5,
            "execution_time_ms": 200
        }
        super().__init__(data)


class CopyStrategyResult(BaseResult):
    """Copy strategy result with consistent interface"""
    
    def __init__(self, task: Dict[str, Any]):
        # Create structured data for copy strategy
        data = {
            "copy_elements": {
                "title_hooks": ["Join Your Community"],
                "emotional_leads": ["Become part of something bigger"],
                "benefit_copy": ["Connect with like-minded individuals"],
                "social_proof_elements": ["Join thousands of members"],
                "ugc_encouragement": ["Share your community pride!"],
                "authority_positioning": ["Trusted by community leaders"]
            },
            "messaging_framework": {
                "primary_message": "Community and belonging",
                "target_audience": "Community seekers",
                "tone": "Authentic and engaging",
                "key_messaging": [
                    "Lead with emotional connection",
                    "Build trust through authenticity",
                    "Include social proof elements"
                ]
            },
            "psychological_triggers": {
                "emotional_triggers": ["belonging", "community"],
                "cognitive_biases": ["social_proof", "authority"],
                "conversion_elements": ["community_membership", "social_validation"]
            },
            "conversion_optimization": {
                "urgency_elements": ["Limited time", "Exclusive access"],
                "social_proof": ["Community membership", "Customer testimonials"],
                "psychological_hooks": ["Community belonging", "Identity enhancement"]
            },
            "model_used": "fallback",
            "confidence_score": 8.0,
            "execution_time_ms": 120
        }
        super().__init__(data)


class TokenBudgetManager:
    """Manages token budgets for cost optimization"""
    
    def __init__(self, config: HeliosConfig):
        self.config = config
        self.daily_budgets = {
            AIModelType.GEMINI_2_5_FLASH_THINKING: config.ceo_thinking_budget,
            AIModelType.GEMINI_2_5_FLASH_LITE: 1000000,  # 1M tokens/day
            AIModelType.GEMINI_2_0_FLASH_LITE: 2000000   # 2M tokens/day
        }
        self.current_usage = {model: 0 for model in AIModelType}
        self.daily_reset_time = time.time()
    
    def select_model(self, task_complexity: int, thinking_required: bool = False) -> AIModelType:
        """Smart model selection based on budget and complexity"""
        # Reset daily usage if 24 hours have passed
        if time.time() - self.daily_reset_time > 86400:
            self.current_usage = {model: 0 for model in AIModelType}
            self.daily_reset_time = time.time()
        
        if thinking_required and task_complexity >= 8 and self._has_budget(AIModelType.GEMINI_2_5_FLASH_THINKING):
            return AIModelType.GEMINI_2_5_FLASH_THINKING
        elif task_complexity >= 5 and self._has_budget(AIModelType.GEMINI_2_5_FLASH_LITE):
            return AIModelType.GEMINI_2_5_FLASH_LITE
        else:
            return AIModelType.GEMINI_2_0_FLASH_LITE
    
    def _has_budget(self, model: AIModelType) -> bool:
        """Check if model has remaining daily budget"""
        current = self.current_usage.get(model, 0)
        limit = self.daily_budgets.get(model, 0)
        return current < limit * 0.9  # 90% threshold
    
    def record_usage(self, model: AIModelType, tokens_used: int):
        """Record token usage for budget tracking"""
        self.current_usage[model] = self.current_usage.get(model, 0) + tokens_used


class BusinessRulesEngine:
    """Validates AI outputs against business rules"""
    
    def __init__(self, config: HeliosConfig):
        self.config = config
        self.rules = self._initialize_rules()
    
    def _initialize_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize business rules for validation"""
        return {
            "trend_validation": {
                "min_opportunity_score": self.config.min_opportunity_score,
                "min_audience_confidence": self.config.min_audience_confidence,
                "min_profit_margin": self.config.min_profit_margin
            },
            "content_safety": {
                "ethical_standards": True,
                "copyright_compliance": True,
                "platform_policies": True
            },
            "quality_standards": {
                "min_confidence_score": 7.0,
                "max_execution_time": self.config.max_execution_time
            }
        }
    
    def validate(self, ai_result: Any, rule_set: str) -> Dict[str, Any]:
        """Validate AI result against specified business rules"""
        rules = self.rules.get(rule_set, {})
        validation_result = {"passed": True, "violations": [], "score": 0.0}
        
        if rule_set == "trend_validation":
            validation_result = self._validate_trend_data(ai_result, rules)
        elif rule_set == "content_safety":
            validation_result = self._validate_content_safety(ai_result, rules)
        elif rule_set == "quality_standards":
            validation_result = self._validate_quality_standards(ai_result, rules)
        
        return validation_result
    
    def _validate_trend_data(self, trend_data: Dict, rules: Dict) -> Dict[str, Any]:
        """Validate trend data against business rules"""
        violations = []
        score = 0.0
        
        # Check opportunity score
        if trend_data.get("opportunity_score", 0) < rules.get("min_opportunity_score", 5.0):
            violations.append(f"Opportunity score {trend_data.get('opportunity_score')} below minimum {rules['min_opportunity_score']}")
        
        # Check audience confidence
        if trend_data.get("confidence_level", 0) < rules.get("min_audience_confidence", 0.7):
            violations.append(f"Confidence level {trend_data.get('confidence_level')} below minimum {rules['min_audience_confidence']}")
        
        # Calculate validation score
        score = max(0.0, 10.0 - len(violations) * 2.0)
        
        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "score": score
        }
    
    def _validate_content_safety(self, content: Dict, rules: Dict) -> Dict[str, Any]:
        """Validate content against safety rules"""
        violations = []
        score = 10.0
        
        # Basic content safety checks (implement based on your requirements)
        if content.get("ethical_status") != "approved":
            violations.append("Content failed ethical screening")
            score -= 5.0
        
        if content.get("copyright_status") != "clear":
            violations.append("Copyright status unclear")
            score -= 3.0
        
        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "score": max(0.0, score)
        }
    
    def _validate_quality_standards(self, result: Dict, rules: Dict) -> Dict[str, Any]:
        """Validate result against quality standards"""
        violations = []
        score = 10.0
        
        # Check confidence score
        if result.get("confidence_score", 0) < rules.get("min_confidence_score", 7.0):
            violations.append(f"Confidence score {result.get('confidence_score')} below minimum {rules['min_confidence_score']}")
            score -= 3.0
        
        # Check execution time
        if result.get("execution_time_ms", 0) > rules.get("max_execution_time", 300) * 1000:
            violations.append(f"Execution time {result.get('execution_time_ms')}ms exceeds maximum {rules['max_execution_time']}s")
            score -= 2.0
        
        return {
            "passed": len(violations) == 0,
            "violations": violations,
            "score": max(0.0, score)
        }


class HybridAIBase(ABC):
    """Base class for hybrid AI agents combining AI reasoning with business rules"""
    
    def __init__(self, config: HeliosConfig, agent_type: str):
        self.config = config
        self.agent_type = agent_type
        self.token_budget_manager = TokenBudgetManager(config)
        self.rules_engine = BusinessRulesEngine(config)
        self.logger = logging.getLogger(f"helios.hybrid_ai.{agent_type}")
        
        # Initialize AI model based on agent type
        self.ai_model = self._initialize_ai_model()
    
    @abstractmethod
    def _initialize_ai_model(self) -> Any:
        """Initialize the appropriate AI model for this agent"""
        pass
    
    @abstractmethod
    def get_hybrid_prompts(self, task_context: Dict[str, Any]) -> HybridPrompt:
        """Generate the 3-layer prompt structure for this agent"""
        pass
    
    async def process_hybrid_task(self, task: Dict[str, Any], task_complexity: int = 5) -> HybridResult:
        """Process task using hybrid AI + rules approach"""
        start_time = time.time()
        
        try:
            # Step 1: Select optimal AI model
            thinking_required = task.get("thinking_required", False)
            model_type = self.token_budget_manager.select_model(task_complexity, thinking_required)
            
            # Step 2: Generate hybrid prompts
            prompts = self.get_hybrid_prompts(task)
            
            # Step 3: Execute AI analysis
            ai_result = await self._execute_ai_analysis(prompts, model_type, task)
            
            # Step 4: Apply business rules validation
            validation_result = self.rules_engine.validate(ai_result, "trend_validation")
            
            # Step 5: Apply quality gates
            quality_gates = self._apply_quality_gates(ai_result, validation_result)
            
            # Step 6: Calculate confidence and metrics
            confidence_score = self._calculate_confidence_score(ai_result, validation_result, quality_gates)
            cost_metrics = self._calculate_cost_metrics(model_type, ai_result)
            
            execution_time_ms = int((time.time() - start_time) * 1000)
            
            # Record token usage
            if hasattr(ai_result, 'usage_metadata'):
                self.token_budget_manager.record_usage(model_type, ai_result.usage_metadata.get('total_tokens', 0))
            
            return HybridResult(
                task=task,
                confidence_score=confidence_score,
                execution_time_ms=execution_time_ms,
                usage_metadata=ai_result.usage_metadata if hasattr(ai_result, 'usage_metadata') else {},
                ai_analysis=ai_result,
                model_used=model_type.value,
                quality_gates=quality_gates
            )
            
        except Exception as e:
            self.logger.error(f"Error in hybrid task processing: {e}")
            raise
    
    async def _execute_ai_analysis(self, prompts: HybridPrompt, model_type: AIModelType, task: Dict) -> Any:
        """Execute AI analysis with the selected model"""
        # This is a placeholder - implement based on your AI client
        # Should integrate with Google MCP, Vertex AI, or direct Gemini API
        raise NotImplementedError("Subclasses must implement _execute_ai_analysis")
    
    def _apply_quality_gates(self, ai_result: Any, validation_result: Dict) -> Dict[str, Any]:
        """Apply quality gates to the result"""
        quality_gates = {}
        
        # Quality gate 1: Business rules compliance
        quality_gates["business_rules"] = {
            "passed": validation_result.get("passed", False),
            "score": validation_result.get("score", 0.0),
            "threshold": 7.0
        }
        
        # Quality gate 2: Confidence threshold
        confidence_score = getattr(ai_result, 'confidence_score', 0.0)
        quality_gates["confidence"] = {
            "passed": confidence_score >= 7.0,
            "score": confidence_score,
            "threshold": 7.0
        }
        
        # Quality gate 3: Execution time
        execution_time = getattr(ai_result, 'execution_time_ms', 0)
        quality_gates["execution_time"] = {
            "passed": execution_time <= self.config.max_execution_time * 1000,
            "score": max(0.0, 10.0 - (execution_time / 1000) / 30.0),  # Score based on time
            "threshold": 7.0
        }
        
        return quality_gates
    
    def _calculate_confidence_score(self, ai_result: Any, validation_result: Dict, quality_gates: Dict) -> float:
        """Calculate overall confidence score"""
        scores = []
        
        # AI confidence
        if hasattr(ai_result, 'confidence_score'):
            scores.append(ai_result.confidence_score)
        
        # Validation score
        scores.append(validation_result.get("score", 0.0))
        
        # Quality gate scores
        for gate_name, gate_data in quality_gates.items():
            scores.append(gate_data.get("score", 0.0))
        
        # Return average score, normalized to 0-10 scale
        return sum(scores) / len(scores) if scores else 0.0
    
    def _calculate_cost_metrics(self, model_type: AIModelType, ai_result: Any) -> Dict[str, float]:
        """Calculate cost metrics for the operation"""
        # This is a placeholder - implement actual cost calculation
        # based on your AI provider's pricing
        base_costs = {
            AIModelType.GEMINI_2_5_FLASH_THINKING: 0.0035,  # per 1K thinking tokens
            AIModelType.GEMINI_2_5_FLASH_LITE: 0.0001,      # per 1K input tokens
            AIModelType.GEMINI_2_0_FLASH_LITE: 0.00005      # per 1K input tokens
        }
        
        total_tokens = getattr(ai_result, 'usage_metadata', {}).get('total_tokens', 1000)
        thinking_tokens = getattr(ai_result, 'usage_metadata', {}).get('thinking_tokens', 0)
        
        base_cost = base_costs.get(model_type, 0.0001)
        cost = (total_tokens / 1000) * base_cost
        
        if thinking_tokens > 0:
            thinking_cost = (thinking_tokens / 1000) * 0.0035
            cost += thinking_cost
        
        return {
            "total_cost_usd": cost,
            "tokens_used": total_tokens,
            "thinking_tokens": thinking_tokens,
            "cost_per_1k_tokens": base_cost * 1000
        }
