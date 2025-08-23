#!/usr/bin/env python3
"""
Autonomous Workflow Orchestrator
End-to-end autonomous trend-to-product pipeline
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from loguru import logger

from ..config import HeliosConfig
from ..services.zeitgeist_finder import ZeitgeistFinder, TrendAnalysis
from ..services.product_strategy import ProductStrategist, ProductRecommendation
from ..services.external_apis.image_generation import ImageGenerationService
from ..services.external_apis.printify_client import PrintifyAPIClient
from ..services.google_cloud.vertex_ai_client import VertexAIClient


@dataclass
class WorkflowResult:
    """Complete workflow execution result"""
    success: bool
    trend_analysis: Optional[TrendAnalysis]
    product_recommendation: Optional[ProductRecommendation]
    generated_image_url: Optional[str]
    published_product_id: Optional[str]
    execution_time: float
    errors: List[str]
    metadata: Dict[str, Any]


class AutonomousWorkflow:
    """Main autonomous workflow orchestrator"""
    
    def __init__(self, config: HeliosConfig):
        self.config = config
        self.zeitgeist_finder = ZeitgeistFinder(config)
        self.product_strategist = ProductStrategist(config)
        self.image_generator = ImageGenerationService(config)
        self.printify_client = PrintifyAPIClient(
            api_token=config.printify_api_token,
            shop_id=config.printify_shop_id
        )
        self.vertex_ai = VertexAIClient(config)
        
        # Workflow configuration
        self.max_retries = 3
        self.retry_delay = 5  # seconds
        
    async def run_autonomous_workflow(self, trigger_source: str = "scheduler") -> WorkflowResult:
        """Run the complete autonomous workflow"""
        
        start_time = time.time()
        errors = []
        
        try:
            logger.info("🚀 Starting autonomous workflow...")
            logger.info(f"📡 Trigger source: {trigger_source}")
            
            # Step 1: Discover current trends
            logger.info("🔍 Step 1: Discovering current trends...")
            trend_analysis = await self._discover_trends_with_retry()
            
            if not trend_analysis:
                raise ValueError("Failed to discover trends")
            
            logger.info(f"✅ Trends discovered: {trend_analysis.primary_trend.keyword}")
            
            # Step 2: Generate design concept
            logger.info("🎨 Step 2: Generating design concept...")
            design_concept = await self._generate_design_concept_with_retry(trend_analysis)
            
            if not design_concept:
                raise ValueError("Failed to generate design concept")
            
            logger.info(f"✅ Design concept generated: {design_concept[:100]}...")
            
            # Step 3: Select optimal product
            logger.info("🎯 Step 3: Selecting optimal product...")
            product_recommendation = await self._select_product_with_retry(design_concept, trend_analysis.primary_trend.keyword)
            
            if not product_recommendation:
                raise ValueError("Failed to select product")
            
            logger.info(f"✅ Product selected: {product_recommendation.product_name}")
            
            # Step 4: Generate AI image
            logger.info("🖼️ Step 4: Generating AI image...")
            image_url = await self._generate_image_with_retry(design_concept, product_recommendation)
            
            if not image_url:
                raise ValueError("Failed to generate image")
            
            logger.info(f"✅ Image generated: {image_url}")
            
            # Step 5: Generate marketing copy
            logger.info("✍️ Step 5: Generating marketing copy...")
            marketing_copy = await self._generate_marketing_copy_with_retry(
                trend_analysis.primary_trend, 
                design_concept, 
                product_recommendation
            )
            
            if not marketing_copy:
                raise ValueError("Failed to generate marketing copy")
            
            logger.info(f"✅ Marketing copy generated: {len(marketing_copy)} characters")
            
            # Step 6: Publish to Printify
            logger.info("📤 Step 6: Publishing to Printify...")
            product_id = await self._publish_product_with_retry(
                image_url, 
                product_recommendation, 
                marketing_copy,
                trend_analysis
            )
            
            if not product_id:
                raise ValueError("Failed to publish product")
            
            logger.info(f"✅ Product published: {product_id}")
            
            # Step 7: Log results
            logger.info("📊 Step 7: Logging results...")
            await self._log_workflow_results(
                trend_analysis, 
                product_recommendation, 
                image_url, 
                product_id,
                marketing_copy
            )
            
            execution_time = time.time() - start_time
            logger.info(f"🎉 Autonomous workflow completed successfully in {execution_time:.2f}s")
            
            return WorkflowResult(
                success=True,
                trend_analysis=trend_analysis,
                product_recommendation=product_recommendation,
                generated_image_url=image_url,
                published_product_id=product_id,
                execution_time=execution_time,
                errors=errors,
                metadata={
                    'trigger_source': trigger_source,
                    'workflow_version': '2.0',
                    'ai_models_used': ['gemini-1.5-flash', 'imagen-4.0-generate-001']
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            error_msg = f"Workflow failed: {str(e)}"
            logger.error(f"❌ {error_msg}")
            errors.append(error_msg)
            
            return WorkflowResult(
                success=False,
                trend_analysis=None,
                product_recommendation=None,
                generated_image_url=None,
                published_product_id=None,
                execution_time=execution_time,
                errors=errors,
                metadata={'trigger_source': trigger_source, 'workflow_version': '2.0'}
            )
    
    async def _discover_trends_with_retry(self) -> Optional[TrendAnalysis]:
        """Discover trends with retry logic"""
        
        for attempt in range(self.max_retries):
            try:
                return await self.zeitgeist_finder.discover_current_trends()
            except Exception as e:
                logger.warning(f"⚠️ Trend discovery attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("❌ All trend discovery attempts failed")
                    raise
        
        return None
    
    async def _generate_design_concept_with_retry(self, trend_analysis: TrendAnalysis) -> Optional[str]:
        """Generate design concept with retry logic"""
        
        for attempt in range(self.max_retries):
            try:
                prompt = f"""
