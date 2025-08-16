"""
Unit tests for TrendAnalysisAI agent
Tests AI-powered trend analysis, pattern recognition, and product predictions
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import Dict, List, Any

from helios.agents.trend_analysis_ai import (
    TrendAnalysisAI,
    TrendAnalysisMode,
    TrendAnalysis,
    ProductPrediction
)
from helios.config import HeliosConfig


@pytest.fixture
def mock_config():
    """Create a mock configuration for testing"""
    config = Mock(spec=HeliosConfig)
    config.google_mcp_url = "http://test-mcp-server"
    config.google_mcp_auth_token = "test-token"
    config.google_cloud_project = "test-project"
    config.google_cloud_location = "us-central1"
    config.vertex_ai_project_id = "test-project"
    config.vertex_ai_location = "us-central1"
    config.gsheet_id = None
    config.google_drive_folder_id = None
    return config


@pytest.fixture
def mock_mcp_client():
    """Create a mock MCP client"""
    client = AsyncMock()
    client.discover_trends = AsyncMock(return_value={
        "status": "success",
        "analysis": {
            "ranked_trends": [
                {
                    "keyword": "test trend",
                    "composite_score": 8.5,
                    "total_volume": 5000,
                    "total_growth": 150,
                    "total_engagement": 2000,
                    "source_diversity": 0.75,
                    "sources": ["google_trends", "social_media", "news"]
                }
            ]
        }
    })
    client.close = AsyncMock()
    return client


@pytest.fixture
def mock_vertex_ai_client():
    """Create a mock Vertex AI client"""
    client = AsyncMock()
    client.generate_text = AsyncMock(return_value='{"patterns": {"test trend": {"type": "emerging"}}}')
    return client


@pytest.fixture
def mock_google_trends_client():
    """Create a mock Google Trends client"""
    client = AsyncMock()
    client.get_trend_data = AsyncMock(return_value={"status": "success", "data": {}})
    return client


class TestTrendAnalysisAI:
    """Test cases for TrendAnalysisAI agent"""
    
    @pytest.mark.asyncio
    async def test_initialization(self, mock_config):
        """Test AI agent initialization"""
        with patch('helios.agents.trend_analysis_ai.GoogleMCPClient') as mock_mcp, \
             patch('helios.agents.trend_analysis_ai.VertexAIClient') as mock_vertex, \
             patch('helios.agents.trend_analysis_ai.GoogleTrendsClient') as mock_trends, \
             patch('helios.agents.trend_analysis_ai.PerformanceMonitor') as mock_monitor:
            
            ai_agent = TrendAnalysisAI(mock_config)
            
            assert ai_agent.config == mock_config
            assert ai_agent.min_confidence_threshold == 0.7
            assert ai_agent.pattern_recognition_threshold == 0.8
            assert ai_agent.prediction_confidence_threshold == 0.75
            
            mock_mcp.assert_called_once()
            mock_vertex.assert_called_once()
            mock_trends.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_trends_discovery_mode(self, mock_config, mock_mcp_client, mock_vertex_ai_client):
        """Test trend analysis in discovery mode"""
        with patch('helios.agents.trend_analysis_ai.GoogleMCPClient', return_value=mock_mcp_client), \
             patch('helios.agents.trend_analysis_ai.VertexAIClient', return_value=mock_vertex_ai_client), \
             patch('helios.agents.trend_analysis_ai.GoogleTrendsClient'), \
             patch('helios.agents.trend_analysis_ai.PerformanceMonitor'):
            
            ai_agent = TrendAnalysisAI(mock_config)
            
            # Run trend analysis
            trends = await ai_agent.analyze_trends(
                keywords=["test", "trend"],
                mode=TrendAnalysisMode.DISCOVERY,
                categories=["fashion"],
                geo="US"
            )
            
            # Verify results
            assert isinstance(trends, list)
            assert len(trends) > 0
            
            # Check first trend
            trend = trends[0]
            assert isinstance(trend, TrendAnalysis)
            assert trend.trend_name == "test trend"
            assert trend.ai_confidence_score >= 0
            assert trend.ai_confidence_score <= 1
            assert trend.market_opportunity_score == 8.5
            
            # Verify MCP client was called
            mock_mcp_client.discover_trends.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_analyze_trends_filters_by_confidence(self, mock_config, mock_mcp_client, mock_vertex_ai_client):
        """Test that trends are filtered by confidence threshold"""
        # Set up mock to return trends with different confidence scores
        mock_mcp_client.discover_trends.return_value = {
            "status": "success",
            "analysis": {
                "ranked_trends": [
                    {
                        "keyword": "high confidence trend",
                        "composite_score": 9.0,
                        "source_diversity": 0.9,
                        "sources": ["google_trends", "social_media", "news", "competitor"]
                    },
                    {
                        "keyword": "low confidence trend", 
                        "composite_score": 3.0,
                        "source_diversity": 0.2,
                        "sources": ["google_trends"]
                    }
                ]
            }
        }
        
        with patch('helios.agents.trend_analysis_ai.GoogleMCPClient', return_value=mock_mcp_client), \
             patch('helios.agents.trend_analysis_ai.VertexAIClient', return_value=mock_vertex_ai_client), \
             patch('helios.agents.trend_analysis_ai.GoogleTrendsClient'), \
             patch('helios.agents.trend_analysis_ai.PerformanceMonitor'):
            
            ai_agent = TrendAnalysisAI(mock_config)
            
            trends = await ai_agent.analyze_trends(["test"], mode=TrendAnalysisMode.DISCOVERY)
            
            # Should only include high confidence trend
            assert len(trends) == 1
            assert trends[0].trend_name == "high confidence trend"
            assert trends[0].ai_confidence_score >= ai_agent.min_confidence_threshold
    
    @pytest.mark.asyncio
    async def test_predict_product_success(self, mock_config, mock_vertex_ai_client):
        """Test product success prediction"""
        # Create a mock trend analysis
        trend_analysis = TrendAnalysis(
            trend_id="test_trend_1",
            trend_name="Test Trend",
            category="Fashion",
            ai_confidence_score=0.85,
            market_opportunity_score=8.0,
            predicted_success_rate=0.8,
            pattern_type="emerging",
            pattern_strength=0.9,
            trend_lifecycle_stage="growing",
            target_demographics={"age": "18-35"},
            competitive_landscape={"competition": "medium"},
            market_size_estimate="large",
            growth_velocity=0.7,
            recommended_products=[],
            design_themes=["modern"],
            marketing_angles=["trendy"],
            pricing_strategy={"strategy": "premium"}
        )
        
        product_concept = {
            "design_concept": "Modern test trend design",
            "target_audience": {"age": "18-35"},
            "product_type": "t-shirt"
        }
        
        # Mock Vertex AI response
        mock_vertex_ai_client.generate_text.return_value = '''
        {
            "success_rate": 0.85,
            "market_fit_score": 8.5,
            "risk_factors": [{"factor": "competition", "level": "medium"}],
            "optimization_suggestions": ["Use bold colors"],
            "marketing_recommendations": ["Target social media"]
        }
        '''
        
        with patch('helios.agents.trend_analysis_ai.GoogleMCPClient'), \
             patch('helios.agents.trend_analysis_ai.VertexAIClient', return_value=mock_vertex_ai_client), \
             patch('helios.agents.trend_analysis_ai.GoogleTrendsClient'), \
             patch('helios.agents.trend_analysis_ai.PerformanceMonitor'):
            
            ai_agent = TrendAnalysisAI(mock_config)
            
            prediction = await ai_agent.predict_product_success(trend_analysis, product_concept)
            
            assert isinstance(prediction, ProductPrediction)
            assert prediction.predicted_success_rate == 0.85
            assert prediction.market_fit_score == 8.5
            assert len(prediction.risk_factors) > 0
            assert len(prediction.optimization_suggestions) > 0
    
    @pytest.mark.asyncio
    async def test_optimize_trend_strategy(self, mock_config, mock_vertex_ai_client):
        """Test trend strategy optimization"""
        # Create mock trend analyses
        trend_analyses = [
            TrendAnalysis(
                trend_id=f"trend_{i}",
                trend_name=f"Trend {i}",
                category="Fashion",
                ai_confidence_score=0.8,
                market_opportunity_score=7 + i,
                predicted_success_rate=0.75,
                pattern_type="emerging",
                pattern_strength=0.8,
                trend_lifecycle_stage="growing",
                target_demographics={},
                competitive_landscape={},
                market_size_estimate="medium",
                growth_velocity=0.5,
                recommended_products=[],
                design_themes=[],
                marketing_angles=[],
                pricing_strategy={}
            )
            for i in range(3)
        ]
        
        # Mock Vertex AI response
        mock_vertex_ai_client.generate_text.return_value = '''
        {
            "priority_ranking": ["Trend 2", "Trend 1", "Trend 0"],
            "resource_allocation": {"Trend 2": 50, "Trend 1": 30, "Trend 0": 20},
            "timeline": "4 weeks",
            "risk_mitigation": ["Monitor competition", "Test designs"],
            "expected_roi": 3.5
        }
        '''
        
        with patch('helios.agents.trend_analysis_ai.GoogleMCPClient'), \
             patch('helios.agents.trend_analysis_ai.VertexAIClient', return_value=mock_vertex_ai_client), \
             patch('helios.agents.trend_analysis_ai.GoogleTrendsClient'), \
             patch('helios.agents.trend_analysis_ai.PerformanceMonitor'):
            
            ai_agent = TrendAnalysisAI(mock_config)
            
            strategy = await ai_agent.optimize_trend_strategy(
                trend_analyses,
                business_constraints={"budget": "moderate"}
            )
            
            assert strategy["status"] == "success"
            assert "optimization" in strategy
            assert strategy["trends_analyzed"] == 3
    
    @pytest.mark.asyncio
    async def test_error_handling_mcp_failure(self, mock_config, mock_mcp_client):
        """Test error handling when MCP client fails"""
        mock_mcp_client.discover_trends.side_effect = Exception("MCP server error")
        
        with patch('helios.agents.trend_analysis_ai.GoogleMCPClient', return_value=mock_mcp_client), \
             patch('helios.agents.trend_analysis_ai.VertexAIClient'), \
             patch('helios.agents.trend_analysis_ai.GoogleTrendsClient'), \
             patch('helios.agents.trend_analysis_ai.PerformanceMonitor'):
            
            ai_agent = TrendAnalysisAI(mock_config)
            
            with pytest.raises(Exception) as exc_info:
                await ai_agent.analyze_trends(["test"])
            
            assert "MCP server error" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_pattern_recognition(self, mock_config, mock_mcp_client, mock_vertex_ai_client):
        """Test pattern recognition functionality"""
        # Mock Vertex AI to return specific patterns
        mock_vertex_ai_client.generate_text.return_value = '''
        {
            "patterns": {
                "test trend": {
                    "type": "seasonal",
                    "strength": 0.9,
                    "lifecycle": "peak"
                }
            },
            "growth_velocity": {"test trend": 0.8},
            "saturation": {"test trend": 0.3}
        }
        '''
        
        with patch('helios.agents.trend_analysis_ai.GoogleMCPClient', return_value=mock_mcp_client), \
             patch('helios.agents.trend_analysis_ai.VertexAIClient', return_value=mock_vertex_ai_client), \
             patch('helios.agents.trend_analysis_ai.GoogleTrendsClient'), \
             patch('helios.agents.trend_analysis_ai.PerformanceMonitor'):
            
            ai_agent = TrendAnalysisAI(mock_config)
            
            trends = await ai_agent.analyze_trends(["test trend"])
            
            assert len(trends) > 0
            trend = trends[0]
            assert trend.pattern_type == "seasonal"  # Should use AI-detected pattern
    
    @pytest.mark.asyncio
    async def test_close_cleanup(self, mock_config, mock_mcp_client):
        """Test that resources are properly cleaned up"""
        with patch('helios.agents.trend_analysis_ai.GoogleMCPClient', return_value=mock_mcp_client), \
             patch('helios.agents.trend_analysis_ai.VertexAIClient'), \
             patch('helios.agents.trend_analysis_ai.GoogleTrendsClient'), \
             patch('helios.agents.trend_analysis_ai.PerformanceMonitor'):
            
            ai_agent = TrendAnalysisAI(mock_config)
            
            await ai_agent.close()
            
            mock_mcp_client.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])