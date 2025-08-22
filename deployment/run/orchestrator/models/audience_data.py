"""Audience data models for Helios Autonomous Store"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional


class AudienceSegment(Enum):
    """Audience segment types"""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    TERTIARY = "tertiary"
    NICHE = "niche"


class IncomeLevel(Enum):
    """Income level categories"""
    LOW = "low"
    MIDDLE = "middle"
    HIGH = "high"
    ULTRA_HIGH = "ultra_high"


class LifestyleCategory(Enum):
    """Lifestyle categories"""
    MINIMALIST = "minimalist"
    LUXURY = "luxury"
    ADVENTURE = "adventure"
    FAMILY_ORIENTED = "family_oriented"
    CAREER_FOCUSED = "career_focused"
    CREATIVE = "creative"
    TECH_SAVVY = "tech_savvy"
    TRADITIONAL = "traditional"
    TRENDY = "trendy"
    SUSTAINABLE = "sustainable"


@dataclass
class AudiencePersona:
    """Detailed audience persona"""
    persona_id: str
    name: str
    segment: AudienceSegment
    age_range: str
    gender: Optional[str] = None
    location: str = "global"
    income_level: IncomeLevel = IncomeLevel.MIDDLE
    lifestyle: LifestyleCategory = LifestyleCategory.TRENDY
    
    # Psychographic data
    interests: List[str] = field(default_factory=list)
    values: List[str] = field(default_factory=list)
    personality_traits: List[str] = field(default_factory=list)
    pain_points: List[str] = field(default_factory=list)
    aspirations: List[str] = field(default_factory=list)
    
    # Behavioral data
    online_platforms: List[str] = field(default_factory=list)
    shopping_habits: List[str] = field(default_factory=list)
    content_preferences: List[str] = field(default_factory=list)
    brand_loyalty: float = 0.5
    
    # Engagement metrics
    engagement_score: float = 0.0
    conversion_potential: float = 0.0
    lifetime_value: float = 0.0
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    data_sources: List[str] = field(default_factory=list)
    confidence_score: float = 0.0


@dataclass
class AudienceAnalysis:
    """Comprehensive audience analysis"""
    analysis_id: str
    trend_name: str
    primary_persona: AudiencePersona
    secondary_personas: List[AudiencePersona] = field(default_factory=list)
    
    # Analysis results
    total_addressable_market: int = 0
    market_segments: List[str] = field(default_factory=list)
    engagement_potential: float = 0.0
    conversion_likelihood: float = 0.0
    
    # Trend-specific insights
    trend_relevance_score: float = 0.0
    audience_overlap: float = 0.0
    competitive_advantage: List[str] = field(default_factory=list)
    
    # Recommendations
    targeting_strategy: str = ""
    messaging_approach: str = ""
    platform_priorities: List[str] = field(default_factory=list)
    content_strategy: str = ""
    
    # Performance metrics
    analysis_duration_ms: int = 0
    confidence_score: float = 0.0
    data_quality_score: float = 0.0
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    mcp_model_used: str = "unknown"
    analysis_method: str = "comprehensive"
    rapid_mode_used: bool = False
    
    def get_total_personas(self) -> int:
        """Get total number of personas"""
        return 1 + len(self.secondary_personas)
    
    def get_average_confidence(self) -> float:
        """Get average confidence score across all personas"""
        scores = [self.primary_persona.confidence_score]
        scores.extend([p.confidence_score for p in self.secondary_personas])
        return sum(scores) / len(scores) if scores else 0.0
    
    def is_high_confidence(self) -> bool:
        """Check if analysis has high confidence"""
        return self.confidence_score >= 0.8 and self.data_quality_score >= 0.8