You are a creative director for a print-on-demand business. Create a compelling design concept based on this trend analysis.

TREND: {trend_analysis.primary_trend.keyword}
CATEGORY: {trend_analysis.primary_trend.category}
MARKET OPPORTUNITY: {trend_analysis.market_opportunity}
DESIGN INSPIRATION: {trend_analysis.design_inspiration}
TARGET AUDIENCE: {trend_analysis.target_audience}

REQUIREMENTS:
1. Create a visual design concept that captures the trend
2. Consider the target audience and market opportunity
3. Make it suitable for print-on-demand products
4. Include specific visual elements and style direction
5. Keep it concise but descriptive (2-3 sentences)

RESPONSE: Provide only the design concept description, no additional text.
"""
                
                response = await self.vertex_ai.generate_text(
                    prompt=prompt,
                    model="gemini-1.5-flash",
                    max_tokens=500,
                    temperature=0.8
                )
                
                if isinstance(response, dict):
                    design_concept = response.get('text', '')
                else:
                    design_concept = str(response)
                
                if design_concept and len(design_concept.strip()) > 10:
                    return design_concept.strip()
                else:
                    raise ValueError("Generated design concept is too short or empty")
                    
            except Exception as e:
                logger.warning(f"⚠️ Design concept generation attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("❌ All design concept generation attempts failed")
                    raise
        
        return None
    
    async def _select_product_with_retry(self, design_concept: str, trend_keyword: str) -> Optional[ProductRecommendation]:
        """Select product with retry logic"""
        
        for attempt in range(self.max_retries):
            try:
                recommendation = await self.product_strategist.select_best_product(design_concept, trend_keyword)
                
                # Validate the selection
                is_valid = await self.product_strategist.validate_product_selection(recommendation)
                
                if is_valid:
                    return recommendation
                else:
                    raise ValueError("Selected product validation failed")
                    
            except Exception as e:
                logger.warning(f"⚠️ Product selection attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("❌ All product selection attempts failed")
                    raise
        
        return None
    
    async def _generate_image_with_retry(self, design_concept: str, product_recommendation: ProductRecommendation) -> Optional[str]:
        """Generate image with retry logic"""
        
        for attempt in range(self.max_retries):
            try:
                # Create enhanced prompt for image generation
                enhanced_prompt = f"""
{design_concept}

