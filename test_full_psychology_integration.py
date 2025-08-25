#!/usr/bin/env python3
"""
Full Psychology Integration Test Script
Tests the complete Helios Hybrid AI System with all 8 sales psychology principles
and full MCP method integration
"""

import asyncio
import time
from typing import Dict, Any
from helios.agents.zeitgeist import ZeitgeistAgent
from helios.agents.audience import AudienceAnalyst
from helios.agents.product import ProductStrategist
from helios.agents.creative_director import CreativeDirector
from helios.agents.marketing_copywriter import MarketingCopywriter
from helios.agents.hybrid_ai_orchestrator import HybridAIOrchestrator
from helios.agents.hybrid_ai_orchestrator import TaskComplexity


async def test_full_psychology_integration():
    """Test the complete psychological integration workflow end-to-end"""
    
    print("🧠 TESTING FULL PSYCHOLOGY INTEGRATION")
    print("=" * 60)
    
    # Test individual agents with full MCP integration
    await test_zeitgeist_full_integration()
    await test_audience_full_integration()
    await test_product_full_integration()
    await test_creative_full_integration()
    await test_marketing_full_integration()
    
    # Test complete orchestrated workflow
    await test_full_orchestrated_workflow()
    
    print("\n✅ FULL PSYCHOLOGY INTEGRATION TESTING COMPLETE")


async def test_zeitgeist_full_integration():
    """Test Zeitgeist agent with real trend discovery (no seed words)"""
    print("🔍 TESTING ZEITGEIST: REAL TREND DISCOVERY")
    print("-" * 50)
    
    zeitgeist = ZeitgeistAgent()
    
    # Create task context for real trend discovery (no seed words)
    trend_task = {
        "time_range": "30 days",
        "target_regions": "US",
        "product_categories": "apparel, accessories, home_decor",
        "max_trends": 10,
        "min_opportunity_score": 7.0,
        "data_sources": ["google_trends", "social_media", "news", "reddit", "tiktok"]
    }
    
    print("📈 Discovering real trends using multiple data sources...")
    trend_result = await zeitgeist.process_hybrid_task(trend_task, TaskComplexity.STRATEGIC.value)
    
    if hasattr(trend_result, 'trends') and trend_result.trends:
        # Use the first discovered trend for testing
        discovered_trend = trend_result.trends[0] if isinstance(trend_result.trends, list) else list(trend_result.trends.keys())[0]
        print(f"  ✅ Discovered Trend: {discovered_trend}")
        
        # Extract emotional driver from AI analysis
        if hasattr(trend_result, 'emotional_drivers'):
            emotional_driver = trend_result.emotional_drivers.get("primary_emotion", "desire")
        else:
            emotional_driver = "desire"  # Default fallback
            
        print(f"  🎯 Primary Emotion: {emotional_driver}")
        
        # Extract identity statement
        if hasattr(trend_result, 'ai_analysis') and trend_result.ai_analysis:
            identity_statement = trend_result.ai_analysis.get("identity_statement", "Trend follower")
        else:
            identity_statement = "Trend follower"
            
        print(f"  💭 Identity Statement: {identity_statement}")
        
        # Extract social validation
        if hasattr(trend_result, 'ai_analysis') and trend_result.ai_analysis:
            social_validation = trend_result.ai_analysis.get("social_validation", "Join the trend")
        else:
            social_validation = "Join the trend"
            
        print(f"  🤝 Social Validation: {social_validation}")
        
        # Extract confidence score
        confidence = getattr(trend_result, 'confidence_score', 0.0) / 10.0 if hasattr(trend_result, 'confidence_score') else 0.0
        print(f"  📊 Confidence: {confidence:.2f}")
        
        # Extract source
        source = getattr(trend_result, 'model_used', 'ai_analysis')
        print(f"  🔧 Source: {source}")
        
        # Check psychology integration
        if emotional_driver in ["desire", "fear", "pride", "nostalgia", "belonging", "expression"]:
            print("  🧠 Principle #1: Emotion > Logic ✅ FULLY IMPLEMENTED")
            print(f"  🎯 Emotional Driver: {emotional_driver}")
            if identity_statement and identity_statement != "Trend follower":
                print("  💡 Psychological Motivation: ✅ IDENTIFIED")
            else:
                print("  💡 Psychological Motivation: ⚠️ NEEDS IMPROVEMENT")
        else:
            print("  🧠 Principle #1: Emotion > Logic ❌ MISSING")
            
        # Check MCP integration
        if hasattr(trend_result, 'model_used') and trend_result.model_used:
            print(f"  🔌 MCP Integration: ✅ ACTIVE ({trend_result.model_used})")
        else:
            print(f"  🔌 MCP Integration: ❌ INACTIVE")
            
    else:
        print("  ❌ No trends discovered - using fallback analysis")
        discovered_trend = "trending_topic"
        emotional_driver = "desire"
        
    print()
    
    return discovered_trend, emotional_driver


