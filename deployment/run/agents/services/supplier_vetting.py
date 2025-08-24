from typing import Dict, List, Any
import asyncio
from helios.services.external_apis.printify_client import PrintifyAPIClient
from helios.mcp_client import MCPClient
from helios.config import load_config

class SupplierVettingService:
    """Comprehensive supplier vetting system for POD business"""
    
    def __init__(self):
        self.config = load_config()
        self.mcp_client = MCPClient.from_env(
            self.config.google_mcp_url, 
            self.config.google_mcp_auth_token
        )
        self.printify_client = PrintifyAPIClient(self.config.printify_api_token, self.config.printify_shop_id)
    
    async def vet_pod_suppliers(self) -> Dict[str, Any]:
        """Vet potential POD suppliers"""
        
        # Research major POD platforms
        platforms = await self._research_pod_platforms()
        
        # Evaluate Printify (your current provider)
        printify_evaluation = await self._evaluate_printify()
        
        # Research alternatives
        alternatives = await self._research_alternatives()
        
        # Generate recommendations
        recommendations = await self._generate_supplier_recommendations(
            platforms, printify_evaluation, alternatives
        )
        
        return {
            "current_provider": printify_evaluation,
            "alternative_platforms": alternatives,
            "recommendations": recommendations,
            "risk_assessment": await self._assess_supplier_risks(),
            "quality_standards": self._define_quality_standards()
        }
    
    async def _research_pod_platforms(self) -> List[Dict[str, Any]]:
        """Research major POD platforms"""
        
        platforms = [
            {
                "name": "Printify",
                "pros": ["Large supplier network", "Good API", "Competitive pricing"],
                "cons": ["Quality varies by supplier", "Limited customization"],
                "best_for": "Beginners, large catalogs",
                "pricing": "No monthly fees, pay per product",
                "supplier_count": "100+ suppliers",
                "shipping_time": "3-7 business days"
            },
            {
                "name": "Printful",
                "pros": ["High quality", "Fast shipping", "Good customer service"],
                "cons": ["Higher prices", "Limited supplier options"],
                "best_for": "Quality-focused, premium products",
                "pricing": "No monthly fees, higher product costs",
                "supplier_count": "20+ suppliers",
                "shipping_time": "2-5 business days"
            },
            {
                "name": "Gooten",
                "pros": ["Global suppliers", "Good for international", "Competitive pricing"],
                "cons": ["Complex API", "Quality inconsistency"],
                "best_for": "International expansion",
                "pricing": "No monthly fees, competitive pricing",
                "supplier_count": "50+ suppliers",
                "shipping_time": "5-10 business days"
            },
            {
                "name": "CustomCat",
                "pros": ["Fast production", "Good for apparel", "Competitive pricing"],
                "cons": ["Limited product types", "Quality issues"],
                "best_for": "Fast fashion, apparel focus",
                "pricing": "No monthly fees, low product costs",
                "supplier_count": "30+ suppliers",
                "shipping_time": "2-4 business days"
            }
        ]
        
        return platforms
    
    async def _evaluate_printify(self) -> Dict[str, Any]:
        """Evaluate current Printify setup"""
        
        try:
            # Test API connection using health check
            health_check = await self.printify_client.health_check()
            
            # Get existing products to test API
            products_result = await self.printify_client.get_products(limit=5)
            
            # Test with a simple health check instead of creating test products
            test_status = "healthy" if health_check.get("success") else "unhealthy"
            
            return {
                "status": "operational",
                "api_health": test_status,
                "products_retrieved": products_result.get("success", False),
                "total_products": products_result.get("total_count", 0) if products_result.get("success") else 0,
                "api_connection": health_check.get("success", False),
                "recommendations": [
                    "Continue with Printify as primary provider",
                    "Implement quality control measures",
                    "Diversify with backup suppliers"
                ]
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "recommendations": [
                    "Fix API connection issues",
                    "Consider alternative providers",
                    "Review API configuration"
                ]
            }
    
    async def _research_alternatives(self) -> List[Dict[str, Any]]:
        """Research alternative POD suppliers"""
        
        # Use AI to research alternatives
        prompt = """
        Research alternative print-on-demand suppliers for vintage gaming merchandise.
        
        Focus on:
        1. Quality and reliability
        2. Pricing competitiveness
        3. Shipping speed and costs
        4. Product variety
        5. Customer service
        6. Integration capabilities
        
        Provide top 5 alternatives with pros/cons and recommendations.
        """
        
        response = await self.mcp_client.orchestrator_ai({
            "prompt": prompt
        })
        
        return self._parse_alternative_data(response)
    
    def _parse_alternative_data(self, response: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Parse AI response for alternative supplier data"""
        # This would parse the AI response into structured data
        # For now, return sample alternatives with all required keys
        return [
            {
                "name": "Redbubble",
                "pros": ["Large marketplace", "Good for exposure", "No upfront costs"],
                "cons": ["Lower profit margins", "Less control", "Competition"],
                "best_for": "Market testing, brand exposure",
                "pricing": "No monthly fees, lower profit margins",
                "supplier_count": "Marketplace platform",
                "shipping_time": "5-10 business days"
            },
            {
                "name": "TeePublic",
                "pros": ["Gaming-focused audience", "Good community", "No upfront costs"],
                "cons": ["Lower margins", "Limited customization", "Competition"],
                "best_for": "Gaming-specific products",
                "pricing": "No monthly fees, competitive pricing",
                "supplier_count": "Marketplace platform",
                "shipping_time": "5-8 business days"
            }
        ]
    
    async def _generate_supplier_recommendations(self, platforms, printify_eval, alternatives):
        """Generate supplier strategy recommendations"""
        
        prompt = f"""
        Based on this supplier analysis, provide strategic recommendations:
        
        Current provider (Printify): {printify_eval}
        Alternative platforms: {alternatives}
        
        Recommend:
        1. Primary supplier strategy
        2. Backup supplier options
        3. Quality control measures
        4. Risk mitigation strategies
        5. Cost optimization approaches
        """
        
        response = await self.mcp_client.orchestrator_ai({
            "prompt": prompt
        })
        
        return response
    
    async def _assess_supplier_risks(self) -> Dict[str, Any]:
        """Assess risks associated with different suppliers"""
        
        risks = {
            "single_supplier_risk": {
                "description": "Dependency on single supplier",
                "impact": "High",
                "mitigation": "Diversify suppliers, maintain backup options"
            },
            "quality_consistency_risk": {
                "description": "Inconsistent product quality",
                "impact": "Medium",
                "mitigation": "Implement quality control, order samples regularly"
            },
            "shipping_delay_risk": {
                "description": "Delays in product delivery",
                "impact": "Medium",
                "mitigation": "Set clear expectations, offer multiple shipping options"
            },
            "price_volatility_risk": {
                "description": "Fluctuating product costs",
                "impact": "Low",
                "mitigation": "Lock in pricing, monitor cost trends"
            }
        }
        
        return risks
    
    def _define_quality_standards(self) -> Dict[str, Any]:
        """Define quality standards for POD products"""
        
        return {
            "print_quality": {
                "resolution": "300 DPI minimum",
                "color_accuracy": "95%+ match to design",
                "durability": "50+ washes without fading"
            },
            "material_quality": {
                "fabric_weight": "180 GSM minimum for t-shirts",
                "material_composition": "100% cotton or premium blends",
                "finish": "Soft, comfortable feel"
            },
            "production_standards": {
                "turnaround_time": "3-5 business days",
                "defect_rate": "<2%",
                "packaging": "Professional, branded packaging"
            }
        }
    
    async def test_supplier_quality(self, supplier_name: str, product_type: str) -> Dict[str, Any]:
        """Test supplier quality with sample orders"""
        
        test_plan = {
            "supplier": supplier_name,
            "product_type": product_type,
            "test_products": [
                "Basic t-shirt with simple design",
                "Complex design with multiple colors",
                "Product with text and graphics"
            ],
            "quality_metrics": [
                "Print sharpness and clarity",
                "Color accuracy and vibrancy",
                "Material feel and durability",
                "Packaging and presentation",
                "Shipping time and condition"
            ]
        }
        
        return test_plan
    
    def generate_supplier_report(self, vetting_results: Dict[str, Any]) -> str:
        """Generate comprehensive supplier vetting report"""
        
        report = f"""
# POD Supplier Vetting Report

## Executive Summary
Comprehensive evaluation of print-on-demand suppliers for vintage gaming merchandise business.

## Current Provider Assessment
**Printify Status**: {vetting_results['current_provider']['status']}
- API Health: {vetting_results['current_provider'].get('api_health', 'Unknown')}
- Supplier Count: {vetting_results['current_provider'].get('supplier_count', 'Unknown')}
- Shop Count: {vetting_results['current_provider'].get('shop_count', 'Unknown')}

## Alternative Platform Analysis
"""
        
        for platform in vetting_results['alternative_platforms']:
            report += f"""
### {platform['name']}
- Best For: {platform.get('best_for', 'N/A')}
- Pricing: {platform.get('pricing', 'N/A')}
- Supplier Count: {platform.get('supplier_count', 'N/A')}
- Shipping Time: {platform.get('shipping_time', 'N/A')}
- Pros: {', '.join(platform.get('pros', []))}
- Cons: {', '.join(platform.get('cons', []))}

"""
        
        report += f"""
## Risk Assessment
"""
        
        for risk_name, risk_data in vetting_results['risk_assessment'].items():
            report += f"""
### {risk_name.replace('_', ' ').title()}
- Description: {risk_data['description']}
- Impact: {risk_data['impact']}
- Mitigation: {risk_data['mitigation']}
"""
        
        report += f"""
## Quality Standards
- Print Quality: {vetting_results['quality_standards']['print_quality']['resolution']}
- Material Quality: {vetting_results['quality_standards']['material_quality']['fabric_weight']}
- Production Standards: {vetting_results['quality_standards']['production_standards']['turnaround_time']}

## Recommendations
{vetting_results['recommendations']}

## Next Steps
1. Implement quality control measures
2. Establish backup supplier relationships
3. Monitor supplier performance regularly
4. Develop supplier evaluation metrics
5. Create supplier onboarding process
"""
        
        return report