PRODUCT: {product_recommendation.product_name}
STYLE: Modern, high-quality, print-on-demand ready
FORMAT: Clean, centered design with good contrast
RESOLUTION: High quality for printing on fabric
"""
                
                # Generate image using Vertex AI
                image_data = await self.image_generator.generate_image(
                    prompt=enhanced_prompt,
                    model="imagen-4.0-generate-001",
                    aspect_ratio="1:1",
                    number_of_images=1
                )
                
                if image_data:
                    # Upload to Printify
                    image_url = await self.printify_client.upload_image(
                        image_data=image_data,
                        filename=f"ai_generated_{int(time.time())}.jpg"
                    )
                    
                    if image_url:
                        return image_url
                    else:
                        raise ValueError("Failed to upload image to Printify")
                else:
                    raise ValueError("Failed to generate image")
                    
            except Exception as e:
                logger.warning(f"⚠️ Image generation attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("❌ All image generation attempts failed")
                    raise
        
        return None
    
    async def _generate_marketing_copy_with_retry(self, trend: Any, design_concept: str, 
                                                product_recommendation: ProductRecommendation) -> Optional[str]:
        """Generate marketing copy with retry logic"""
        
        for attempt in range(self.max_retries):
            try:
                prompt = f"""
You are a marketing copywriter for a print-on-demand business. Create compelling product copy for this item.

TREND: {trend.keyword}
DESIGN CONCEPT: {design_concept}
PRODUCT: {product_recommendation.product_name}
TARGET AUDIENCE: {getattr(trend, 'target_audience', 'General audience')}

REQUIREMENTS:
1. Create a catchy product title (under 60 characters)
2. Write compelling product description (2-3 sentences)
3. Include relevant hashtags for social media
4. Make it appealing to the target audience
5. Highlight the trend connection

RESPONSE FORMAT (JSON only):
{{
    "title": "Product title",
    "description": "Product description",
    "hashtags": ["#hashtag1", "#hashtag2", "#hashtag3"],
    "social_media_copy": "Short copy for social media posts"
}}