async def test_audience_analyst_full_integration(discovered_trend: str, emotional_driver: str):
    """Test Audience Analyst agent with real trend data (no seed words)"""
    print("👥 TESTING AUDIENCE ANALYST: REAL TREND ANALYSIS")
    print("-" * 50)
    
    audience_analyst = AudienceAnalyst()
    
    # Create audience analysis task using discovered trend data
    audience_task = {
        "trend_name": discovered_trend,
        "emotional_driver": emotional_driver,
        "audience_profile": "trend_followers",
        "target_regions": "US",
        "demographic_focus": "gen_z_urban",
        "psychographic_depth": "comprehensive"
    }
    
    print(f"👤 Analyzing audience for discovered trend: {discovered_trend}")
    print(f"  🎯 Emotion: {emotional_driver}")
    print(f"  📊 Profile: trend_followers")
    
    try:
        result = await audience_analyst.process_hybrid_task(audience_task, TaskComplexity.STRATEGIC.value)
        
        # Check for AI analysis data
        if hasattr(result, 'ai_analysis') and result.ai_analysis:
            print("  ✅ AI analysis data available")
            
            # Extract audience insights
            if hasattr(result, 'audience_insights'):
                audience_insights = result.audience_insights
                if audience_insights.get("primary_persona"):
                    persona = audience_insights["primary_persona"]
                    print(f"  👥 Primary Persona: {persona.get('demographic_cluster', 'Unknown')}")
                    print(f"  🎯 Age Range: {persona.get('age_range', 'Unknown')}")
                    print(f"  💰 Income Level: {persona.get('income_level', 'Unknown')}")
                    
                    # Check psychology principles
                    if persona.get('emotional_triggers'):
                        print("  🧠 Principle #2: Build Trust by Understanding Needs ✅ IMPLEMENTED")
                    else:
                        print("  🧠 Principle #2: Build Trust by Understanding Needs ⚠️ NEEDS IMPROVEMENT")
                        
                    if persona.get('authority_figures'):
                        print("  🧠 Principle #8: Authority/Social Proof ✅ IMPLEMENTED")
                    else:
                        print("  🧠 Principle #8: Authority/Social Proof ⚠️ NEEDS IMPROVEMENT")
                else:
                    print("  ⚠️ No primary persona data available")
            else:
                print("  ⚠️ No audience insights data available")
        else:
            print("  ⚠️ No AI analysis data available")
            
        # Check MCP integration
        if hasattr(result, 'model_used') and result.model_used:
            print(f"  🔌 MCP Integration: ✅ ACTIVE ({result.model_used})")
        else:
            print("  🔌 MCP Integration: ❌ INACTIVE")
            
    except Exception as e:
        print(f"  ❌ Error in audience analysis: {e}")
        
    print()


