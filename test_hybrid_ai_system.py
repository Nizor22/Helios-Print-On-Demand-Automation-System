#!/usr/bin/env python3
"""
Test Script for Helios Hybrid AI System

This script tests the new hybrid AI + rules architecture with cost optimization.
"""

import asyncio
import time
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from helios.agents.hybrid_ai_orchestrator import HybridAIOrchestrator, OrchestrationTask
from helios.config import load_config


async def test_hybrid_ai_system():
    """Test the complete hybrid AI system"""
    print("🚀 Testing Helios Hybrid AI System")
    print("=" * 50)
    
    try:
        # Load configuration
        print("📋 Loading configuration...")
        config = load_config()
        
        # Check hybrid AI system configuration
        if not config.enable_hybrid_ai_system:
            print("❌ Hybrid AI system is not enabled in configuration")
            return False
        
        print(f"✅ Hybrid AI System: {config.enable_hybrid_ai_system}")
        print(f"✅ Thinking Budget Control: {config.enable_thinking_budget_control}")
        print(f"✅ Cost Optimization: {config.enable_cost_optimization}")
        print(f"✅ AI Model Strategy: {config.ai_model_selection_strategy}")
        
        # Initialize the hybrid AI orchestrator
        print("\n🤖 Initializing Hybrid AI Orchestrator...")
        orchestrator = HybridAIOrchestrator()
        
        if not orchestrator.agents:
            print("❌ No agents were initialized")
            return False
        
        print(f"✅ Initialized {len(orchestrator.agents)} agents:")
        for agent_name, agent in orchestrator.agents.items():
            print(f"   - {agent_name}: {type(agent).__name__}")
        
        # Test 1: Trend Discovery Task
        print("\n🔍 Test 1: Trend Discovery Task")
        print("-" * 30)
        
        trend_task = OrchestrationTask(
            task_type="trend_discovery",
            priority="high",
            complexity=5,
            thinking_required=False,
            data={"seed": "vintage gaming aesthetic"},
            expected_output=["trends", "opportunity_scores", "keywords"],
            quality_gates=["trend_validation", "opportunity_threshold"]
        )
        
        start_time = time.time()
        trend_result = await orchestrator.orchestrate_task(trend_task)
        execution_time = time.time() - start_time
        
        print(f"✅ Trend Discovery completed in {execution_time:.2f}s")
        print(f"   Status: {trend_result.status}")
        print(f"   Execution Time: {trend_result.execution_time_ms}ms")
        print(f"   Total Cost: ${trend_result.cost_metrics.get('total_cost', 0):.4f}")
        print(f"   Model Used: {trend_result.results.get('main_execution', {}).get('model_used', 'unknown')}")
        
        # Test 2: Audience Analysis Task
        print("\n👥 Test 2: Audience Analysis Task")
        print("-" * 30)
        
        audience_task = OrchestrationTask(
            task_type="audience_analysis",
            priority="medium",
            complexity=6,
            thinking_required=False,
            data={"trend_data": trend_result.results.get("main_execution", {}).get("ai_analysis", {})},
            expected_output=["audience_personas", "targeting_criteria"],
            quality_gates=["audience_validation", "confidence_threshold"]
        )
        
        start_time = time.time()
        audience_result = await orchestrator.orchestrate_task(audience_task)
        execution_time = time.time() - start_time
        
        print(f"✅ Audience Analysis completed in {execution_time:.2f}s")
        print(f"   Status: {audience_result.status}")
        print(f"   Execution Time: {audience_result.execution_time_ms}ms")
        print(f"   Total Cost: ${audience_result.cost_metrics.get('total_cost', 0):.4f}")
        print(f"   Model Used: {audience_result.results.get('main_execution', {}).get('model_used', 'unknown')}")
        
        # Test 3: Full Pipeline
        print("\n🔄 Test 3: Full Pipeline Execution")
        print("-" * 30)
        
        start_time = time.time()
        pipeline_result = await orchestrator.run_full_pipeline("minimalist quote designs")
        execution_time = time.time() - start_time
        
        print(f"✅ Full Pipeline completed in {execution_time:.2f}s")
        print(f"   Status: {pipeline_result.get('status', 'unknown')}")
        print(f"   Total Cost: ${pipeline_result.get('total_cost', 0):.4f}")
        print(f"   Total Execution Time: {pipeline_result.get('total_execution_time', 0)}ms")
        
        # Performance Summary
        print("\n📊 Performance Summary")
        print("=" * 50)
        
        total_cost = (
            trend_result.cost_metrics.get('total_cost', 0) +
            audience_result.cost_metrics.get('total_cost', 0) +
            pipeline_result.get('total_cost', 0)
        )
        
        total_time = (
            trend_result.execution_time_ms +
            audience_result.execution_time_ms +
            pipeline_result.get('total_execution_time', 0)
        )
        
        print(f"Total Tasks Executed: {orchestrator.performance_metrics['total_tasks']}")
        print(f"Successful Tasks: {orchestrator.performance_metrics['successful_tasks']}")
        print(f"Failed Tasks: {orchestrator.performance_metrics['failed_tasks']}")
        print(f"Success Rate: {(orchestrator.performance_metrics['successful_tasks'] / max(orchestrator.performance_metrics['total_tasks'], 1)) * 100:.1f}%")
        print(f"Total Cost: ${total_cost:.4f}")
        print(f"Total Execution Time: {total_time}ms")
        print(f"Average Cost per Task: ${total_cost / max(orchestrator.performance_metrics['total_tasks'], 1):.4f}")
        
        # Cost Analysis
        print("\n💰 Cost Analysis")
        print("-" * 30)
        
        if total_cost > config.ai_cost_per_day_target:
            print(f"⚠️  Total cost (${total_cost:.4f}) exceeds daily target (${config.ai_cost_per_day_target})")
        else:
            print(f"✅ Total cost (${total_cost:.4f}) within daily target (${config.ai_cost_per_day_target})")
        
        if total_cost > config.ai_cost_per_product_target * orchestrator.performance_metrics['total_tasks']:
            print(f"⚠️  Cost per task exceeds target (${config.ai_cost_per_product_target})")
        else:
            print(f"✅ Cost per task within target (${config.ai_cost_per_product_target})")
        
        # Quality Gates Analysis
        print("\n🔒 Quality Gates Analysis")
        print("-" * 30)
        
        all_results = [trend_result, audience_result]
        quality_passed = 0
        total_quality_gates = 0
        
        for result in all_results:
            if hasattr(result, 'quality_gates'):
                for gate_name, gate_data in result.quality_gates.items():
                    total_quality_gates += 1
                    if gate_data.get('passed', False):
                        quality_passed += 1
        
        if total_quality_gates > 0:
            quality_rate = (quality_passed / total_quality_gates) * 100
            print(f"Quality Gates Passed: {quality_passed}/{total_quality_gates} ({quality_rate:.1f}%)")
            
            if quality_rate >= 90:
                print("✅ Excellent quality performance")
            elif quality_rate >= 80:
                print("✅ Good quality performance")
            elif quality_rate >= 70:
                print("⚠️  Acceptable quality performance")
            else:
                print("❌ Quality performance needs improvement")
        
        print("\n🎉 Hybrid AI System Test Completed Successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_individual_agents():
    """Test individual agents separately"""
    print("\n🧪 Testing Individual Agents")
    print("=" * 50)
    
    try:
        from helios.agents.zeitgeist import ZeitgeistAgent
        from helios.agents.audience import AudienceAnalyst
        from helios.agents.ceo import HeliosCEO
        
        # Test Zeitgeist Agent
        print("\n🔍 Testing Zeitgeist Agent...")
        zeitgeist = ZeitgeistAgent()
        trend_result = await zeitgeist.run("cyberpunk aesthetic")
        print(f"✅ Zeitgeist: Found {len(trend_result.get('keywords', []))} keywords")
        print(f"   Opportunity Score: {trend_result.get('opportunity_score', 0)}")
        print(f"   Confidence: {trend_result.get('confidence_level', 0)}")
        
        # Test Audience Analyst
        print("\n👥 Testing Audience Analyst...")
        audience = AudienceAnalyst()
        audience_result = await audience.run(trend_result)
        print(f"✅ Audience Analysis: {audience_result.primary_persona.demographic_cluster}")
        print(f"   Confidence: {audience_result.confidence_score}")
        
        # Test CEO Agent
        print("\n👑 Testing CEO Agent...")
        ceo = HeliosCEO()
        ceo_context = {
            "task_type": "system_optimization",
            "priority": "high",
            "system_metrics": {"total_tasks": 10, "success_rate": 0.9},
            "trend_count": 5,
            "pending_tasks": 2,
            "current_kpis": {"average_cost": 0.05, "average_execution_time": 1500},
            "request_details": "Optimize system performance",
            "trend_data": trend_result,
            "resource_status": "Available"
        }
        ceo_result = await ceo.process_hybrid_task(ceo_context, 8)
        print(f"✅ CEO Planning: Confidence {ceo_result.confidence_score}")
        print(f"   Model Used: {ceo_result.model_used}")
        
        return True
        
    except Exception as e:
        print(f"❌ Individual agent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main test function"""
    print("🚀 Helios Hybrid AI System Test Suite")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not Path("helios").exists():
        print("❌ Error: Please run this script from the project root directory")
        print("   Expected to find 'helios' directory")
        return 1
    
    # Run tests
    success = True
    
    # Test individual agents
    try:
        success &= asyncio.run(test_individual_agents())
    except Exception as e:
        print(f"❌ Individual agent test failed: {e}")
        success = False
    
    # Test full system
    try:
        success &= asyncio.run(test_hybrid_ai_system())
    except Exception as e:
        print(f"❌ Full system test failed: {e}")
        success = False
    
    # Final result
    print("\n" + "=" * 60)
    if success:
        print("🎉 ALL TESTS PASSED! Hybrid AI System is working correctly.")
        return 0
    else:
        print("❌ SOME TESTS FAILED! Please check the errors above.")
        return 1


if __name__ == "__main__":
    exit(main())
