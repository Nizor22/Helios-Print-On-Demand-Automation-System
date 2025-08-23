"""Trend data models for Helios Autonomous Store"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional


class TrendUrgency(Enum):
    """Trend urgency levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TrendCategory(Enum):
    """Trend categories"""
    POP_CULTURE = "pop_culture"
    TECHNOLOGY = "technology"
    LIFESTYLE = "lifestyle"
    POLITICS = "politics"
    BUSINESS = "business"
    ENTERTAINMENT = "entertainment"
    SPORTS = "sports"
    HEALTH = "health"
    FASHION = "fashion"
    FOOD = "food"


@dataclass
class TrendData:
    """Core trend data structure"""
    trend_name: str
    keywords: List[str]
    category: TrendCategory
    urgency: TrendUrgency
    discovered_at: datetime = field(default_factory=datetime.utcnow)
    source: str = "unknown"
    confidence_score: float = 0.0
    volume_score: float = 0.0
    growth_rate: float = 0.0
    geographic_spread: List[str] = field(default_factory=list)
    demographic_targets: List[str] = field(default_factory=list)
    emotional_triggers: List[str] = field(default_factory=list)
    related_trends: List[str] = field(default_factory=list)
    competitor_activity: Dict[str, Any] = field(default_factory=dict)
    raw_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrendAnalysis:
    """Comprehensive trend analysis"""
    trend_data: TrendData
    opportunity_score: float
    market_size: str
    competition_level: str
    entry_barriers: List[str]
    monetization_potential: float
    time_to_market: str
    risk_factors: List[str]
    success_indicators: List[str]
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    mcp_model_used: str = "unknown"
    analysis_duration_ms: int = 0
    confidence_level: float = 0.0


@dataclass
class TrendOpportunity:
    """Trend opportunity assessment"""
    trend_analysis: TrendAnalysis
    recommended_products: List[str]
    target_audience: str
    pricing_strategy: str
    marketing_angle: str
    launch_timing: str
    expected_roi: float
    success_probability: float
    priority_level: str
    execution_complexity: str
    resource_requirements: List[str]
    created_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "identified"
    assigned_agent: Optional[str] = None