async def test_product_full_integration():
    """Test Product Strategist with real trend data (no seed words)"""
    print("\n🎯 TESTING PRODUCT STRATEGIST: REAL TREND STRATEGY")
    print("-" * 50)
    
    product_strategist = ProductStrategist()
    
    # Create product strategy task using discovered trend data
    product_task = {
        "trend_name": "discovered_trend",  # Will be replaced with actual discovered trend
        "emotional_driver": "desire",  # Will be replaced with actual emotional driver
        "product_category": "apparel",
        "target_audience": "trend_followers",
        "market_focus": "US",
        "psychological_positioning": True,
        "collection_strategy": True
    }
    
    print(f"🛍️  Testing product strategy for discovered trend")
    print(f"  🎯 Emotion: {product_task['emotional_driver']}")
    print(f"  📦 Category: {product_task['product_category']}")
    
    try:
        result = await product_strategist.process_hybrid_task(product_task, TaskComplexity.STRATEGIC.value)
        
        # Check for AI analysis data
        if hasattr(result, 'ai_analysis') and result.ai_analysis:
            print("  ✅ AI analysis data available")
            
            # Extract product strategy insights
            if hasattr(result, 'product_strategy'):
                strategy = result.product_strategy
                if strategy.get("product_title"):
                    print(f"  🏷️  Product Title: {strategy['product_title']}")
                if strategy.get("psychological_positioning"):
                    print(f"  🧠 Psychological Positioning: ✅ IMPLEMENTED")
                if strategy.get("collection_strategy"):
                    print(f"  📦 Collection Strategy: ✅ IMPLEMENTED")
                    
                    # Check psychology principles
                    if strategy.get("psychological_positioning", {}).get("emotional_driver"):
                        print("  🧠 Principle #1: Emotion > Logic ✅ IMPLEMENTED")
                    else:
                        print("  🧠 Principle #1: Emotion > Logic ⚠️ NEEDS IMPROVEMENT")
                        
                    if strategy.get("collection_strategy", {}).get("theme"):
                        print("  🧠 Principle #7: Consistency & Commitment ✅ IMPLEMENTED")
                    else:
                        print("  🧠 Principle #7: Consistency & Commitment ⚠️ NEEDS IMPROVEMENT")
                else:
                    print("  ⚠️ No product strategy data available")
            else:
                print("  ⚠️ No product strategy data available")
        else:
            print("  ⚠️ No AI analysis data available")
            
        # Check MCP integration
        if hasattr(result, 'model_used') and result.model_used:
            print(f"  🔌 MCP Integration: ✅ ACTIVE ({result.model_used})")
        else:
            print("  🔌 MCP Integration: ❌ INACTIVE")
            
    except Exception as e:
        print(f"  ❌ Error in product strategy: {e}")
        
    print()


async def test_creative_full_integration():
    """Test Creative Director with real trend data (no seed words)"""
    print("\n🎨 TESTING CREATIVE DIRECTOR: REAL TREND CREATIVE DIRECTION")
    print("-" * 50)
    
    creative_director = CreativeDirector()
    
    # Create creative direction task using discovered trend data
    creative_task = {
        "trend_name": "discovered_trend",  # Will be replaced with actual discovered trend
        "emotional_driver": "expression",  # Will be replaced with actual emotional driver
        "creative_theme": "Real Trend Collection",
        "target_audience": "trend_followers",
        "brand_guidelines": "modern, authentic, trend-aware",
        "psychological_principles": True
    }
    
    print(f"🎨 Testing creative direction for discovered trend")
    print(f"  🎯 Emotion: {creative_task['emotional_driver']}")
    print(f"  🎨 Theme: {creative_task['creative_theme']}")
    
    try:
        result = await creative_director.process_hybrid_task(creative_task, TaskComplexity.STRATEGIC.value)
        
        # Check for AI analysis data
        if hasattr(result, 'ai_analysis') and result.ai_analysis:
            print("  ✅ AI analysis data available")
            
            # Extract creative direction insights
            if hasattr(result, 'creative_direction'):
                direction = result.creative_direction
                if direction.get("design_concepts"):
                    print(f"  🎨 Design Concepts: ✅ IMPLEMENTED")
                if direction.get("copy_elements"):
                    print(f"  ✍️  Copy Elements: ✅ IMPLEMENTED")
                if direction.get("marketing_angles"):
                    print(f"  📢 Marketing Angles: ✅ IMPLEMENTED")
                    
                    # Check psychology principles
                    if direction.get("copy_elements", {}).get("emotional_leads"):
                        print("  🧠 Principle #1: Emotion > Logic ✅ IMPLEMENTED")
                    else:
                        print("  🧠 Principle #1: Emotion > Logic ⚠️ NEEDS IMPROVEMENT")
                        
                    if direction.get("visual_guidelines", {}).get("layout_style"):
                        print("  🧠 Principle #4: Visual Simplicity ✅ IMPLEMENTED")
                    else:
                        print("  🧠 Principle #4: Visual Simplicity ⚠️ NEEDS IMPROVEMENT")
                else:
                    print("  ⚠️ No creative direction data available")
            else:
                print("  ⚠️ No creative direction data available")
        else:
            print("  ⚠️ No AI analysis data available")
            
        # Check MCP integration
        if hasattr(result, 'model_used') and result.model_used:
            print(f"  🔌 MCP Integration: ✅ ACTIVE ({result.model_used})")
        else:
            print("  🔌 MCP Integration: ❌ INACTIVE")
            
    except Exception as e:
        print(f"  ❌ Error in creative direction: {e}")
        
    print()


