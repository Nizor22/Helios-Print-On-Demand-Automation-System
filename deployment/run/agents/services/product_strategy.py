#!/usr/bin/env python3
"""
Product Strategy Module
AI-powered product selection from Printify catalog based on design concepts
"""

import asyncio
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from loguru import logger

from ..config import HeliosConfig
from ..services.google_cloud.vertex_ai_client import VertexAIClient
from ..services.external_apis.printify_client import PrintifyAPIClient


@dataclass
class ProductRecommendation:
    """Product recommendation with reasoning"""
    blueprint_id: int
    print_provider_id: int
    product_name: str
    confidence_score: float
    reasoning: str
    design_compatibility: str
    market_potential: str


@dataclass
class CatalogProduct:
    """Simplified catalog product for AI analysis"""
    blueprint_id: int
    print_provider_id: int
    name: str
    category: str
    description: str
    tags: List[str]
    print_areas: List[str]


class ProductStrategist:
    """AI-powered product selection strategist"""
    
    def __init__(self, config: HeliosConfig):
        self.config = config
        self.vertex_ai = VertexAIClient(config)
        self.printify_client = PrintifyAPIClient(
            api_token=config.printify_api_token,
            shop_id=config.printify_shop_id
        )
        self.catalog_cache: Optional[List[CatalogProduct]] = None
        self.cache_timestamp: Optional[float] = None
        self.cache_ttl = 3600  # 1 hour cache
        
    async def get_cached_catalog(self) -> List[CatalogProduct]:
        """Get cached catalog or fetch fresh data"""
        import time
        
        current_time = time.time()
        
        # Return cached catalog if still valid
        if (self.catalog_cache and self.cache_timestamp and 
            current_time - self.cache_timestamp < self.cache_ttl):
            logger.info(f"📚 Using cached catalog ({len(self.catalog_cache)} products)")
            return self.catalog_cache
        
        # Fetch fresh catalog
        logger.info("🔄 Fetching fresh Printify catalog...")
        try:
            # Get blueprints (product types)
            blueprints_response = await self.printify_client.get_blueprints()
            
            if not blueprints_response.get('success'):
                raise ValueError(f"Failed to get blueprints: {blueprints_response.get('error', 'Unknown error')}")
            
            blueprints = blueprints_response.get('data', [])
            
            if not blueprints:
                raise ValueError("No blueprints available")
            
            # Get print providers for each blueprint
            catalog_products = []
            
            for blueprint in blueprints[:10]:  # Limit to top 10 for performance
                try:
                    providers_response = await self.printify_client.get_print_providers(blueprint['id'])
                    
                    if not providers_response.get('success'):
                        logger.warning(f"⚠️ Failed to get providers for blueprint {blueprint['id']}: {providers_response.get('error', 'Unknown error')}")
                        continue
                    
                    providers = providers_response.get('data', [])
                    
                    for provider in providers[:3]:  # Top 3 providers per blueprint
                        product = CatalogProduct(
                            blueprint_id=blueprint['id'],
                            print_provider_id=provider['id'],
                            name=f"{blueprint['title']} - {provider['title']}",
                            category=blueprint.get('category', 'Unknown'),
                            description=blueprint.get('description', ''),
                            tags=blueprint.get('tags', []),
                            print_areas=blueprint.get('print_areas', [])
                        )
                        catalog_products.append(product)
                        
                except Exception as e:
                    logger.warning(f"⚠️ Failed to get providers for blueprint {blueprint['id']}: {e}")
                    continue
            
            # Cache the results
            self.catalog_cache = catalog_products
            self.cache_timestamp = current_time
            
            logger.info(f"✅ Catalog updated: {len(catalog_products)} products cached")
            return catalog_products
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch catalog: {e}")
            # Return cached data if available, even if expired
            if self.catalog_cache:
                logger.warning("⚠️ Using expired cache due to fetch failure")
                return self.catalog_cache
            raise
    
    async def select_best_product(self, design_concept: str, trend_keyword: str) -> ProductRecommendation:
        """AI-powered product selection based on design concept and trend"""
        
        try:
            # Get catalog
            catalog = await self.get_cached_catalog()
            
            if not catalog:
                raise ValueError("No catalog products available")
            
            # Create AI prompt for product selection
            prompt = self._create_product_selection_prompt(design_concept, trend_keyword, catalog)
            
            # Get AI recommendation
            ai_response = await self.vertex_ai.generate_text(
                prompt=prompt,
                model="gemini-1.5-flash",
                max_tokens=2000,
                temperature=0.3
            )
            
            # Parse AI response
            recommendation = self._parse_ai_recommendation(ai_response, catalog)
            
            logger.info(f"🎯 AI selected product: {recommendation.product_name} (Score: {recommendation.confidence_score:.2f})")
            
            return recommendation
            
        except Exception as e:
            logger.error(f"❌ Product selection failed: {e}")
            # Fallback to best-selling product
            return await self._fallback_product_selection(catalog)
    
    def _create_product_selection_prompt(self, design_concept: str, trend_keyword: str, catalog: List[CatalogProduct]) -> str:
        """Create AI prompt for product selection"""
        
        catalog_summary = []
        for product in catalog:
            catalog_summary.append({
                'id': f"{product.blueprint_id}-{product.print_provider_id}",
                'name': product.name,
                'category': product.category,
                'tags': product.tags,
                'print_areas': product.print_areas
            })
        
        prompt = f"""
You are an expert product strategist for a print-on-demand business. Your task is to select the BEST product from the available catalog that would work perfectly with a given design concept and trend.

DESIGN CONCEPT: {design_concept}
TREND KEYWORD: {trend_keyword}

AVAILABLE PRODUCTS:
{json.dumps(catalog_summary, indent=2)}

ANALYSIS REQUIREMENTS:
1. Analyze the design concept and trend keyword
2. Consider visual appeal, market demand, and print-on-demand suitability
3. Evaluate which product would showcase the design best
4. Consider print areas and technical limitations
5. Assess market potential and customer appeal

RESPONSE FORMAT (JSON only):
{{
    "selected_product_id": "blueprint_id-print_provider_id",
    "confidence_score": 0.95,
    "reasoning": "Detailed explanation of why this product is the best choice",
    "design_compatibility": "How well the design works with this product",
    "market_potential": "Market opportunity and customer appeal assessment"
}}

Select the product that would create the most compelling, marketable item. Be strategic and consider both artistic and commercial factors.
"""
        return prompt
    
    def _parse_ai_recommendation(self, ai_response: str, catalog: List[CatalogProduct]) -> ProductRecommendation:
        """Parse AI response into structured recommendation"""
        
        try:
            # Extract JSON from response
            if isinstance(ai_response, dict):
                response_data = ai_response.get('text', '')
            else:
                response_data = str(ai_response)
            
            # Find JSON in the response
            start_idx = response_data.find('{')
            end_idx = response_data.rfind('}') + 1
            
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No JSON found in AI response")
            
            json_str = response_data[start_idx:end_idx]
            data = json.loads(json_str)
            
            # Extract product ID
            product_id = data['selected_product_id']
            blueprint_id, print_provider_id = map(int, product_id.split('-'))
            
            # Find product in catalog
            product = next(
                (p for p in catalog if p.blueprint_id == blueprint_id and p.print_provider_id == print_provider_id),
                None
            )
            
            if not product:
                raise ValueError(f"Selected product {product_id} not found in catalog")
            
            return ProductRecommendation(
                blueprint_id=blueprint_id,
                print_provider_id=print_provider_id,
                product_name=product.name,
                confidence_score=float(data.get('confidence_score', 0.8)),
                reasoning=data.get('reasoning', 'AI analysis'),
                design_compatibility=data.get('design_compatibility', 'Compatible'),
                market_potential=data.get('market_potential', 'Good potential')
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to parse AI recommendation: {e}")
            raise ValueError(f"Invalid AI response format: {e}")
    
    async def _fallback_product_selection(self, catalog: List[CatalogProduct]) -> ProductRecommendation:
        """Fallback to best-selling product types"""
        
        # Prefer t-shirts and hoodies as fallback
        preferred_categories = ['t-shirt', 'hoodie', 'sweatshirt']
        
        for category in preferred_categories:
            for product in catalog:
                if category.lower() in product.name.lower():
                    logger.info(f"🔄 Fallback selection: {product.name}")
                    return ProductRecommendation(
                        blueprint_id=product.blueprint_id,
                        print_provider_id=product.print_provider_id,
                        product_name=product.name,
                        confidence_score=0.6,
                        reasoning="Fallback selection based on product category",
                        design_compatibility="Standard compatibility",
                        market_potential="Good market potential"
                    )
        
        # Last resort: first available product
        product = catalog[0]
        logger.warning(f"⚠️ Emergency fallback: {product.name}")
        return ProductRecommendation(
            blueprint_id=product.blueprint_id,
            print_provider_id=product.print_provider_id,
            product_name=product.name,
            confidence_score=0.5,
            reasoning="Emergency fallback selection",
            design_compatibility="Unknown compatibility",
            market_potential="Unknown potential"
        )
    
    async def get_product_variants(self, blueprint_id: int, print_provider_id: int) -> List[Dict]:
        """Get available variants for selected product"""
        
        try:
            variants = await self.printify_client.get_variants(blueprint_id, print_provider_id)
            logger.info(f"📋 Found {len(variants)} variants for product {blueprint_id}-{print_provider_id}")
            return variants
        except Exception as e:
            logger.error(f"❌ Failed to get variants: {e}")
            return []
    
    async def validate_product_selection(self, recommendation: ProductRecommendation) -> bool:
        """Validate that the selected product is available and suitable"""
        
        try:
            # Check if variants are available
            variants = await self.get_product_variants(
                recommendation.blueprint_id, 
                recommendation.print_provider_id
            )
            
            if not variants:
                logger.warning(f"⚠️ No variants available for {recommendation.product_name}")
                return False
            
            # Check if product is in stock (basic validation)
            available_variants = [v for v in variants if v.get('is_enabled', True)]
            
            if not available_variants:
                logger.warning(f"⚠️ No enabled variants for {recommendation.product_name}")
                return False
            
            logger.info(f"✅ Product validation passed: {len(available_variants)} variants available")
            return True
            
        except Exception as e:
            logger.error(f"❌ Product validation failed: {e}")
            return False
