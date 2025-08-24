"""Analytics data models for Helios Autonomous Store"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional


class PublicationStatus(Enum):
    """Publication status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    RETRY = "retry"
    CANCELLED = "cancelled"


class PerformanceTier(Enum):
    """Performance tier classification"""
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    BELOW_AVERAGE = "below_average"
    POOR = "poor"


@dataclass
class PerformanceMetrics:
    """Performance metrics for products and campaigns"""
    metrics_id: str
    product_id: str
    period_start: datetime
    period_end: datetime
    
    # View metrics
    total_views: int = 0
    unique_views: int = 0
    view_duration_avg: float = 0.0
    
    # Engagement metrics
    likes: int = 0
    shares: int = 0
    comments: int = 0
    engagement_rate: float = 0.0
    
    # Conversion metrics
    clicks: int = 0
    conversions: int = 0
    conversion_rate: float = 0.0
    cost_per_conversion: float = 0.0
    
    # Revenue metrics
    revenue: float = 0.0
    profit: float = 0.0
    roi: float = 0.0
    profit_margin: float = 0.0
    
    # Performance scores
    performance_score: float = 0.0
    performance_tier: PerformanceTier = PerformanceTier.AVERAGE
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    data_source: str = "unknown"
    last_updated: datetime = field(default_factory=datetime.utcnow)
    
    def calculate_engagement_rate(self) -> float:
        """Calculate engagement rate"""
        if self.total_views == 0:
            return 0.0
        return (self.likes + self.shares + self.comments) / self.total_views
    
    def calculate_conversion_rate(self) -> float:
        """Calculate conversion rate"""
        if self.clicks == 0:
            return 0.0
        return self.conversions / self.clicks
    
    def calculate_roi(self) -> float:
        """Calculate ROI"""
        if self.revenue == 0:
            return 0.0
        return (self.profit / self.revenue) * 100
    
    def update_performance_tier(self) -> None:
        """Update performance tier based on score"""
        if self.performance_score >= 9.0:
            self.performance_tier = PerformanceTier.EXCELLENT
        elif self.performance_score >= 7.5:
            self.performance_tier = PerformanceTier.GOOD
        elif self.performance_score >= 6.0:
            self.performance_tier = PerformanceTier.AVERAGE
        elif self.performance_score >= 4.0:
            self.performance_tier = PerformanceTier.BELOW_AVERAGE
        else:
            self.performance_tier = PerformanceTier.POOR


@dataclass
class PublicationResult:
    """Result of publication attempts"""
    publication_id: str
    product_id: str
    platform: str
    status: PublicationStatus
    published_at: Optional[datetime] = None
    
    # Platform-specific data
    platform_product_id: Optional[str] = None
    platform_url: Optional[str] = None
    platform_status: Optional[str] = None
    
    # Publication details
    publication_duration_ms: int = 0
    retry_count: int = 0
    error_messages: List[str] = field(default_factory=list)
    
    # Quality checks
    image_validation: bool = False
    content_validation: bool = False
    pricing_validation: bool = False
    compliance_check: bool = False
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    agent_used: Optional[str] = None
    mcp_model_used: Optional[str] = None
    
    def is_successful(self) -> bool:
        """Check if publication was successful"""
        return self.status == PublicationStatus.SUCCESS
    
    def has_errors(self) -> bool:
        """Check if publication has errors"""
        return bool(self.error_messages)
    
    def all_validations_passed(self) -> bool:
        """Check if all quality validations passed"""
        return all([
            self.image_validation,
            self.content_validation,
            self.pricing_validation,
            self.compliance_check
        ])


@dataclass
class AnalyticsData:
    """Comprehensive analytics data"""
    analytics_id: str
    trend_name: str
    product_id: str
    
    # Performance data
    performance_metrics: PerformanceMetrics
    publication_results: List[PublicationResult] = field(default_factory=list)
    
    # Trend correlation
    trend_performance_score: float = 0.0
    market_timing_score: float = 0.0
    competitive_positioning: float = 0.0
    
    # Optimization insights
    improvement_opportunities: List[str] = field(default_factory=list)
    recommended_actions: List[str] = field(default_factory=list)
    next_iteration_strategy: str = ""
    
    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    analysis_timestamp: datetime = field(default_factory=datetime.utcnow)
    data_freshness_hours: int = 0
    
    def get_total_publications(self) -> int:
        """Get total number of publication attempts"""
        return len(self.publication_results)
    
    def get_successful_publications(self) -> int:
        """Get number of successful publications"""
        return sum(1 for result in self.publication_results if result.is_successful())
    
    def get_publication_success_rate(self) -> float:
        """Get publication success rate"""
        total = self.get_total_publications()
        if total == 0:
            return 0.0
        return self.get_successful_publications() / total
    
    def get_overall_performance_score(self) -> float:
        """Calculate overall performance score"""
        scores = [self.performance_metrics.performance_score]
        if self.trend_performance_score > 0:
            scores.append(self.trend_performance_score)
        if self.market_timing_score > 0:
            scores.append(self.market_timing_score)
        if self.competitive_positioning > 0:
            scores.append(self.competitive_positioning)
        
        return sum(scores) / len(scores) if scores else 0.0
