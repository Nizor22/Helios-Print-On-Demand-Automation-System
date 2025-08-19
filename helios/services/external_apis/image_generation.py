"""
Image Generation Service for Helios Autonomous Store
Integrates with Vertex AI for AI-powered image generation
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass
from pathlib import Path
import base64
from loguru import logger

from ..google_cloud.vertex_ai_client import VertexAIClient
from ..google_cloud.storage_client import CloudStorageClient


@dataclass
class ImageGenerationRequest:
    """Image generation request parameters"""
    prompt: str
    negative_prompt: str = ""
    width: int = 1024
    height: int = 1024
    guidance_scale: float = 7.5
    num_inference_steps: int = 50
    seed: Optional[int] = None
    style_preset: str = "photographic"
    safety_filter_level: str = "block_some"
    aspect_ratio: str = "1:1"


@dataclass
class GeneratedImage:
    """Generated image data structure"""
    image_data: bytes
    prompt: str
    negative_prompt: str
    parameters: Dict[str, Any]
    generation_time_ms: int
    model_used: str
    safety_score: float
    created_at: float
    file_name: str
    content_type: str = "image/png"


class ImageGenerationService:
    """AI-powered image generation service using Vertex AI"""
    
    def __init__(
        self,
        vertex_ai_client: VertexAIClient,
        storage_client: CloudStorageClient = None,
        config: Dict[str, Any] = None
    ):
        self.vertex_ai_client = vertex_ai_client
        self.storage_client = storage_client
        self.config = config or {}
        
        # Default configuration
        self.default_config = {
            "model": "imagen-4.0-generate-001",
            "resolution": "1024x1024",
            "format": "PNG",
            "quality": "high",
            "safety_filtering": True,
            "max_concurrent_generations": 5,
            "batch_size": 3,
            "fallback_model": "imagen-3.0-generate-002"
        }
        
        # Update with provided config
        self.default_config.update(self.config)
        
        # Generation queue
        self._generation_queue = asyncio.Queue()
        self._active_generations = 0
        self._max_concurrent = self.default_config["max_concurrent_generations"]
        
        logger.info(f"✅ Image Generation Service initialized with model: {self.default_config['model']}")
    
    async def generate_image(self, request: ImageGenerationRequest) -> Dict[str, Any]:
        """Generate a single image using Vertex AI
        
        Args:
            request: Image generation parameters
        
        Returns:
            Generated image result
        """
        try:
            start_time = time.time()
            
            logger.info(f"🎨 Generating image with prompt: {request.prompt[:100]}...")
            
            # Prepare generation parameters
            generation_params = {
                "prompt": request.prompt,
                "negative_prompt": request.negative_prompt,
                "width": request.width,
                "height": request.height,
                "guidance_scale": request.guidance_scale,
                "num_inference_steps": request.num_inference_steps,
                "seed": request.seed,
                "style_preset": request.style_preset,
                "safety_filter_level": request.safety_filter_level
            }
            
            # Generate image using Vertex AI with Imagen 4.0
            result = await self.vertex_ai_client.generate_image(
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                width=request.width,
                height=request.height,
                guidance_scale=request.guidance_scale,
                num_inference_steps=request.num_inference_steps,
                seed=request.seed,
                model="imagen-4.0-generate-001"
            )
            
            if not result.get("success"):
                # Try fallback model
                logger.warning(f"Primary model failed, trying fallback: {self.default_config['fallback_model']}")
                result = await self.vertex_ai_client.generate_image(
                    prompt=request.prompt,
                    negative_prompt=request.negative_prompt,
                    width=request.width,
                    height=request.height,
                    guidance_scale=request.guidance_scale,
                    num_inference_steps=request.num_inference_steps,
                    seed=request.seed,
                    model=self.default_config["fallback_model"]
                )
                
                if not result.get("success"):
                    return {"success": False, "error": f"Image generation failed: {result.get('error')}"}
            
            generation_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Create generated image object
            generated_image = GeneratedImage(
                image_data=result["image_data"],
                prompt=request.prompt,
                negative_prompt=request.negative_prompt,
                parameters=generation_params,
                generation_time_ms=int(generation_time),
                model_used=result.get("model_used", self.default_config["model"]),
                safety_score=result.get("safety_score", 1.0),
                created_at=time.time(),
                file_name=f"generated_{int(time.time())}.png"
            )
            
            # Store in Cloud Storage if available
            if self.storage_client:
                storage_result = await self.storage_client.store_product_design(
                    design_data=generated_image.image_data,
                    trend_name="ai_generated",
                    design_type="product_design",
                    content_type="image/png"
                )
                
                if storage_result.get("success"):
                    generated_image.file_name = storage_result["file_name"]
                    logger.info(f"✅ Generated image stored in Cloud Storage: {storage_result['public_url']}")
            
            logger.info(f"✅ Image generated successfully in {generation_time:.1f}ms")
            
            return {
                "success": True,
                "generated_image": generated_image,
                "generation_time_ms": generation_time,
                "model_used": generated_image.model_used,
                "storage_url": storage_result.get("public_url") if self.storage_client else None
            }
            
        except Exception as e:
            error_msg = f"Image generation failed: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def generate_batch(
        self, 
        requests: List[ImageGenerationRequest],
        max_concurrent: int = None
    ) -> Dict[str, Any]:
        """Generate multiple images in batch with controlled concurrency
        
        Args:
            requests: List of image generation requests
            max_concurrent: Maximum concurrent generations (overrides default)
        
        Returns:
            Batch generation results
        """
        try:
            max_concurrent = max_concurrent or self._max_concurrent
            logger.info(f"🚀 Starting batch generation of {len(requests)} images (max concurrent: {max_concurrent})")
            
            # Create semaphore to limit concurrent generations
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def generate_with_semaphore(request: ImageGenerationRequest) -> Dict[str, Any]:
                async with semaphore:
                    return await self.generate_image(request)
            
            # Generate all images concurrently
            generation_tasks = [generate_with_semaphore(req) for req in requests]
            results = await asyncio.gather(*generation_tasks, return_exceptions=True)
            
            # Process results
            successful_generations = []
            failed_generations = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_generations.append({
                        "index": i,
                        "error": str(result),
                        "request": requests[i]
                    })
                elif result.get("success"):
                    successful_generations.append(result)
                else:
                    failed_generations.append({
                        "index": i,
                        "error": result.get("error", "Unknown error"),
                        "request": requests[i]
                    })
            
            success_rate = len(successful_generations) / len(requests)
            total_time = sum(r.get("generation_time_ms", 0) for r in successful_generations)
            
            logger.info(f"✅ Batch generation completed: {len(successful_generations)} successful, {len(failed_generations)} failed")
            logger.info(f"   Success rate: {success_rate:.1%}, Total time: {total_time:.1f}ms")
            
            return {
                "success": True,
                "total_requests": len(requests),
                "successful_generations": successful_generations,
                "failed_generations": failed_generations,
                "success_rate": success_rate,
                "total_generation_time_ms": total_time,
                "average_generation_time_ms": total_time / len(successful_generations) if successful_generations else 0
            }
            
        except Exception as e:
            error_msg = f"Batch generation failed: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def generate_product_designs(
        self,
        trend_name: str,
        product_types: List[str],
        design_styles: List[str],
        num_designs_per_product: int = 3
    ) -> Dict[str, Any]:
        """Generate product designs for specific trend and product types
        
        Args:
            trend_name: Name of the trend
            product_types: List of product types to generate designs for
            design_styles: List of design styles to apply
            num_designs_per_product: Number of designs per product type
        
        Returns:
            Generated product designs
        """
        try:
            logger.info(f"🎨 Generating product designs for trend: {trend_name}")
            
            all_requests = []
            design_mapping = {}
            
            for product_type in product_types:
                for style in design_styles:
                    for i in range(num_designs_per_product):
                        # Create design prompt
                        prompt = self._create_design_prompt(trend_name, product_type, style, i + 1)
                        negative_prompt = self._create_negative_prompt()
                        
                        request = ImageGenerationRequest(
                            prompt=prompt,
                            negative_prompt=negative_prompt,
                            width=1024,
                            height=1024,
                            style_preset=style
                        )
                        
                        all_requests.append(request)
                        design_mapping[len(all_requests) - 1] = {
                            "trend_name": trend_name,
                            "product_type": product_type,
                            "style": style,
                            "design_number": i + 1
                        }
            
            # Generate all designs
            batch_result = await self.generate_batch(all_requests)
            
            if not batch_result.get("success"):
                return batch_result
            
            # Organize results by product type and style
            organized_designs = {}
            for product_type in product_types:
                organized_designs[product_type] = {}
                for style in design_styles:
                    organized_designs[product_type][style] = []
            
            # Map results back to their context
            for i, generation in enumerate(batch_result["successful_generations"]):
                context = design_mapping.get(i, {})
                product_type = context.get("product_type")
                style = context.get("style")
                
                if product_type and style:
                    organized_designs[product_type][style].append({
                        "generated_image": generation["generated_image"],
                        "context": context,
                        "generation_metadata": {
                            "generation_time_ms": generation["generation_time_ms"],
                            "model_used": generation["model_used"],
                            "storage_url": generation.get("storage_url")
                        }
                    })
            
            logger.info(f"✅ Product design generation completed for {len(product_types)} product types")
            
            return {
                "success": True,
                "trend_name": trend_name,
                "organized_designs": organized_designs,
                "total_designs": len(batch_result["successful_generations"]),
                "success_rate": batch_result["success_rate"],
                "generation_metadata": {
                    "total_time_ms": batch_result["total_generation_time_ms"],
                    "average_time_ms": batch_result["average_generation_time_ms"],
                    "models_used": list(set(g["model_used"] for g in batch_result["successful_generations"]))
                }
            }
            
        except Exception as e:
            error_msg = f"Product design generation failed: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    def _create_design_prompt(
        self, 
        trend_name: str, 
        product_type: str, 
        style: str, 
        design_number: int
    ) -> str:
        """Create a design prompt based on trend, product type, and style"""
        
        style_prompts = {
            "photographic": "high-quality photographic style",
            "illustration": "clean vector illustration style",
            "minimalist": "minimalist design with clean lines",
            "vintage": "vintage retro aesthetic",
            "modern": "contemporary modern design",
            "artistic": "artistic creative style",
            "professional": "professional business style",
            "playful": "fun playful design style"
        }
        
        style_desc = style_prompts.get(style, "professional design style")
        
        prompt = f"Create a {style_desc} design for a {product_type} featuring the trend '{trend_name}'. "
        prompt += f"The design should be visually appealing, on-trend, and suitable for print-on-demand. "
        prompt += f"Design variation {design_number}. "
        prompt += f"High resolution, clean composition, commercial use ready."
        
        return prompt
    
    def _create_negative_prompt(self) -> str:
        """Create a negative prompt to avoid unwanted elements"""
        return "blurry, low quality, text overlay, watermarks, logos, copyrighted material, inappropriate content, distorted, pixelated"
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health and connectivity"""
        try:
            # Test Vertex AI connection
            vertex_health = await self.vertex_ai_client.health_check()
            
            if not vertex_health.get("success"):
                return {"success": False, "status": "unhealthy", "error": "Vertex AI connection failed"}
            
            # Test storage connection if available
            storage_health = None
            if self.storage_client:
                storage_health = await self.storage_client.get_storage_stats()
            
            return {
                "success": True,
                "status": "healthy",
                "vertex_ai": vertex_health,
                "storage": storage_health,
                "config": self.default_config
            }
            
        except Exception as e:
            return {"success": False, "status": "error", "error": str(e)}


async def generate_product_design(
    vertex_ai_client: VertexAIClient,
    prompt: str,
    width: int = 1024,
    height: int = 1024
) -> Dict[str, Any]:
    """Convenience function to generate a single product design"""
    service = ImageGenerationService(vertex_ai_client)
    try:
        request = ImageGenerationRequest(
            prompt=prompt,
            width=width,
            height=height
        )
        return await service.generate_image(request)
    finally:
        await service.close()


async def generate_product_designs_batch(
    vertex_ai_client: VertexAIClient,
    trend_name: str,
    product_types: List[str],
    design_styles: List[str],
    num_designs_per_product: int = 3
) -> Dict[str, Any]:
    """Convenience function to generate product designs in batch"""
    service = ImageGenerationService(vertex_ai_client)
    try:
        return await service.generate_product_designs(
            trend_name=trend_name,
            product_types=product_types,
            design_styles=design_styles,
            num_designs_per_product=num_designs_per_product
        )
    finally:
        await service.close()
