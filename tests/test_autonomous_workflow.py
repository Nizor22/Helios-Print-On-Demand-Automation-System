#!/usr/bin/env python3
"""
Test script for the new autonomous workflow system
Demonstrates the end-to-end AI-driven trend-to-product pipeline
"""

import asyncio
import json
from helios.config import load_config
from helios.services.autonomous_workflow import AutonomousWorkflow
from helios.services.zeitgeist_finder import ZeitgeistFinder
from helios.services.product_strategy import ProductStrategist

async def test_workflow_components():
    """Test individual workflow components"""
    print("🧪 Testing Autonomous Workflow Components")
    print("=" * 60)
    
    try:
        # Load configuration
        config = load_config()
        print(f"✅ Configuration loaded: {config.google_cloud_project}")
        
        # Test 1: Workflow Status
        print("\n🔍 Test 1: Workflow Status Check")
        workflow = AutonomousWorkflow(config)
        status = await workflow.get_workflow_status()
        print(f"   Overall Health: {'✅' if status['overall_health'] else '❌'}")
        print(f"   Components: {json.dumps(status['components'], indent=4)}")
        
        # Test 2: Trend Discovery
        print("\n🔍 Test 2: Trend Discovery")
        zeitgeist = ZeitgeistFinder(config)
        trends = await zeitgeist.discover_current_trends()
        print(f"   Primary Trend: {trends.primary_trend.keyword}")
        print(f"   Category: {trends.primary_trend.category}")
        print(f"   Source: {trends.primary_trend.source}")
        print(f"   Confidence: {trends.primary_trend.confidence_score:.2f}")
        print(f"   Market Opportunity: {trends.market_opportunity[:100]}...")
        
        # Test 3: Product Strategy
        print("\n🔍 Test 3: Product Strategy")
        strategist = ProductStrategist(config)
        catalog = await strategist.get_cached_catalog()
        print(f"   Catalog Products: {len(catalog)}")
        if catalog:
            print(f"   Sample Product: {catalog[0].name}")
            print(f"   Categories: {list(set(p.category for p in catalog))}")
        
        # Test 4: Component Testing
        print("\n🔍 Test 4: Component Testing")
        component_tests = await workflow.get_workflow_status()
        print(f"   Trend Discovery: {'✅' if component_tests['components']['trend_discovery'] else '❌'}")
        print(f"   Product Strategy: {'✅' if component_tests['components']['product_strategy'] else '❌'}")
        print(f"   Image Generation: {'✅' if component_tests['components']['image_generation'] else '❌'}")
        print(f"   Printify Integration: {'✅' if component_tests['components']['printify_integration'] else '❌'}")
        
        print("\n🎉 All component tests completed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Component testing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_trend_discovery():
    """Test trend discovery specifically"""
    print("\n🔍 Testing Trend Discovery in Detail")
    print("=" * 60)
    
    try:
        config = load_config()
        zeitgeist = ZeitgeistFinder(config)
        
        # Test with specific categories
        categories = ["technology", "lifestyle"]
        geo_locations = ["US", "CA"]
        
        print(f"   Categories: {categories}")
        print(f"   Locations: {geo_locations}")
        
        analysis = await zeitgeist.discover_current_trends(categories, geo_locations)
        
        print(f"\n📊 Trend Analysis Results:")
        print(f"   Primary Trend: {analysis.primary_trend.keyword}")
        print(f"   Category: {analysis.primary_trend.category}")
        print(f"   Source: {analysis.primary_trend.source}")
        print(f"   Confidence: {analysis.primary_trend.confidence_score:.2f}")
        print(f"   Market Opportunity: {analysis.market_opportunity}")
        print(f"   Design Inspiration: {analysis.design_inspiration}")
        print(f"   Target Audience: {analysis.target_audience}")
        
        if analysis.related_trends:
            print(f"\n📈 Related Trends:")
            for i, trend in enumerate(analysis.related_trends[:3], 1):
                print(f"   {i}. {trend.keyword} ({trend.category}) - Score: {trend.confidence_score:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Trend discovery test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_product_strategy():
    """Test product strategy specifically"""
    print("\n🎯 Testing Product Strategy in Detail")
    print("=" * 60)
    
    try:
        config = load_config()
        strategist = ProductStrategist(config)
        
        # Get catalog
        print("   Fetching product catalog...")
        catalog = await strategist.get_cached_catalog()
        print(f"   ✅ Catalog loaded: {len(catalog)} products")
        
        if catalog:
            # Show sample products
            print(f"\n📋 Sample Products:")
            for i, product in enumerate(catalog[:5], 1):
                print(f"   {i}. {product.name}")
                print(f"      Category: {product.category}")
                print(f"      Blueprint ID: {product.blueprint_id}")
                print(f"      Provider ID: {product.print_provider_id}")
                print(f"      Print Areas: {len(product.print_areas)}")
                print()
        
        return True
        
    except Exception as e:
        print(f"❌ Product strategy test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🚀 Autonomous Workflow System Test")
    print("=" * 60)
    
    try:
        # Test 1: Component testing
        success1 = await test_workflow_components()
        
        # Test 2: Trend discovery
        success2 = await test_trend_discovery()
        
        # Test 3: Product strategy
        success3 = await test_product_strategy()
        
        # Summary
        print("\n📊 Test Summary")
        print("=" * 60)
        print(f"   Component Testing: {'✅ PASS' if success1 else '❌ FAIL'}")
        print(f"   Trend Discovery: {'✅ PASS' if success2 else '❌ FAIL'}")
        print(f"   Product Strategy: {'✅ PASS' if success3 else '❌ FAIL'}")
        
        overall_success = success1 and success2 and success3
        
        if overall_success:
            print("\n🎉 All tests passed! The autonomous workflow system is ready.")
            print("\n📋 Next Steps:")
            print("   1. Deploy the updated CEO service to Cloud Run")
            print("   2. Test the new /autonomous/* endpoints")
            print("   3. Run a full autonomous workflow")
            print("   4. Monitor the results in Printify")
        else:
            print("\n⚠️ Some tests failed. Please review the errors above.")
        
        return overall_success
        
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(main())
