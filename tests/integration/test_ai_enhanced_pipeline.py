"""
Integration tests for AI-enhanced pipeline
Tests the complete flow from trend discovery to product generation with AI
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone
from typing import Dict, List, Any

from helios.config import HeliosConfig
from helios.services.automated_trend_discovery import AutomatedTrendDiscovery
from helios.services.product_generation_pipeline import ProductGenerationPipeline
from helios.services.helios_orchestrator import HeliosOrchestrator
from helios.agents.trend_analysis_ai import TrendAnalysisMode, TrendAnalysis


@pytest.fixture
def test_config():
    """Create test configuration"""
    config = Mock(spec=HeliosConfig)
    config.google_mcp_url = "http://test-mcp-server"
    config.google_mcp_auth_token = "test-token"
    config.google_cloud_project = "test-project"
    config.google_cloud_location = "us-central1"
    config.vertex_ai_project_id = "test-project"
    config.vertex_ai_location = "us-central1"
    config.min_opportunity_score = 7.0
    config.min_audience_confidence = 0.7
    config.max_execution_time = 300
    config.printify_api_token = "test-printify-token"
    config.printify_shop_id = "test-shop"
    config.output_dir = "/tmp/test-output"
    config.fonts_dir = "/tmp/test-fonts"
    config.gsheet_id = None
    config.google_drive_folder_id = None
    config.enable_performance_monitoring = False
    return config


class TestAIEnhancedTrendDiscovery:
    """Integration tests for AI-enhanced trend discovery"""
    
    @pytest.mark.asyncio
    async def test_ai_trend_discovery_flow(self, test_config):
        """Test complete AI-powered trend discovery flow"""
        with patch('helios.services.automated_trend_discovery.TrendAnalysisAI') as mock_ai, \
             patch('helios.services.automated_trend_discovery.HeliosCEO') as mock_ceo, \
             patch('helios.services.automated_trend_discovery.ZeitgeistAgent'), \
             patch('helios.services.automated_trend_discovery.GoogleTrendsClient'), \
             patch('helios.services.automated_trend_discovery.PerformanceMonitor'):
            
            # Mock AI agent
            mock_ai_instance = AsyncMock()
            mock_ai_instance.analyze_trends = AsyncMock(return_value=[
                TrendAnalysis(
                    trend_id="ai_test_trend_1",
                    trend_name="AI Test Trend",
                    category="Fashion",
                    ai_confidence_score=0.85,
                    market_opportunity_score=8.5,
                    predicted_success_rate=0.82,
                    pattern_type="emerging",
                    pattern_strength=0.9,
                    trend_lifecycle_stage="growing",
                    target_demographics={"age": "18-35", "gender": "all"},
                    competitive_landscape={"competition_level": "medium"},
                    market_size_estimate="large",
                    growth_velocity=0.75,
                    recommended_products=[
                        {"type": "t-shirt", "style": "modern", "confidence": 0.9}
                    ],
                    design_themes=["minimalist", "bold", "trendy"],
                    marketing_angles=["Be part of the movement", "Express yourself"],
                    pricing_strategy={"strategy": "premium", "margin_multiplier": 1.5}
                )
            ])
            mock_ai.return_value = mock_ai_instance
            
            # Mock CEO validation
            mock_ceo_instance = AsyncMock()
            mock_ceo_instance.validate_trend = AsyncMock(return_value=Mock(
                approved=True,
                trend_name="AI Test Trend",
                opportunity_score=8.5,
                priority=Mock(value="HIGH")
            ))
            mock_ceo.return_value = mock_ceo_instance
            
            # Create service and run discovery
            discovery_service = AutomatedTrendDiscovery(test_config)
            result = await discovery_service.run_discovery_pipeline(["test", "trend"])
            
            # Verify results
            assert result["status"] == "success"
            assert len(result["trends_discovered"]) > 0
            assert result["ai_mode"] is True
            
            # Verify AI agent was used
            mock_ai_instance.analyze_trends.assert_called_once()
            
            # Check trend data includes AI insights
            trend = result["trends_discovered"][0]
            assert "ai_analysis" in trend
            assert trend["ai_analysis"]["pattern_type"] == "emerging"
            assert trend["ai_analysis"]["predicted_success_rate"] == 0.82
    
    @pytest.mark.asyncio
    async def test_ai_to_legacy_conversion(self, test_config):
        """Test conversion between AI and legacy trend formats"""
        discovery_service = AutomatedTrendDiscovery(test_config)
        
        # Create AI trend analysis
        ai_trend = TrendAnalysis(
            trend_id="test_ai_trend",
            trend_name="Test AI Trend",
            category="Technology",
            ai_confidence_score=0.9,
            market_opportunity_score=9.0,
            predicted_success_rate=0.88,
            pattern_type="viral",
            pattern_strength=0.95,
            trend_lifecycle_stage="emerging",
            target_demographics={"age": "25-40", "interests": ["tech"]},
            competitive_landscape={"competition_level": "low"},
            market_size_estimate="large",
            growth_velocity=0.9,
            recommended_products=[{"type": "phone case"}],
            design_themes=["futuristic"],
            marketing_angles=["Future is now"],
            pricing_strategy={"strategy": "competitive"}
        )
        
        # Convert to legacy format
        legacy_trends = discovery_service._convert_ai_trends_to_legacy([ai_trend])
        
        assert len(legacy_trends) == 1
        legacy = legacy_trends[0]
        
        # Verify conversion
        assert legacy["trend_name"] == "Test AI Trend"
        assert legacy["opportunity_score"] == 9.0
        assert legacy["confidence_level"] == 0.9
        assert legacy["velocity"] == "high"  # growth_velocity > 0.5
        assert "ai_analysis" in legacy
        assert legacy["ai_analysis"]["pattern_type"] == "viral"


class TestAIEnhancedProductGeneration:
    """Integration tests for AI-enhanced product generation"""
    
    @pytest.mark.asyncio
    async def test_ai_enhanced_product_generation(self, test_config):
        """Test product generation with AI insights"""
        with patch('helios.services.product_generation_pipeline.TrendAnalysisAI') as mock_ai, \
             patch('helios.services.product_generation_pipeline.CreativeDirector') as mock_creative, \
             patch('helios.services.product_generation_pipeline.MarketingCopywriter') as mock_copywriter, \
             patch('helios.services.product_generation_pipeline.EthicalGuardianAgent'), \
             patch('helios.services.product_generation_pipeline.PrintifyPublisherAgent'), \
             patch('helios.services.product_generation_pipeline.ImageGenerationService'), \
             patch('helios.services.product_generation_pipeline.PerformanceMonitor'):
            
            # Mock creative director
            mock_creative_instance = AsyncMock()
            mock_creative_instance.generate_design_concept = AsyncMock(return_value={
                "status": "success",
                "design_data": {
                    "concept": "AI-optimized modern design",
                    "elements": ["minimalist", "bold"],
                    "colors": ["black", "white"],
                    "prompt": "Modern AI trend design"
                }
            })
            mock_creative.return_value = mock_creative_instance
            
            # Mock copywriter
            mock_copywriter_instance = AsyncMock()
            mock_copywriter_instance.generate_marketing_copy = AsyncMock(return_value={
                "status": "success", 
                "copy_data": {
                    "title": "AI-Enhanced Product Title",
                    "description": "AI-optimized description",
                    "bullet_points": ["Feature 1", "Feature 2"],
                    "tags": ["ai", "trend"],
                    "call_to_action": "Buy now!"
                }
            })
            mock_copywriter.return_value = mock_copywriter_instance
            
            # Create trend opportunity with AI insights
            trend_opportunity = {
                "trend_name": "AI Test Trend",
                "opportunity_score": 8.5,
                "ai_analysis": {
                    "design_themes": ["modern", "minimalist", "tech"],
                    "recommended_products": [
                        {"type": "t-shirt", "style": "modern"}
                    ],
                    "marketing_angles": ["Future tech", "Innovation"],
                    "pricing_strategy": {"strategy": "premium", "margin": 1.5}
                }
            }
            
            # Create pipeline and run
            pipeline = ProductGenerationPipeline(test_config)
            pipeline.max_designs_per_trend = 2  # Reduce for testing
            
            result = await pipeline.run_generation_pipeline(trend_opportunity)
            
            # Verify results
            assert result["status"] == "success"
            assert len(result["designs"]) == 2
            
            # Verify AI insights were used
            call_args = mock_creative_instance.generate_design_concept.call_args_list
            assert any("modern" in str(call.kwargs.get("style_preferences", {})) for call in call_args)
            
            # Verify marketing copy used AI angles
            copywriter_calls = mock_copywriter_instance.generate_marketing_copy.call_args_list
            assert len(copywriter_calls) > 0


class TestAIOrchestrationIntegration:
    """Integration tests for AI-enhanced orchestration"""
    
    @pytest.mark.asyncio
    async def test_orchestrator_with_ai_agents(self, test_config):
        """Test orchestrator initialization with AI agents"""
        with patch('helios.services.helios_orchestrator.TrendAnalysisAI') as mock_trend_ai, \
             patch('helios.services.helios_orchestrator.HeliosCEO') as mock_ceo, \
             patch('helios.services.helios_orchestrator.create_automated_trend_discovery'), \
             patch('helios.services.helios_orchestrator.create_product_generation_pipeline'), \
             patch('helios.services.helios_orchestrator.create_performance_optimization_service'), \
             patch('helios.services.helios_orchestrator.PerformanceMonitor'):
            
            orchestrator = HeliosOrchestrator(test_config)
            
            # Initialize services
            success = await orchestrator.initialize_services()
            
            # Verify AI agents were initialized
            assert orchestrator.use_ai_orchestration is True
            mock_trend_ai.assert_called_once_with(test_config)
            mock_ceo.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ai_keyword_generation(self, test_config):
        """Test AI-powered keyword generation"""
        with patch('helios.services.helios_orchestrator.TrendAnalysisAI') as mock_trend_ai, \
             patch('helios.services.helios_orchestrator.PerformanceMonitor'):
            
            # Mock AI trend analysis
            mock_ai_instance = AsyncMock()
            mock_ai_instance.analyze_trends = AsyncMock(return_value=[
                Mock(
                    trend_name="Emerging Tech Trend",
                    marketing_angles=["Future is here", "Tech revolution"]
                ),
                Mock(
                    trend_name="Sustainable Fashion",
                    marketing_angles=["Eco-friendly", "Save the planet"]
                )
            ])
            mock_trend_ai.return_value = mock_ai_instance
            
            orchestrator = HeliosOrchestrator(test_config)
            orchestrator.trend_ai = mock_ai_instance
            
            # Generate keywords
            keywords = await orchestrator._get_ai_generated_keywords()
            
            # Verify keywords include AI suggestions
            assert "Emerging Tech Trend" in keywords
            assert "Sustainable Fashion" in keywords
            assert "Future is here" in keywords
            assert len(keywords) <= 20  # Should be limited
    
    @pytest.mark.asyncio  
    async def test_end_to_end_ai_pipeline(self, test_config):
        """Test complete end-to-end flow with AI enhancements"""
        # This test verifies the entire pipeline works together
        # In a real scenario, this would be more complex
        
        with patch('helios.services.automated_trend_discovery.TrendAnalysisAI'), \
             patch('helios.services.product_generation_pipeline.TrendAnalysisAI'), \
             patch('helios.services.helios_orchestrator.TrendAnalysisAI'), \
             patch('helios.services.helios_orchestrator.create_automated_trend_discovery') as mock_discovery_factory, \
             patch('helios.services.helios_orchestrator.create_product_generation_pipeline') as mock_pipeline_factory, \
             patch('helios.services.helios_orchestrator.create_performance_optimization_service'), \
             patch('helios.services.helios_orchestrator.PerformanceMonitor'):
            
            # Mock discovery service
            mock_discovery = AsyncMock()
            mock_discovery.run_discovery_pipeline = AsyncMock(return_value={
                "status": "success",
                "trends_discovered": [{"trend_name": "AI Test", "ai_analysis": {}}],
                "opportunities_validated": [{"trend_name": "AI Test"}]
            })
            mock_discovery_factory.return_value = mock_discovery
            
            # Mock product pipeline
            mock_pipeline = AsyncMock()
            mock_pipeline.run_generation_pipeline = AsyncMock(return_value={
                "status": "success",
                "product_packages": [{"id": "prod_1"}]
            })
            mock_pipeline_factory.return_value = mock_pipeline
            
            # Create orchestrator
            orchestrator = HeliosOrchestrator(test_config)
            await orchestrator.initialize_services()
            
            # Run trend discovery cycle
            result = await orchestrator.run_trend_discovery_cycle()
            
            # Verify success
            assert result is not None
            mock_discovery.run_discovery_pipeline.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])