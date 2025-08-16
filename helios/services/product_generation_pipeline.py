"""
Automated Product Generation Pipeline for Helios
Design automation, ethical screening, marketing copy generation, and publishing
"""

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
from loguru import logger

from ..agents.creative import CreativeDirector
from ..agents.marketing import MarketingCopywriter
from ..agents.ethics import EthicalGuardianAgent
from ..agents.publisher_agent import PrintifyPublisherAgent
from ..agents.trend_analysis_ai import TrendAnalysisAI, TrendAnalysisMode, ProductPrediction
from ..services.ethical_code import EthicalCodeService
from ..services.copyright_review import CopyrightReviewService
from ..services.external_apis.image_generation import ImageGenerationService
from ..services.google_cloud.vertex_ai_client import VertexAIClient
from ..config import HeliosConfig
from ..utils.performance_monitor import PerformanceMonitor


@dataclass
class ProductDesign:
    """Product design specification"""
    design_id: str
    trend_name: str
    design_concept: str
    design_elements: List[str]
    color_scheme: List[str]
    style_preferences: Dict[str, Any]
    target_audience: Dict[str, Any]
    design_prompt: str
    ethical_score: float = 0.0
    copyright_status: str = "pending"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ai_enhanced: bool = False


@dataclass
class GeneratedImage:
    """Generated image data"""
    image_id: str
    design_id: str
    image_url: str
    image_metadata: Dict[str, Any]
    generation_prompt: str
    model_used: str
    image_path: Optional[str] = None
    quality_score: float = 0.0
    ethical_approval: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class MarketingCopy:
    """Marketing copy for product"""
    copy_id: str
    design_id: str
    product_title: str
    product_description: str
    tags: List[str]
    social_media_copy: Dict[str, str]
    seo_keywords: List[str]
    call_to_action: str
    ethical_approval: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    bullet_points: List[str] = field(default_factory=list)
    pricing_strategy: Dict[str, Any] = field(default_factory=dict)
    ai_enhanced: bool = False


@dataclass
class ProductPackage:
    """Complete product package ready for publishing"""
    package_id: str
    trend_name: str
    design: ProductDesign
    images: List[GeneratedImage]
    marketing_copy: MarketingCopy
    ethical_approval: bool = False
    ready_for_publishing: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class GenerationSession:
    """Product generation session data"""
    session_id: str
    trend_opportunity: Dict[str, Any]
    start_time: datetime
    end_time: Optional[datetime] = None
    designs_created: int = 0
    images_generated: int = 0
    copy_created: int = 0
    packages_completed: int = 0
    ethical_issues: int = 0
    execution_time: float = 0.0
    status: str = "running"
    errors: List[str] = field(default_factory=list)