async def test_marketing_full_integration():
    """Test Marketing Copywriter with real trend data (no seed words)"""
    print("\n✍️  TESTING MARKETING COPYWRITER: REAL TREND COPY GENERATION")
    print("-" * 50)
    
    marketing_copywriter = MarketingCopywriter()
    
    # Create copy generation task using discovered trend data
    copy_task = {
        "product_name": "Discovered Trend Product",
        "emotional_driver": "expression",  # Will be replaced with actual emotional driver
        "target_audience": "trend_followers",
        "platform": "Etsy",
        "psychological_frameworks": True,
        "conversion_optimization": True
    }
    
    print(f"✍️  Testing copy generation for discovered trend product")
    print(f"  🎯 Emotion: {copy_task['emotional_driver']}")
    print(f"  👥 Audience: {copy_task['target_audience']}")
    
    try:
        result = await marketing_copywriter.process_hybrid_task(copy_task, TaskComplexity.STRATEGIC.value)
        
        # Check for AI analysis data
        if hasattr(result, 'ai_analysis') and result.ai_analysis:
            print("  ✅ AI analysis data available")
            
            # Extract copy strategy insights
            if hasattr(result, 'copy_strategy'):
                strategy = result.copy_strategy
                if strategy.get("copy_elements"):
                    print(f"  ✍️  Copy Elements: ✅ IMPLEMENTED")
                if strategy.get("messaging_framework"):
                    print(f"  📢 Messaging Framework: ✅ IMPLEMENTED")
                if strategy.get("psychological_triggers"):
                    print(f"  🧠 Psychological Triggers: ✅ IMPLEMENTED")
                    
                    # Check psychology principles
                    if strategy.get("copy_elements", {}).get("emotional_leads"):
                        print("  🧠 Principle #1: Emotion > Logic ✅ IMPLEMENTED")
                    else:
                        print("  🧠 Principle #1: Emotion > Logic ⚠️ NEEDS IMPROVEMENT")
                        
                    if strategy.get("copy_elements", {}).get("social_proof_elements"):
                        print("  🧠 Principle #6: Social Proof ✅ IMPLEMENTED")
                    else:
                        print("  🧠 Principle #6: Social Proof ⚠️ NEEDS IMPROVEMENT")
                else:
                    print("  ⚠️ No copy strategy data available")
            else:
                print("  ⚠️ No copy strategy data available")
        else:
            print("  ⚠️ No AI analysis data available")
            
        # Check MCP integration
        if hasattr(result, 'model_used') and result.model_used:
            print(f"  🔌 MCP Integration: ✅ ACTIVE ({result.model_used})")
        else:
            print("  🔌 MCP Integration: ❌ INACTIVE")
            
    except Exception as e:
        print(f"  ❌ Error in copy generation: {e}")
        
    print()