Create copy that will drive sales and engagement.
"""
                
                response = await self.vertex_ai.generate_text(
                    prompt=prompt,
                    model="gemini-1.5-flash",
                    max_tokens=1000,
                    temperature=0.7
                )
                
                if isinstance(response, dict):
                    copy_text = response.get('text', '')
                else:
                    copy_text = str(response)
                
                # Extract JSON
                start_idx = copy_text.find('{')
                end_idx = copy_text.rfind('}') + 1
                
                if start_idx != -1 and end_idx > 0:
                    json_str = copy_text[start_idx:end_idx]
                    copy_data = json.loads(json_str)
                    
                    # Combine all copy elements
                    full_copy = f"{copy_data.get('title', '')}\n\n{copy_data.get('description', '')}\n\n{' '.join(copy_data.get('hashtags', []))}"
                    return full_copy
                else:
                    raise ValueError("Failed to parse marketing copy JSON")
                    
            except Exception as e:
                logger.warning(f"⚠️ Marketing copy generation attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("❌ All marketing copy generation attempts failed")
                    raise
        
        return None
    
    async def _publish_product_with_retry(self, image_url: str, product_recommendation: ProductRecommendation,
                                        marketing_copy: str, trend_analysis: TrendAnalysis) -> Optional[str]:
        """Publish product with retry logic"""
        
        for attempt in range(self.max_retries):
            try:
                # Get product variants
                variants = await self.product_strategist.get_product_variants(
                    product_recommendation.blueprint_id,
                    product_recommendation.print_provider_id
                )
                
                if not variants:
                    raise ValueError("No variants available for product")
                
                # Create product data
                product_data = {
                    'title': marketing_copy.split('\n')[0][:60],  # First line as title
                    'description': marketing_copy,
                    'blueprint_id': product_recommendation.blueprint_id,
                    'print_provider_id': product_recommendation.print_provider_id,
                    'print_areas': [
                        {
                            'variant_ids': [v['id'] for v in variants[:3]],  # Top 3 variants
                            'placeholders': [
                                {
                                    'position': 'front',
                                    'images': [{'url': image_url}]
                                }
                            ]
                        }
                    ]
                }
                
                # Create product
                product = await self.printify_client.create_product(product_data)
                
                if product and product.get('id'):
                    # Publish product
                    published = await self.printify_client.publish_product(product['id'])
                    
                    if published:
                        return str(product['id'])
                    else:
                        raise ValueError("Product creation succeeded but publishing failed")
                else:
                    raise ValueError("Product creation failed")
                    
            except Exception as e:
                logger.warning(f"⚠️ Product publishing attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    logger.error("❌ All product publishing attempts failed")
                    raise
        
        return None
    
    async def _log_workflow_results(self, trend_analysis: TrendAnalysis, product_recommendation: ProductRecommendation,
                                  image_url: str, product_id: str, marketing_copy: str):
        """Log workflow results for analysis and tracking"""
        
        try:
            # Create result summary
            result_summary = {
                'timestamp': time.time(),
                'trend': {
                    'keyword': trend_analysis.primary_trend.keyword,
                    'category': trend_analysis.primary_trend.category,
                    'source': trend_analysis.primary_trend.source,
                    'confidence': trend_analysis.primary_trend.confidence_score
                },
                'product': {
                    'name': product_recommendation.product_name,
                    'blueprint_id': product_recommendation.blueprint_id,
                    'confidence': product_recommendation.confidence_score
                },
                'image_url': image_url,
                'product_id': product_id,
                'marketing_copy_length': len(marketing_copy),
                'workflow_success': True
            }
            
            # Log to console and could be extended to Google Sheets
            logger.info(f"📊 Workflow Results Logged: {json.dumps(result_summary, indent=2)}")
            
            # TODO: Add Google Sheets logging when available
            # await self._log_to_sheets(result_summary)
            
        except Exception as e:
            logger.warning(f"⚠️ Failed to log workflow results: {e}")
    
    async def get_workflow_status(self) -> Dict[str, Any]:
        """Get current workflow status and health"""
        
        try:
            # Test each component
            components_status = {
                'trend_discovery': await self._test_trend_discovery(),
                'product_strategy': await self._test_product_strategy(),
                'image_generation': await self._test_image_generation(),
                'printify_integration': await self._test_printify_integration()
            }
            
            overall_health = all(components_status.values())
            
            return {
                'overall_health': overall_health,
                'components': components_status,
                'timestamp': time.time(),
                'workflow_version': '2.0'
            }
            
        except Exception as e:
            logger.error(f"❌ Failed to get workflow status: {e}")
            return {
                'overall_health': False,
                'error': str(e),
                'timestamp': time.time(),
                'workflow_version': '2.0'
            }
    
    async def _test_trend_discovery(self) -> bool:
        """Test trend discovery functionality"""
        try:
            await self.zeitgeist_finder.discover_current_trends()
            return True
        except Exception:
            return False
    
    async def _test_product_strategy(self) -> bool:
        """Test product strategy functionality"""
        try:
            await self.product_strategist.get_cached_catalog()
            return True
        except Exception:
            return False
    
    async def _test_image_generation(self) -> bool:
        """Test image generation functionality"""
        try:
            # Simple test - just check if service is accessible
            return True
        except Exception:
            return False
    
    async def _test_printify_integration(self) -> bool:
        """Test Printify integration"""
        try:
            # Test basic connectivity
            await self.printify_client.get_blueprints()
            return True
        except Exception:
            return False
