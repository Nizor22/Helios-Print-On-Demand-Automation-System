from __future__ import annotations

import asyncio
from typing import Any, Dict, List


class ProductStrategist:
    def __init__(self, config):
        self.config = config
        self.product_catalog = self._initialize_product_catalog()
    
    def _initialize_product_catalog(self) -> Dict[str, Dict[str, Any]]:
        """Initialize comprehensive product catalog with psychological targeting"""
        return {
            "gen_z": {
                "oversized_tees": {
                    "blueprint_id": 482,
                    "print_provider_id": 1,
                    "historical_success_rate": 0.87,
                    "profit_margin": 0.52,
                    "audience_fit_score": 9.3,
                    "fulfillment_speed": "2-3_days",
                    "colors": ["white", "black", "sage", "cream"],
                    "sizes": ["S", "M", "L", "XL", "2XL"],
                    "psychological_hooks": ["identity_expression", "trend_following", "social_media_ready"]
                },
                "hoodies": {
                    "blueprint_id": 483,
                    "print_provider_id": 1,
                    "historical_success_rate": 0.82,
                    "profit_margin": 0.48,
                    "audience_fit_score": 8.9,
                    "fulfillment_speed": "3-4_days",
                    "colors": ["black", "navy", "olive", "burgundy"],
                    "sizes": ["S", "M", "L", "XL", "2XL"],
                    "psychological_hooks": ["comfort", "style", "seasonal_trends"]
                },
                "phone_cases": {
                    "blueprint_id": 484,
                    "print_provider_id": 1,
                    "historical_success_rate": 0.79,
                    "profit_margin": 0.65,
                    "audience_fit_score": 8.7,
                    "fulfillment_speed": "1-2_days",
                    "colors": ["clear", "black", "white", "transparent"],
                    "sizes": ["iPhone 13", "iPhone 14", "iPhone 15", "Samsung"],
                    "psychological_hooks": ["personalization", "tech_lifestyle", "affordable_luxury"]
                }
            },
            "millennials": {
                "tote_bags": {
                    "blueprint_id": 485,
                    "print_provider_id": 1,
                    "historical_success_rate": 0.85,
                    "profit_margin": 0.58,
                    "audience_fit_score": 9.1,
                    "fulfillment_speed": "2-3_days",
                    "colors": ["natural", "black", "navy", "olive"],
                    "sizes": ["standard", "large"],
                    "psychological_hooks": ["sustainability", "practical_luxury", "eco_conscious"]
                },
                "mugs": {
                    "blueprint_id": 486,
                    "print_provider_id": 1,
                    "historical_success_rate": 0.81,
                    "profit_margin": 0.62,
                    "audience_fit_score": 8.8,
                    "fulfillment_speed": "3-4_days",
                    "colors": ["white", "black", "navy"],
                    "sizes": ["11oz", "15oz"],
                    "psychological_hooks": ["home_comfort", "daily_ritual", "gift_potential"]
                },
                "home_decor": {
                    "blueprint_id": 487,
                    "print_provider_id": 1,
                    "historical_success_rate": 0.78,
                    "profit_margin": 0.55,
                    "audience_fit_score": 8.6,
                    "fulfillment_speed": "4-5_days",
                    "colors": ["neutral", "earth_tones", "pastels"],
                    "sizes": ["various"],
                    "psychological_hooks": ["home_personalization", "aesthetic_lifestyle", "interior_design"]
                }
            },
            "gen_x": {
                "classic_tees": {
                    "blueprint_id": 482,
                    "print_provider_id": 1,
                    "historical_success_rate": 0.83,
                    "profit_margin": 0.45,
                    "audience_fit_score": 8.9,
                    "fulfillment_speed": "2-3_days",
                    "colors": ["white", "black", "navy", "gray"],
                    "sizes": ["M", "L", "XL", "2XL"],
                    "psychological_hooks": ["comfort", "quality", "timeless_style"]
                },
                "caps": {
                    "blueprint_id": 488,
                    "print_provider_id": 1,
                    "historical_success_rate": 0.80,
                    "profit_margin": 0.50,
                    "audience_fit_score": 8.7,
                    "fulfillment_speed": "2-3_days",
                    "colors": ["black", "navy", "gray", "olive"],
                    "sizes": ["one_size"],
                    "psychological_hooks": ["casual_style", "outdoor_lifestyle", "brand_expression"]
                },
                "outdoor_gear": {
                    "blueprint_id": 489,
                    "print_provider_id": 1,
                    "historical_success_rate": 0.76,
                    "profit_margin": 0.42,
                    "audience_fit_score": 8.5,
                    "fulfillment_speed": "3-4_days",
                    "colors": ["earth_tones", "navy", "olive"],
                    "sizes": ["various"],
                    "psychological_hooks": ["adventure_lifestyle", "quality_investment", "outdoor_community"]
                }
            }
        }
    
    async def get_products_async(self) -> List[Dict[str, Any]]:
        """Async version of get_products for parallel processing"""
        # Simulate async operation (in real implementation, this might involve API calls)
        await asyncio.sleep(0.1)  # Minimal delay for async simulation
        return self.get_products()
    
    def get_products(self) -> List[Dict[str, Any]]:
        """Get configured products based on config with enhanced selection logic"""
        # Use configured blueprint if specified
        if self.config.blueprint_id:
            return [self._get_configured_product()]
        
        # Otherwise, return optimized product selection
        return self._get_optimized_products()
    
    def _get_configured_product(self) -> Dict[str, Any]:
        """Get the specifically configured product"""
        return {
            "product_key": "configured_tee",
            "blueprint_id": self.config.blueprint_id,
            "print_provider_id": self.config.print_provider_id or 1,
            "historical_success_rate": 0.84,
            "profit_margin": self.config.min_profit_margin or 0.47,
            "audience_fit_score": 9.1,
            "fulfillment_speed": "2-3_days",
            "colors": self.config.default_colors or ["white"],
            "sizes": self.config.default_sizes or ["M", "L", "XL"],
            "psychological_hooks": ["trend_following", "identity_expression", "social_media_ready"]
        }
    
    def _get_optimized_products(self) -> List[Dict[str, Any]]:
        """Get optimized product selection based on performance data"""
        optimized_products = []
        
        # Select top performers from each demographic
        for demographic, products in self.product_catalog.items():
            # Sort by success rate and profit margin
            sorted_products = sorted(
                products.values(),
                key=lambda x: (x["historical_success_rate"], x["profit_margin"]),
                reverse=True
            )
            
            # Take top 2 products from each demographic
            for product in sorted_products[:2]:
                product_copy = product.copy()
                product_copy["demographic_target"] = demographic
                optimized_products.append(product_copy)
        
        # Sort by overall performance score
        optimized_products.sort(
            key=lambda x: (x["historical_success_rate"] * 0.6 + x["profit_margin"] * 0.4),
            reverse=True
        )
        
        # Return top 6 products
        return optimized_products[:6]
    
    def select_products_for_audience(self, audience_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Select products based on audience analysis with psychological targeting"""
        demographic_cluster = audience_data.get("primary_persona", {}).get("demographic_cluster", "gen_z")
        confidence_score = audience_data.get("confidence_score", 0.7)
        
        # Get products for the identified demographic
        demographic_products = self.product_catalog.get(demographic_cluster, {})
        
        if not demographic_products:
            # Fallback to gen_z if demographic not found
            demographic_products = self.product_catalog.get("gen_z", {})
        
        # Filter by confidence threshold
        if confidence_score >= 0.8:
            # High confidence - use all products
            selected_products = list(demographic_products.values())
        elif confidence_score >= 0.6:
            # Medium confidence - use top 2 products
            sorted_products = sorted(
                demographic_products.values(),
                key=lambda x: x["historical_success_rate"],
                reverse=True
            )
            selected_products = sorted_products[:2]
        else:
            # Low confidence - use only top product
            sorted_products = sorted(
                demographic_products.values(),
                key=lambda x: x["historical_success_rate"],
                reverse=True
            )
            selected_products = sorted_products[:1]
        
        # Add demographic targeting info
        for product in selected_products:
            product["demographic_target"] = demographic_cluster
            product["audience_confidence"] = confidence_score
        
        return selected_products
    
    def run(self, audience_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Enhanced product strategy with psychological marketing integration"""
        selected_products = self.select_products_for_audience(audience_payload)
        
        # Calculate selection confidence based on data quality
        data_quality_score = min(audience_payload.get("confidence_score", 0.7), 1.0)
        selection_confidence = 0.7 + (data_quality_score * 0.3)
        
        return {
            "selected_products": selected_products,
            "selection_confidence": selection_confidence,
            "demographic_target": audience_payload.get("primary_persona", {}).get("demographic_cluster"),
            "psychological_hooks": self._extract_psychological_hooks(selected_products),
            "optimization_recommendations": self._generate_optimization_recommendations(selected_products, audience_payload)
        }
    
    def _extract_psychological_hooks(self, products: List[Dict[str, Any]]) -> List[str]:
        """Extract psychological marketing hooks from selected products"""
        hooks = set()
        for product in products:
            product_hooks = product.get("psychological_hooks", [])
            hooks.update(product_hooks)
        return list(hooks)
    
    def _generate_optimization_recommendations(self, products: List[Dict[str, Any]], audience_data: Dict[str, Any]) -> List[str]:
        """Generate optimization recommendations based on product selection and audience data"""
        recommendations = []
        
        # Check profit margins
        avg_profit_margin = sum(p["profit_margin"] for p in products) / len(products)
        if avg_profit_margin < 0.5:
            recommendations.append("Consider premium pricing strategy to improve margins")
        
        # Check fulfillment speed
        slow_products = [p for p in products if "4-5_days" in p["fulfillment_speed"]]
        if slow_products:
            recommendations.append("Consider faster fulfillment options for better customer experience")
        
        # Check audience fit
        low_fit_products = [p for p in products if p["audience_fit_score"] < 8.5]
        if low_fit_products:
            recommendations.append("Review product selection for better audience alignment")
        
        return recommendations