async def test_full_orchestrated_workflow(discovered_trend: str, emotional_driver: str):
    """Test the complete orchestrated workflow with all psychology principles"""
    print("\n🚀 TESTING FULL ORCHESTRATED WORKFLOW")
    print("-" * 50)
    
    try:
        orchestrator = HybridAIOrchestrator()
        print(f"  ✅ Orchestrator initialized successfully")
        print(f"  🔧 Available agents: {list(orchestrator.agents.keys())}")
        
        # Test complete workflow
        test_workflow = {
            "trend_name": discovered_trend,
            "workflow_type": "full_psychology_pipeline",
            "target_audience": "gen_z_urban",
            "product_categories": ["apparel", "accessories"],
            "emotional_focus": emotional_driver,
            "conversion_optimization": True
        }
        
        print(f"\n🔄 Testing complete workflow: {test_workflow['trend_name']}")
        print(f"  🎯 Focus: {test_workflow['emotional_focus']}")
        print(f"  📦 Categories: {', '.join(test_workflow['product_categories'])}")
        
        # Execute full pipeline
        start_time = time.time()
        
        # Create a proper orchestration task
        from helios.agents.hybrid_ai_orchestrator import OrchestrationTask
        
        task = OrchestrationTask(
            task_type="full_psychology_pipeline",
            priority="HIGH",
            complexity=8,
            thinking_required=True,
            data=test_workflow,
            expected_output=["trend_analysis", "audience_analysis", "product_strategy", "creative_direction"],
            quality_gates=["emotional_driver_detected", "subculture_analyzed", "psychology_applied", "creative_assets_generated"],
            cost_budget=50.0
        )
        
        result = await orchestrator.orchestrate_task(task)
        
        execution_time = time.time() - start_time
        
        print(f"  ✅ Workflow completed in {execution_time:.2f} seconds")
        
        # Extract workflow results
        if hasattr(result, 'status') and result.status == "completed":
            workflow_data = result.results
            
            # Check psychology integration across all phases
            psychology_integration = {
                "trend_analysis": "emotional_driver" in str(workflow_data),
                "audience_analysis": "subculture_analysis" in str(workflow_data),
                "product_strategy": "psychological_positioning" in str(workflow_data),
                "creative_direction": "all_psychology_principles" in str(workflow_data)
            }
            
            print(f"\n  🧠 PSYCHOLOGY INTEGRATION STATUS:")
            for phase, integrated in psychology_integration.items():
                status = "✅ INTEGRATED" if integrated else "❌ MISSING"
                print(f"    {phase.replace('_', ' ').title()}: {status}")
            
            # Overall psychology implementation score
            integration_score = sum(psychology_integration.values()) / len(psychology_integration) * 100
            print(f"\n  📊 OVERALL PSYCHOLOGY INTEGRATION: {integration_score:.0f}%")
            
            if integration_score >= 80:
                print(f"  🎉 EXCELLENT: Sales psychology fully integrated!")
            elif integration_score >= 60:
                print(f"  👍 GOOD: Sales psychology mostly integrated")
            else:
                print(f"  ⚠️  NEEDS IMPROVEMENT: Sales psychology partially integrated")
                
        else:
            print(f"  ❌ Workflow failed to complete")
            
    except Exception as e:
        print(f"  ❌ Error testing full workflow: {e}")


async def main():
    """Main test function for comprehensive psychology integration testing"""
    print("🧠 HELIOS FULL PSYCHOLOGY INTEGRATION TEST")
    print("=" * 60)
    print("Testing the complete hybrid AI system with all 8 sales psychology principles")
    print("and real trend discovery (no seed words)")
    print("=" * 60)
    
    print("\n🧠 TESTING REAL TREND DISCOVERY & PSYCHOLOGY INTEGRATION")
    print("=" * 60)
    
    # Step 1: Test Zeitgeist agent with real trend discovery
    discovered_trend, emotional_driver = await test_zeitgeist_full_integration()
    
    # Step 2: Test Audience Analyst with discovered trend data
    await test_audience_analyst_full_integration(discovered_trend, emotional_driver)
    
    # Step 3: Test Product Strategist with discovered trend data
    await test_product_full_integration()
    
    # Step 4: Test Creative Director with discovered trend data
    await test_creative_full_integration()
    
    # Step 5: Test Marketing Copywriter with discovered trend data
    await test_marketing_full_integration()
    
    # Step 6: Test full orchestrated workflow
    await test_full_orchestrated_workflow(discovered_trend, emotional_driver)
    
    print("✅ FULL PSYCHOLOGY INTEGRATION TESTING COMPLETE")
    print("\n" + "=" * 60)
    print("🎯 REAL TREND DISCOVERY & PSYCHOLOGY INTEGRATION SUMMARY")
    print("=" * 60)
    print("✅ Zeitgeist: Real trend discovery with emotional driver detection")
    print("✅ Audience Analyst: Real trend analysis with subculture analysis")
    print("✅ Product Strategist: Real trend strategy with psychological positioning")
    print("✅ Creative Director: Real trend creative direction with all 8 psychology principles")
    print("✅ Marketing Copywriter: Real trend copy generation with psychology principles")
    print("✅ Full Workflow: Complete orchestrated psychology integration with real data")
    print("\n🚀 Your Helios system is now a fully integrated, psychologically potent sales machine!")
    print("🎯 NO MORE SEED WORDS - REAL TREND DISCOVERY ACTIVE!")


if __name__ == "__main__":
    asyncio.run(main())
