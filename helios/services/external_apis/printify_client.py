"""
Printify API Client for Helios Autonomous Store
Handles product creation, image uploads, and store management
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import httpx
from loguru import logger

from ..google_cloud.storage_client import CloudStorageClient


@dataclass
class PrintifyProduct:
    """Printify product data structure"""
    title: str
    description: str
    blueprint_id: int
    print_provider_id: int
    variants: List[Dict[str, Any]]
    print_areas: List[Dict[str, Any]]
    tags: List[str] = None
    is_enabled: bool = True
    is_draft: bool = True


@dataclass
class PrintifyImage:
    """Printify image data structure"""
    file_name: str
    url: str
    width: int
    height: int
    preview_url: str = None


class PrintifyAPIClient:
    """Printify API client for Helios Autonomous Store"""
    
    def __init__(
        self, 
        api_token: str,
        shop_id: str,
        storage_client: CloudStorageClient = None
    ):
        self.api_token = api_token
        self.shop_id = shop_id
        self.base_url = "https://api.printify.com/v1"
        self.storage_client = storage_client
        
        # Rate limiting configuration
        self.rate_limit_delay = 2.0  # seconds between calls
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # API endpoints
        self.endpoints = {
            "upload_image": "/uploads/images.json",
            "create_product": f"/shops/{shop_id}/products.json",
            "publish_product": f"/shops/{shop_id}/products/{{product_id}}/publish.json",
            "get_products": f"/shops/{shop_id}/products.json",
            "get_product": f"/shops/{shop_id}/products/{{product_id}}.json",
            "update_product": f"/shops/{shop_id}/products/{{product_id}}.json",
            "delete_product": f"/shops/{shop_id}/products/{{product_id}}.json",
            # Catalog endpoints
            "catalog_blueprints": "/catalog/blueprints.json",
            "catalog_providers": "/catalog/blueprints/{blueprint_id}/print_providers.json",
            "catalog_variants": "/catalog/blueprints/{blueprint_id}/print_providers/{provider_id}/variants.json"
        }
        
        # HTTP client configuration
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "User-Agent": "Helios-Autonomous-Store/1.0"
        }
        
        logger.info(f"✅ Printify API client initialized for shop: {shop_id}")
    
    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Printify API with rate limiting and retry logic"""
        
        url = f"{self.base_url}{endpoint}"
        
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    if method == "GET":
                        response = await client.get(url, headers=self.headers, params=params)
                    elif method == "POST":
                        response = await client.post(url, headers=self.headers, json=data)
                    elif method == "PUT":
                        response = await client.put(url, headers=self.headers, json=data)
                    elif method == "DELETE":
                        response = await client.delete(url, headers=self.headers)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                    
                    # Rate limiting
                    await asyncio.sleep(self.rate_limit_delay)
                    
                    if response.status_code == 200:
                        return {"success": True, "data": response.json()}
                    elif response.status_code == 201:
                        return {"success": True, "data": response.json()}
                    elif response.status_code == 429:  # Rate limited
                        retry_after = int(response.headers.get("Retry-After", 60))
                        logger.warning(f"Rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        error_msg = f"API request failed: {response.status_code} - {response.text}"
                        logger.error(error_msg)
                        return {"success": False, "error": error_msg, "status_code": response.status_code}
                        
            except Exception as e:
                if attempt < self.max_retries - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    logger.warning(f"Request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    await asyncio.sleep(wait_time)
                else:
                    error_msg = f"Request failed after {self.max_retries} attempts: {e}"
                    logger.error(error_msg)
                    return {"success": False, "error": error_msg}
        
        return {"success": False, "error": "Max retries exceeded"}
    
    async def upload_image(
        self, 
        file_name: str,
        image_data: bytes,
        content_type: str = "image/png"
    ) -> Dict[str, Any]:
        """Upload image to Printify
        
        Args:
            image_data: Image bytes
            file_name: Name of the image file
            content_type: MIME type of the image
        
        Returns:
            Upload result with image ID and URLs
        """
        try:
            # First upload to Cloud Storage if available
            if self.storage_client:
                storage_result = await self.storage_client.store_product_design(
                    design_data=image_data,
                    trend_name="printify_upload",
                    design_type="product_image",
                    content_type=content_type
                )
                
                if storage_result.get("success"):
                    image_url = storage_result["public_url"]
                    logger.info(f"Image uploaded to Cloud Storage: {image_url}")
                else:
                    # Fallback to direct upload
                    image_url = None
            else:
                image_url = None
            
            # Upload to Printify
            if image_url:
                # Use Cloud Storage URL if available
                upload_data = {
                    "file_name": file_name,
                    "url": image_url
                }
            else:
                # Convert image data to base64 for direct upload
                import base64
                b64_data = base64.b64encode(image_data).decode('utf-8')
                upload_data = {
                    "file_name": file_name,
                    "contents": b64_data
                }
            
            result = await self._make_request(
                endpoint=self.endpoints["upload_image"],
                method="POST",
                data=upload_data
            )
            
            if result["success"]:
                image_info = result["data"]
                logger.info(f"✅ Image uploaded to Printify: {image_info.get('id')}")
                return {
                    "success": True,
                    "image_id": image_info.get("id"),
                    "printify_url": image_info.get("url"),
                    "storage_url": image_url,
                    "file_name": file_name
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Image upload failed: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def create_product(self, product_data: Union[PrintifyProduct, Dict[str, Any]]) -> Dict[str, Any]:
        """Create a new product on Printify
        
        Args:
            product_data: Product information
        
        Returns:
            Product creation result
        """
        try:
            # Prepare product payload - handle both PrintifyProduct objects and dictionaries
            if hasattr(product_data, 'title'):
                # PrintifyProduct object
                payload = {
                    "title": product_data.title,
                    "description": product_data.description,
                    "blueprint_id": product_data.blueprint_id,
                    "print_provider_id": product_data.print_provider_id,
                    "variants": product_data.variants,
                    "print_areas": product_data.print_areas,
                    "tags": product_data.tags or [],
                    "is_enabled": product_data.is_enabled,
                    "is_draft": product_data.is_draft
                }
            else:
                # Dictionary - use directly
                payload = product_data

            # Ensure image IDs in print_areas use the correct key from upload_image
            try:
                for area in payload.get("print_areas", []) or []:
                    for ph in area.get("placeholders", []) or []:
                        for img in ph.get("images", []) or []:
                            if "printify_image_id" in img and "id" not in img:
                                img["id"] = img.pop("printify_image_id")
            except Exception:
                pass
            
            result = await self._make_request(
                endpoint=self.endpoints["create_product"],
                method="POST",
                data=payload
            )
            
            if result["success"]:
                product_info = result["data"]
                logger.info(f"✅ Product created on Printify: {product_info.get('id')}")
                return {
                    "success": True,
                    "printify_product_id": product_info.get("id"),
                    "product_data": product_info,
                    "status": "created"
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Product creation failed: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}

    async def get_blueprints(self) -> Dict[str, Any]:
        """Fetch available blueprints from Printify catalog"""
        try:
            result = await self._make_request(
                endpoint=self.endpoints["catalog_blueprints"],
                method="GET"
            )
            if result["success"]:
                return {"success": True, "data": result["data"]}
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_print_providers(self, blueprint_id: int) -> Dict[str, Any]:
        """Fetch print providers for a given blueprint"""
        try:
            endpoint = self.endpoints["catalog_providers"].format(blueprint_id=blueprint_id)
            result = await self._make_request(endpoint=endpoint, method="GET")
            if result["success"]:
                return {"success": True, "data": result["data"]}
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def get_variants(self, blueprint_id: int, provider_id: int) -> Dict[str, Any]:
        """Fetch variants for a blueprint/provider combo"""
        try:
            endpoint = self.endpoints["catalog_variants"].format(blueprint_id=blueprint_id, provider_id=provider_id)
            result = await self._make_request(endpoint=endpoint, method="GET")
            if result["success"]:
                return {"success": True, "data": result["data"]}
            return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def publish_product(self, product_id: str) -> Dict[str, Any]:
        """Publish a product to connected stores
        
        Args:
            product_id: Printify product ID
        
        Returns:
            Publishing result
        """
        try:
            publish_data = {
                "title": True,
                "description": True,
                "images": True,
                "variants": True,
                "tags": True,
                "keyFeatures": True,
                "shipping_template": True,
                "redirect_template": True,
                "gift_card": True
            }
            
            result = await self._make_request(
                endpoint=self.endpoints["publish_product"].format(product_id=product_id),
                method="POST",
                data=publish_data
            )
            
            if result["success"]:
                logger.info(f"✅ Product published: {product_id}")
                return {
                    "success": True,
                    "product_id": product_id,
                    "status": "published",
                    "publish_data": result["data"]
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Product publishing failed: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def publish_batch(self, products_to_publish: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Publish multiple products in batch
        
        Args:
            products_to_publish: List of products with designs and marketing data
        
        Returns:
            List of publishing results
        """
        try:
            logger.info(f"🚀 Publishing batch of {len(products_to_publish)} products")
            
            publish_tasks = []
            for product_data in products_to_publish:
                # Create product first
                create_task = self._create_and_publish_product(product_data)
                publish_tasks.append(create_task)
            
            # Execute all tasks concurrently
            results = await asyncio.gather(*publish_tasks, return_exceptions=True)
            
            # Process results
            successful_publishes = []
            failed_publishes = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    failed_publishes.append({
                        "index": i,
                        "error": str(result),
                        "product_data": products_to_publish[i]
                    })
                elif result.get("success"):
                    successful_publishes.append(result)
                else:
                    failed_publishes.append({
                        "index": i,
                        "error": result.get("error", "Unknown error"),
                        "product_data": products_to_publish[i]
                    })
            
            logger.info(f"✅ Batch publishing completed: {len(successful_publishes)} successful, {len(failed_publishes)} failed")
            
            return {
                "success": True,
                "total_products": len(products_to_publish),
                "successful_publishes": successful_publishes,
                "failed_publishes": failed_publishes,
                "success_rate": len(successful_publishes) / len(products_to_publish)
            }
            
        except Exception as e:
            error_msg = f"Batch publishing failed: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def _create_and_publish_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Helper method to create and publish a single product"""
        try:
            design = product_data["design"]
            product = product_data["product"]
            marketing = product_data["marketing"]
            
            # Upload design image
            image_result = await self.upload_image(
                file_name=f"{design['trend_name']}_{product['type']}.png",
                image_data=design["image_data"]
            )
            
            if not image_result["success"]:
                return {"success": False, "error": f"Image upload failed: {image_result['error']}"}
            
            # Create product
            printify_product = PrintifyProduct(
                title=marketing["title"],
                description=marketing["description"],
                blueprint_id=product["blueprint_id"],
                print_provider_id=product["print_provider_id"],
                variants=product["variants"],
                print_areas=[{
                    "variant_ids": [v["id"] for v in product["variants"]],
                    "placeholders": [{
                        "position": "front",
                        "images": [{
                            "id": image_result.get("image_id") or image_result.get("printify_image_id"),
                            "x": 0.5,
                            "y": 0.5,
                            "scale": 1.0,
                            "angle": 0
                        }]
                    }]
                }],
                tags=marketing["tags"],
                is_draft=product.get("is_draft", True)
            )
            
            create_result = await self.create_product(printify_product)
            
            if not create_result["success"]:
                return {"success": False, "error": f"Product creation failed: {create_result['error']}"}
            
            # Publish product
            publish_result = await self.publish_product(create_result["printify_product_id"])
            
            if not publish_result["success"]:
                return {"success": False, "error": f"Product publishing failed: {publish_result['error']}"}
            
            return {
                "success": True,
                "product_id": create_result["printify_product_id"],
                "image_id": image_result.get("image_id") or image_result.get("printify_image_id"),
                "status": "published",
                "design": design,
                "product": product,
                "marketing": marketing
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def get_products(self, limit: int = 100) -> Dict[str, Any]:
        """Get list of products from the shop
        
        Args:
            limit: Maximum number of products to retrieve
        
        Returns:
            List of products
        """
        try:
            params = {"limit": limit}
            
            result = await self._make_request(
                endpoint=self.endpoints["get_products"],
                method="GET",
                params=params
            )
            
            if result["success"]:
                products = result["data"].get("data", [])
                logger.info(f"✅ Retrieved {len(products)} products from Printify")
                return {
                    "success": True,
                    "products": products,
                    "total_count": len(products)
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Failed to retrieve products: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health and connectivity"""
        try:
            result = await self._make_request(
                endpoint="/shops.json",
                method="GET"
            )
            
            if result["success"]:
                return {"success": True, "status": "healthy", "message": "API connection successful"}
            else:
                return {"success": False, "status": "unhealthy", "error": result.get("error")}
                
        except Exception as e:
            return {"success": False, "status": "error", "error": str(e)}


async def create_printify_product(
    api_token: str,
    shop_id: str,
    product_data: PrintifyProduct
) -> Dict[str, Any]:
    """Convenience function to create a Printify product"""
    client = PrintifyAPIClient(api_token, shop_id)
    try:
        return await client.create_product(product_data)
    finally:
        await client.close()


async def publish_printify_product(
    api_token: str,
    shop_id: str,
    product_id: str
) -> Dict[str, Any]:
    """Convenience function to publish a Printify product"""
    client = PrintifyAPIClient(api_token, shop_id)
    try:
        return await client.publish_product(product_id)
    finally:
        await client.close()
