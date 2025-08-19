"""
Google Cloud Vertex AI Client for Helios Autonomous Store
Provides integration with Gemini AI models for text and image generation
"""

import os
import asyncio
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import json
import time

import vertexai
from vertexai.generative_models import GenerativeModel, Part
from google.cloud import aiplatform
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError

from loguru import logger
try:
    import google.generativeai as genai
except Exception:
    genai = None
try:
    # Imagen 3 (preview) image generation
    from vertexai.preview.vision_models import ImageGenerationModel
except Exception:
    ImageGenerationModel = None


@dataclass
class GeminiModelConfig:
    """Configuration for Gemini AI models"""
    model_name: str
    max_tokens: int
    temperature: float
    top_p: float = 0.8
    top_k: int = 40
    use_cases: List[str] = None


class VertexAIClient:
    """
    Google Cloud Vertex AI client for Helios Autonomous Store
    Handles text generation, analysis, and image generation using Gemini models
    """
    
    def __init__(self, project_id: str = None, location: str = "us-central1"):
        # Keep project/location for Sheets/Drive; not required for Gemini direct API
        self.project_id = project_id or os.getenv("GOOGLE_CLOUD_PROJECT")
        self.location = location
        self.initialized = True

        # Configure direct Gemini API if available
        api_key = os.getenv("GEMINI_API_KEY")
        if genai and api_key:
            try:
                genai.configure(api_key=api_key)
            except Exception as e:
                logger.warning(f"Gemini configure failed: {e}")

        # Model configurations (names come from env or sensible defaults)
        self.models = {
            "gemini_pro": GeminiModelConfig(
                model_name=os.getenv("GEMINI_PRO_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash")),
                max_tokens=8192,
                temperature=0.7,
                use_cases=["Complex analysis", "Strategy formulation"]
            ),
            "gemini_flash": GeminiModelConfig(
                model_name=os.getenv("GEMINI_FLASH_MODEL", "gemini-2.0-flash-lite-001"),
                max_tokens=8192,
                temperature=0.8,
                use_cases=["Rapid processing", "Copy generation"]
            ),
            "gemini_ultra": GeminiModelConfig(
                model_name=os.getenv("GEMINI_ULTRA_MODEL", os.getenv("GEMINI_MODEL", "gemini-2.5-flash")),
                max_tokens=32768,
                temperature=0.5,
                use_cases=["CEO orchestration", "Critical decisions"]
            )
        }

        # Image model (prefer Imagen 3 if configured)
        self.image_model = os.getenv("IMAGEN_MODEL", os.getenv("GEMINI_IMAGE_MODEL", "imagen-3.0-generate-001"))
        try:
            if self.project_id and self.location:
                vertexai.init(project=self.project_id, location=self.location)
        except Exception as e:
            logger.warning(f"Vertex AI init failed: {e}")
    
    def _initialize_client(self):
        # No-op for direct Gemini API
        self.initialized = True
    
    def get_model(self, model_type: str = "gemini_pro"):
        if model_type not in self.models:
            raise ValueError(f"Unknown model type: {model_type}")
        config = self.models[model_type]
        if not genai:
            raise RuntimeError("google-generativeai not available")
        return genai.GenerativeModel(config.model_name)
    
    async def generate_text(
        self,
        prompt: str,
        model_type: str = "gemini_pro",
        system_prompt: str = None,
        context: List[Dict] = None,
        model: Optional[str] = None,
        **kwargs: Any
    ) -> str:
        """
        Generate text using Gemini AI
        
        Args:
            prompt: The main prompt for text generation
            model_type: Type of Gemini model to use
            system_prompt: Optional system prompt for context
            context: Optional conversation context
            
        Returns:
            Dictionary containing generated text and metadata
        """
        try:
            # Allow callers to pass explicit model name via `model`
            if model:
                # If a full gemini model name is provided, use it directly
                try:
                    text_model = genai.GenerativeModel(model)
                except Exception:
                    text_model = self.get_model(model_type)
            else:
                text_model = self.get_model(model_type)
            # Concatenate system/context into a single prompt for simplicity
            full_prompt_parts: List[str] = []
            if system_prompt:
                full_prompt_parts.append(system_prompt)
            if context:
                try:
                    for entry in context:
                        if isinstance(entry, dict):
                            part = entry.get("parts") or entry.get("content") or ""
                            if isinstance(part, list):
                                full_prompt_parts.extend([str(p) for p in part])
                            else:
                                full_prompt_parts.append(str(part))
                        else:
                            full_prompt_parts.append(str(entry))
                except Exception:
                    pass
            full_prompt_parts.append(prompt)
            full_prompt = "\n\n".join([p for p in full_prompt_parts if p])

            response = await asyncio.to_thread(text_model.generate_content, full_prompt)
            text = getattr(response, "text", "") or ""
            logger.info(f"✅ Text generated using {model_type}: {len(text)} characters")
            return text
            
        except Exception as e:
            logger.error(f"❌ Text generation failed: {e}")
            return ""
    
    async def analyze_trend(
        self,
        trend_data: Dict[str, Any],
        analysis_type: str = "comprehensive"
    ) -> Dict[str, Any]:
        """
        Analyze trend data using Gemini AI
        
        Args:
            trend_data: Dictionary containing trend information
            analysis_type: Type of analysis to perform
            
        Returns:
            Analysis results with insights and recommendations
        """
        # Use Gemini Pro for complex trend analysis
        model_type = "gemini_pro"
        
        prompt = f"""
        Analyze the following trend data and provide comprehensive insights:
        
        Trend: {trend_data.get('trend_name', 'Unknown')}
        Keywords: {trend_data.get('keywords', [])}
        Volume: {trend_data.get('volume', 'Unknown')}
        Growth: {trend_data.get('growth_rate', 'Unknown')}
        
        Please provide:
        1. Opportunity assessment (1-10 scale)
        2. Target audience analysis
        3. Product category recommendations
        4. Marketing angle suggestions
        5. Risk factors
        6. Timeline recommendations
        
        Analysis type: {analysis_type}
        """
        
        return await self.generate_text(prompt, model_type)
    
    async def generate_marketing_copy(
        self,
        product_info: Dict[str, Any],
        target_audience: Dict[str, Any],
        tone: str = "persuasive"
    ) -> Dict[str, Any]:
        """
        Generate marketing copy using Gemini Flash for speed
        
        Args:
            product_info: Product details
            target_audience: Target audience information
            tone: Desired tone for the copy
            
        Returns:
            Generated marketing copy and variations
        """
        model_type = "gemini_flash"
        
        prompt = f"""
        Generate compelling marketing copy for this product:
        
        Product: {product_info.get('name', 'Unknown')}
        Category: {product_info.get('category', 'Unknown')}
        Target Audience: {target_audience.get('demographic_cluster', 'Unknown')}
        Tone: {tone}
        
        Generate:
        1. Product title (SEO optimized)
        2. Short description (2-3 sentences)
        3. Long description (5-7 sentences)
        4. 5-7 bullet points highlighting benefits
        5. Call-to-action variations
        
        Make it engaging, persuasive, and optimized for e-commerce conversion.
        """
        
        return await self.generate_text(prompt, model_type)
    
    async def generate_product_strategy(
        self,
        trend_analysis: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate product strategy using Gemini Ultra for complex decision making
        
        Args:
            trend_analysis: Results from trend analysis
            market_data: Market and competitor information
            
        Returns:
            Comprehensive product strategy
        """
        model_type = "gemini_ultra"
        
        prompt = f"""
        Based on the following data, generate a comprehensive product strategy:
        
        Trend Analysis:
        {json.dumps(trend_analysis, indent=2)}
        
        Market Data:
        {json.dumps(market_data, indent=2)}
        
        Provide:
        1. Product positioning strategy
        2. Pricing strategy with margin recommendations
        3. Launch timeline
        4. Marketing channel prioritization
        5. Risk mitigation strategies
        6. Success metrics and KPIs
        7. Competitive advantage analysis
        
        This is for a print-on-demand e-commerce business. Be strategic and data-driven.
        """
        
        return await self.generate_text(prompt, model_type)
    
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        guidance_scale: float = 7.5,
        num_inference_steps: int = 50,
        seed: Optional[int] = None,
        model: str = None
    ) -> Dict[str, Any]:
        """
        Generate image using Vertex AI Imagen 4.0. Returns image data and metadata.
        """
        try:
            logger.info(f"🖼️ Image generation requested: {prompt}")
            
            if ImageGenerationModel is None:
                raise RuntimeError("Imagen model not available in this environment")

            # Use specified model or default
            model_name = model or self.image_model
            logger.info(f"Using model: {model_name}")
            
            imagen_model = ImageGenerationModel.from_pretrained(model_name)
            
            # Determine aspect ratio from width/height
            aspect_ratio = "1:1"  # Default
            if width == height:
                aspect_ratio = "1:1"
            elif width > height:
                if width / height == 4/3:
                    aspect_ratio = "4:3"
                elif width / height == 16/9:
                    aspect_ratio = "16:9"
            elif height > width:
                if height / width == 4/3:
                    aspect_ratio = "3:4"
                elif height / width == 16/9:
                    aspect_ratio = "9:16"
            
            raw = await asyncio.to_thread(
                imagen_model.generate_images,
                prompt=prompt,
                number_of_images=1,
                aspect_ratio=aspect_ratio,
                safety_filter_level="block_moderate_and_above",
            )
            
            # Normalize output across SDK variants
            images = []
            if isinstance(raw, list):
                images = raw
            elif hasattr(raw, "generated_images"):
                images = getattr(raw, "generated_images") or []
            elif hasattr(raw, "images"):
                images = getattr(raw, "images") or []

            if not images:
                raise RuntimeError("No image returned from Imagen (empty result)")
            
            img = images[0]
            img_bytes = None
            for attr in ("_image_bytes", "image_bytes", "bytes"):
                val = getattr(img, attr, None)
                if val:
                    img_bytes = val
                    break
            if img_bytes is None and hasattr(img, "as_bytes"):
                try:
                    img_bytes = img.as_bytes()
                except Exception:
                    pass
            if img_bytes is None:
                raise RuntimeError("Imagen returned no bytes for image")
            
            return {
                "success": True,
                "image_data": img_bytes,
                "model_used": model_name,
                "width": width,
                "height": height,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "aspect_ratio": aspect_ratio,
                "safety_score": 1.0  # Default safety score
            }
        except Exception as e:
            logger.error(f"❌ Image generation failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def batch_generate_text(
        self,
        prompts: List[str],
        model_type: str = "gemini_flash"
    ) -> List[Dict[str, Any]]:
        """
        Generate text for multiple prompts in batch
        
        Args:
            prompts: List of prompts to process
            model_type: Type of Gemini model to use
            
        Returns:
            List of generation results
        """
        tasks = []
        for prompt in prompts:
            task = self.generate_text(prompt, model_type)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append({
                    "status": "error",
                    "error": str(result),
                    "prompt_index": i,
                    "timestamp": time.time()
                })
            else:
                processed_results.append({
                    "status": "success",
                    "text": result,
                    "prompt_index": i
                })
        
        logger.info(f"✅ Batch text generation completed: {len(processed_results)} prompts")
        return processed_results
    
    def get_model_info(self, model_type: str = None) -> Dict[str, Any]:
        """Get information about available models"""
        if model_type:
            if model_type not in self.models:
                return {"error": f"Unknown model type: {model_type}"}
            return {
                "model_type": model_type,
                **self.models[model_type].__dict__
            }
        
        return {
            "available_models": list(self.models.keys()),
            "models": self.models,
            "image_model": self.image_model,
            "project_id": self.project_id,
            "location": self.location
        }
    
    async def close(self):
        """Close the Vertex AI client and clean up resources"""
        try:
            # Close any internal clients if they exist
            logger.info("✅ Vertex AI client closed")
        except Exception as e:
            logger.error(f"❌ Error closing Vertex AI client: {e}")


# Convenience functions for common operations
async def analyze_trend_with_ai(trend_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for trend analysis"""
    client = VertexAIClient()
    return await client.analyze_trend(trend_data)


async def generate_marketing_copy_ai(product_info: Dict[str, Any], audience: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for marketing copy generation"""
    client = VertexAIClient()
    return await client.generate_marketing_copy(product_info, audience)


async def generate_product_strategy_ai(trend_analysis: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function for product strategy generation"""
    client = VertexAIClient()
    return await client.generate_product_strategy(trend_analysis, market_data)