class ProductGenerationPipeline:
    """Automated product generation pipeline with ethical screening"""
    
    def __init__(self, config: HeliosConfig):
        self.config = config
        self.creative_director = CreativeDirector(
            output_dir=config.output_dir,
            fonts_dir=config.fonts_dir
        )
        self.marketing_copywriter = MarketingCopywriter()
        self.ethical_guardian = EthicalGuardianAgent()
        self.publisher_agent = PrintifyPublisherAgent(
            api_token=config.printify_api_token,
            shop_id=config.printify_shop_id
        )
        self.ethical_code_service = EthicalCodeService()
        self.copyright_service = CopyrightReviewService()
        self.image_generation = ImageGenerationService(
            vertex_ai_client=VertexAIClient(
                project_id=config.google_cloud_project,
                location=config.google_cloud_location
            )
        )
        self.performance_monitor = PerformanceMonitor(config)
        
        # Initialize AI agent for enhanced product generation
        self.trend_ai = TrendAnalysisAI(config)
        
        # Pipeline configuration
        self.max_designs_per_trend = 5
        self.max_images_per_design = 3
        self.ethical_threshold = 0.8
        self.quality_threshold = 0.7
        
        # AI enhancement configuration
        self.use_ai_insights = True
        self.ai_confidence_threshold = 0.75
        
        # Session tracking
        self.active_session: Optional[GenerationSession] = None
        self.generation_history: List[GenerationSession] = []
        
        logger.info("✅ Product Generation Pipeline initialized with AI enhancements")
    
    async def start_generation_session(self, trend_opportunity: Dict[str, Any]) -> GenerationSession:
        """Start a new product generation session"""
        session_id = f"generation_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        
        self.active_session = GenerationSession(
            session_id=session_id,
            trend_opportunity=trend_opportunity,
            start_time=datetime.now(timezone.utc)
        )
        
        logger.info(f"🎨 Starting generation session: {session_id} for trend: {trend_opportunity.get('trend_name', 'unknown')}")
        return self.active_session
    
    async def run_generation_pipeline(self, trend_opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """Run the complete product generation pipeline"""
        start_time = time.time()
        
        try:
            # Start generation session
            session = await self.start_generation_session(trend_opportunity)
            
            # Get AI insights if available
            ai_insights = None
            if self.use_ai_insights and "ai_analysis" in trend_opportunity:
                ai_insights = trend_opportunity["ai_analysis"]
                logger.info("🤖 Using AI insights for enhanced product generation")
            
            # STAGE 1: AI-enhanced design concept generation
            logger.info("🎨 STAGE 1: AI-enhanced design concept generation")
            designs = await self._generate_design_concepts(trend_opportunity, ai_insights)
            
            # STAGE 2: Image generation with AI optimization
            logger.info("🖼️ STAGE 2: Image generation with AI optimization")
            all_images = await self._generate_images_for_designs(designs, ai_insights)
            
            # STAGE 3: AI-powered marketing copy generation
            logger.info("📝 STAGE 3: AI-powered marketing copy generation")
            marketing_copies = await self._generate_marketing_copy(designs, ai_insights)
            
            # STAGE 4: Ethical screening and validation
            logger.info("✅ STAGE 4: Ethical screening and validation")
            validated_packages = await self._validate_and_package_products(
                designs, all_images, marketing_copies
            )
            
            # STAGE 5: AI product success prediction
            if self.use_ai_insights and validated_packages:
                logger.info("🔮 STAGE 5: AI product success prediction")
                ai_predictions = await self._predict_product_success(
                    validated_packages, trend_opportunity
                )
                
                # Filter packages based on AI predictions
                high_confidence_packages = [
                    pkg for pkg, pred in zip(validated_packages, ai_predictions)
                    if pred and pred.predicted_success_rate >= self.ai_confidence_threshold
                ]
                
                logger.info(f"✅ {len(high_confidence_packages)}/{len(validated_packages)} products meet AI confidence threshold")
                validated_packages = high_confidence_packages
            
            # STAGE 5: Session completion
            session.end_time = datetime.now(timezone.utc)
            session.execution_time = time.time() - start_time
            session.designs_created = len(designs)
            session.images_generated = sum(len(images) for images in all_images.values())
            session.copy_created = len(marketing_copies)
            session.packages_completed = len(validated_packages)
            session.status = "completed"
            
            # Record performance metrics
            self.performance_monitor.record_metric_with_labels(
                "generation_session_duration",
                session.execution_time,
                labels={"session_id": session.session_id}
            )
            
            self.performance_monitor.record_metric_with_labels(
                "products_generated_per_session",
                session.packages_completed,
                labels={"session_id": session.session_id}
            )
            
            # Store session in history
            self.generation_history.append(session)
            
            logger.info(f"✅ Generation session completed: {session.packages_completed} products ready")
            
            return {
                "session": session,
                "designs": designs,
                "images": all_images,
                "marketing_copies": marketing_copies,
                "product_packages": validated_packages,
                "execution_time": session.execution_time,
                "status": "success"
            }
            
        except Exception as e:
            logger.error(f"❌ Generation pipeline failed: {e}")
            if self.active_session:
                self.active_session.status = "failed"
                self.active_session.errors.append(str(e))
                self.active_session.end_time = datetime.now(timezone.utc)
                self.active_session.execution_time = time.time() - start_time
            
            return {
                "status": "error",
                "error": str(e),
                "execution_time": time.time() - start_time
            }
    
    async def _generate_design_concepts(self, trend_opportunity: Dict[str, Any], ai_insights: Dict[str, Any] = None) -> List[ProductDesign]:
        """Generate design concepts using Creative Director agent with AI enhancements"""
        designs = []
        trend_name = trend_opportunity.get("trend_name", "")
        related_keywords = trend_opportunity.get("related_keywords", [])
        audience_demographics = trend_opportunity.get("audience_demographics", {})
        
        # Extract AI recommendations if available
        ai_design_themes = []
        ai_recommended_products = []
        ai_marketing_angles = []
        
        if ai_insights:
            ai_design_themes = ai_insights.get("design_themes", [])
            ai_recommended_products = ai_insights.get("recommended_products", [])
            ai_marketing_angles = ai_insights.get("marketing_angles", [])
            
            logger.info(f"🤖 Using AI-recommended themes: {ai_design_themes[:3]}")
            logger.info(f"🤖 Using AI-recommended products: {[p.get('type') for p in ai_recommended_products[:3]]}")
        
        try:
            # Generate multiple design concepts with AI guidance
            for i in range(self.max_designs_per_trend):
                # Use AI themes and recommendations if available
                style_preferences = {
                    "aesthetic": ai_design_themes[i % len(ai_design_themes)] if ai_design_themes else "modern_vintage",
                    "color_palette": "ai_optimized" if ai_insights else "retro_inspired",
                    "typography": "bold_clean",
                    "ai_guided": bool(ai_insights)
                }
                
                # Enhance keywords with AI insights
                enhanced_keywords = related_keywords.copy()
                if ai_marketing_angles and i < len(ai_marketing_angles):
                    enhanced_keywords.append(ai_marketing_angles[i])
                
                design_concept = await self.creative_director.generate_design_concept(
                    trend_name=trend_name,
                    keywords=enhanced_keywords,
                    audience=audience_demographics,
                    style_preferences=style_preferences,
                    ai_recommendations=ai_recommended_products[i] if i < len(ai_recommended_products) else None
                )
                
                if design_concept and design_concept.get("status") == "success":
                    design_data = design_concept.get("design_data", {})
                    
                    design = ProductDesign(
                        design_id=f"design_{int(time.time())}_{i}",
                        trend_name=trend_name,
                        design_concept=design_data.get("concept", ""),
                        design_elements=design_data.get("elements", []),
                        color_scheme=design_data.get("colors", []),
                        style_preferences=style_preferences,
                        target_audience=audience_demographics,
                        design_prompt=design_data.get("prompt", ""),
                        ai_enhanced=bool(ai_insights)
                    )
                    
                    designs.append(design)
                    logger.info(f"🎨 Generated {'AI-enhanced' if ai_insights else ''} design concept {i+1}: {design.design_concept[:50]}...")
                
                # Small delay between generations
                await asyncio.sleep(1)
            
            logger.info(f"🎨 Generated {len(designs)} design concepts ({sum(1 for d in designs if hasattr(d, 'ai_enhanced') and d.ai_enhanced)} AI-enhanced)")
            return designs
            
        except Exception as e:
            logger.error(f"❌ Design concept generation failed: {e}")
            return []
    
    async def _generate_images_for_designs(self, designs: List[ProductDesign], ai_insights: Dict[str, Any] = None) -> Dict[str, List[GeneratedImage]]:
        """Generate images for each design concept"""
        all_images = {}
        
        for design in designs:
            try:
                images = []
                
                # Generate multiple image variants
                for j in range(self.max_images_per_design):
                    image_result = await self.image_generation.generate_design_image(
                        prompt=design.design_prompt,
                        style_preferences=design.style_preferences,
                        color_scheme=design.color_scheme,
                        model=self.config.imagen_model,
                        resolution=self.config.image_resolution,
                        quality=self.config.image_quality
                    )
                    
                    if image_result and image_result.get("status") == "success":
                        image_data = image_result.get("image_data", {})
                        
                        image = GeneratedImage(
                            image_id=f"image_{int(time.time())}_{len(images)}",
                            design_id=design.design_id,
                            image_url=image_data.get("image_url", ""),
                            image_path=image_data.get("local_path"),
                            image_metadata=image_data.get("metadata", {}),
                            generation_prompt=design.design_prompt,
                            model_used=self.config.imagen_model,
                            quality_score=image_data.get("quality_score", 0.0)
                        )
                        
                        images.append(image)
                        logger.info(f"🖼️ Generated image {j+1} for design {design.design_id}")
                    
                    # Small delay between generations
                    await asyncio.sleep(2)
                
                all_images[design.design_id] = images
                
            except Exception as e:
                logger.error(f"❌ Image generation failed for design {design.design_id}: {e}")
                all_images[design.design_id] = []
        
        total_images = sum(len(images) for images in all_images.values())
        logger.info(f"🖼️ Generated {total_images} images for {len(designs)} designs")
        return all_images
    
    async def _generate_marketing_copy(self, designs: List[ProductDesign], ai_insights: Dict[str, Any] = None) -> List[MarketingCopy]:
        """Generate marketing copy for designs with AI enhancements"""
        marketing_copies = []
        
        # Extract AI marketing angles if available
        ai_marketing_angles = []
        ai_pricing_strategy = {}
        
        if ai_insights:
            ai_marketing_angles = ai_insights.get("marketing_angles", [])
            ai_pricing_strategy = ai_insights.get("pricing_strategy", {})
            logger.info(f"🤖 Using {len(ai_marketing_angles)} AI-generated marketing angles")
        
        try:
            for i, design in enumerate(designs):
                # Use AI marketing angle if available
                marketing_angle = None
                if ai_marketing_angles and i < len(ai_marketing_angles):
                    marketing_angle = ai_marketing_angles[i]
                
                copy_result = await self.marketing_copywriter.generate_marketing_copy(
                    product_concept=design.design_concept,
                    target_audience=design.target_audience,
                    keywords=[design.trend_name] + design.design_elements[:3],
                    tone="engaging_professional",
                    ai_marketing_angle=marketing_angle,
                    ai_pricing_strategy=ai_pricing_strategy
                )
                
                if copy_result and copy_result.get("status") == "success":
                    copy_data = copy_result.get("copy_data", {})
                    
                    marketing_copy = MarketingCopy(
                        copy_id=f"copy_{int(time.time())}_{i}",
                        design_id=design.design_id,
                        title=copy_data.get("title", ""),
                        description=copy_data.get("description", ""),
                        bullet_points=copy_data.get("bullet_points", []),
                        tags=copy_data.get("tags", []),
                        seo_keywords=copy_data.get("seo_keywords", []),
                        call_to_action=copy_data.get("call_to_action", ""),
                        pricing_strategy=ai_pricing_strategy if ai_insights else {},
                        ai_enhanced=bool(ai_insights and marketing_angle)
                    )
                    
                    marketing_copies.append(marketing_copy)
                    logger.info(f"📝 Generated {'AI-enhanced' if marketing_copy.ai_enhanced else ''} marketing copy: {marketing_copy.title[:50]}...")
                
                await asyncio.sleep(0.5)
            
            logger.info(f"📝 Generated {len(marketing_copies)} marketing copies ({sum(1 for c in marketing_copies if hasattr(c, 'ai_enhanced') and c.ai_enhanced)} AI-enhanced)")
            return marketing_copies
            
        except Exception as e:
            logger.error(f"❌ Marketing copy generation failed: {e}")
            return []
    
    async def _predict_product_success(
        self,
        product_packages: List[ProductPackage],
        trend_opportunity: Dict[str, Any]
    ) -> List[Optional[ProductPrediction]]:
        """Predict product success using AI"""
        predictions = []
        
        try:
            # Convert trend opportunity to AI format if needed
            trend_analysis = None
            if "ai_analysis" in trend_opportunity:
                # Use existing AI analysis
                trend_analysis = trend_opportunity["ai_analysis"]
            
            for package in product_packages:
                try:
                    # Create product concept for prediction
                    product_concept = {
                        "design_concept": package.design.design_concept,
                        "design_elements": package.design.design_elements,
                        "marketing_copy": package.marketing_copy.title,
                        "target_audience": package.design.target_audience,
                        "images_count": len(package.images),
                        "product_type": "print-on-demand"
                    }
                    
                    # Get AI prediction
                    if trend_analysis:
                        prediction = await self.trend_ai.predict_product_success(
                            trend_analysis,
                            product_concept
                        )
                        predictions.append(prediction)
                        
                        logger.info(f"🔮 AI prediction for {package.package_id}: {prediction.predicted_success_rate:.2%} success rate")
                    else:
                        predictions.append(None)
                        
                except Exception as e:
                    logger.warning(f"Failed to predict success for {package.package_id}: {e}")
                    predictions.append(None)
                
                await asyncio.sleep(0.5)  # Rate limiting
            
            return predictions
            
        except Exception as e:
            logger.error(f"❌ Product success prediction failed: {e}")
            return [None] * len(product_packages)
    
    async def _validate_and_package_products(
        self,
        designs: List[ProductDesign],
        all_images: Dict[str, List[GeneratedImage]],
        marketing_copies: List[MarketingCopy]
    ) -> List[ProductPackage]:
        """Validate products and create packages"""
        packages = []
        
        for design in designs:
            try:
                # Get associated images and marketing copy
                images = all_images.get(design.design_id, [])
                marketing_copy = next(
                    (copy for copy in marketing_copies if copy.design_id == design.design_id),
                    None
                )
                
                if not images or not marketing_copy:
                    logger.warning(f"⚠️ Missing images or copy for design {design.design_id}")
                    continue
                
                # Ethical screening
                ethical_result = await self._screen_product_ethics(design, images, marketing_copy)
                
                # Copyright review
                copyright_result = await self._review_copyright(design, images, marketing_copy)
                
                # Create product package
                package = ProductPackage(
                    package_id=f"package_{int(time.time())}_{len(packages)}",
                    trend_name=design.trend_name,
                    design=design,
                    images=images,
                    marketing_copy=marketing_copy,
                    ethical_approval=ethical_result.get("approved", False),
                    ready_for_publishing=ethical_result.get("approved", False) and copyright_result.get("approved", False)
                )
                
                # Update design with ethical and copyright status
                design.ethical_score = ethical_result.get("score", 0.0)
                design.copyright_status = copyright_result.get("status", "pending")
                
                packages.append(package)
                
                if package.ready_for_publishing:
                    logger.info(f"✅ Product package {package.package_id} ready for publishing")
                else:
                    logger.warning(f"⚠️ Product package {package.package_id} failed validation")
                
            except Exception as e:
                logger.error(f"❌ Product validation failed for design {design.design_id}: {e}")
                continue
        
        logger.info(f"✅ Created {len(packages)} product packages")
        return packages
    
    async def _screen_product_ethics(
        self,
        design: ProductDesign,
        images: List[GeneratedImage],
        marketing_copy: MarketingCopy
    ) -> Dict[str, Any]:
        """Screen product for ethical compliance"""
        try:
            # Screen design concept
            design_screening = await self.ethical_guardian.screen_content(
                content=design.design_concept,
                content_type="design_concept",
                context={
                    "trend_name": design.trend_name,
                    "target_audience": design.target_audience,
                    "style_preferences": design.style_preferences
                }
            )
            
            # Screen marketing copy
            copy_screening = await self.ethical_guardian.screen_content(
                content=marketing_copy.product_description,
                content_type="marketing_copy",
                context={
                    "product_title": marketing_copy.title,
                    "target_audience": design.target_audience,
                    "tags": marketing_copy.tags
                }
            )
            
            # Screen image prompts
            image_screening = await self.ethical_guardian.screen_content(
                content=design.design_prompt,
                content_type="image_prompt",
                context={
                    "design_concept": design.design_concept,
                    "style_preferences": design.style_preferences
                }
            )
            
            # Calculate composite ethical score
            design_score = design_screening.get("ethical_score", 0.0)
            copy_score = copy_screening.get("ethical_score", 0.0)
            image_score = image_screening.get("ethical_score", 0.0)
            
            composite_score = (design_score + copy_score + image_score) / 3.0
            
            # Determine approval
            approved = composite_score >= self.ethical_threshold
            
            # Update image ethical approval
            for image in images:
                image.ethical_approval = approved
            
            # Update marketing copy ethical approval
            marketing_copy.ethical_approval = approved
            
            return {
                "approved": approved,
                "score": composite_score,
                "design_score": design_score,
                "copy_score": copy_score,
                "image_score": image_score,
                "issues": design_screening.get("issues", []) + copy_screening.get("issues", []) + image_screening.get("issues", [])
            }
            
        except Exception as e:
            logger.error(f"❌ Ethical screening failed: {e}")
            return {
                "approved": False,
                "score": 0.0,
                "issues": [f"Ethical screening error: {str(e)}"]
            }
    
    async def _review_copyright(
        self,
        design: ProductDesign,
        images: List[GeneratedImage],
        marketing_copy: MarketingCopy
    ) -> Dict[str, Any]:
        """Review product for copyright compliance"""
        try:
            # Review design concept
            design_review = await self.copyright_service.review_content(
                content=design.design_concept,
                content_type="design",
                context={
                    "trend_name": design.trend_name,
                    "design_elements": design.design_elements
                }
            )
            
            # Review marketing copy
            copy_review = await self.copyright_service.review_content(
                content=marketing_copy.product_description,
                content_type="marketing",
                context={
                    "product_title": marketing_copy.title,
                    "tags": marketing_copy.tags
                }
            )
            
            # Determine overall copyright status
            design_approved = design_review.get("approved", False)
            copy_approved = copy_review.get("approved", False)
            
            overall_approved = design_approved and copy_approved
            
            # Determine status
            if overall_approved:
                status = "approved"
            elif design_approved or copy_approved:
                status = "partial_approval"
            else:
                status = "rejected"
            
            return {
                "approved": overall_approved,
                "status": status,
                "design_approved": design_approved,
                "copy_approved": copy_approved,
                "issues": design_review.get("issues", []) + copy_review.get("issues", [])
            }
            
        except Exception as e:
            logger.error(f"❌ Copyright review failed: {e}")
            return {
                "approved": False,
                "status": "error",
                "issues": [f"Copyright review error: {str(e)}"]
            }
    
    async def publish_products(self, product_packages: List[ProductPackage]) -> Dict[str, Any]:
        """Publish approved products to Printify"""
        published_products = []
        failed_publications = []
        
        for package in product_packages:
            if not package.ready_for_publishing:
                logger.warning(f"⚠️ Skipping package {package.package_id} - not ready for publishing")
                continue
            
            try:
                # Prepare product data for publishing
                product_data = {
                    "title": package.marketing_copy.title,
                    "description": package.marketing_copy.description,
                    "tags": package.marketing_copy.tags,
                    "images": [img.image_url for img in package.images if img.image_url],
                    "design_concept": package.design.design_concept,
                    "trend_name": package.trend_name
                }
                
                # Publish to Printify
                publication_result = await self.publisher_agent.publish_product(product_data)
                
                if publication_result and publication_result.get("status") == "success":
                    published_products.append({
                        "package_id": package.package_id,
                        "printify_product_id": publication_result.get("product_id"),
                        "publication_status": "published"
                    })
                    logger.info(f"✅ Published product {package.package_id} to Printify")
                else:
                    failed_publications.append({
                        "package_id": package.package_id,
                        "error": publication_result.get("error", "Unknown error")
                    })
                    logger.error(f"❌ Failed to publish product {package.package_id}")
                
            except Exception as e:
                failed_publications.append({
                    "package_id": package.package_id,
                    "error": str(e)
                })
                logger.error(f"❌ Publication error for package {package.package_id}: {e}")
        
        return {
            "published_count": len(published_products),
            "failed_count": len(failed_publications),
            "published_products": published_products,
            "failed_publications": failed_publications
        }
    
    async def get_generation_summary(self) -> Dict[str, Any]:
        """Get summary of generation activities"""
        total_sessions = len(self.generation_history)
        total_designs = sum(s.designs_created for s in self.generation_history)
        total_images = sum(s.images_generated for s in self.generation_history)
        total_packages = sum(s.packages_completed for s in self.generation_history)
        
        return {
            "total_sessions": total_sessions,
            "total_designs_created": total_designs,
            "total_images_generated": total_images,
            "total_packages_completed": total_packages,
            "success_rate": total_packages / total_designs if total_designs > 0 else 0,
            "last_session": self.generation_history[-1] if self.generation_history else None,
            "active_session": self.active_session
        }
    
    async def cleanup(self):
        """Cleanup resources"""
        try:
            await self.performance_monitor.cleanup()
            logger.info("✅ Product Generation Pipeline cleaned up")
        except Exception as e:
            logger.error(f"❌ Cleanup failed: {e}")


async def create_product_generation_pipeline(config: HeliosConfig) -> ProductGenerationPipeline:
    """Factory function to create product generation pipeline"""
    return ProductGenerationPipeline(config)
