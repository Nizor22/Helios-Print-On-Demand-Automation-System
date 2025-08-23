"""
Etsy API Client for Helios Autonomous Store
Provides direct Etsy integration for product management and analytics
Note: This is a backup/future implementation when Etsy API access is approved
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from pathlib import Path
import httpx
from loguru import logger


@dataclass
class EtsyProduct:
    """Etsy product data structure"""
    title: str
    description: str
    price: float
    currency_code: str = "USD"
    quantity: int = 1
    tags: List[str] = None
    materials: List[str] = None
    shipping_profile_id: Optional[int] = None
    shop_section_id: Optional[int] = None
    state: str = "draft"  # draft, active, inactive
    is_supply: bool = False
    is_customizable: bool = False
    is_digital: bool = False
    language: str = "en"


@dataclass
class EtsyListing:
    """Etsy listing data structure"""
    listing_id: int
    title: str
    description: str
    state: str
    quantity: int
    price: Dict[str, Any]
    tags: List[str]
    materials: List[str]
    created_timestamp: int
    updated_timestamp: int
    views: int = 0
    num_favorers: int = 0


class EtsyAPIClient:
    """Etsy API client for Helios Autonomous Store"""
    
    def __init__(self, api_key: str = None, shop_id: str = None):
        self.api_key = api_key
        self.shop_id = shop_id
        self.base_url = "https://openapi.etsy.com/v3"
        
        # Rate limiting configuration
        self.rate_limit_delay = 1.0  # seconds between calls
        self.max_retries = 3
        self.retry_delay = 1.0
        
        # API endpoints
        self.endpoints = {
            "shop_listings": f"/application/shops/{{shop_id}}/listings/active",
            "create_listing": f"/application/listings",
            "update_listing": f"/application/listings/{{listing_id}}",
            "delete_listing": f"/application/listings/{{listing_id}}",
            "upload_image": f"/application/listings/{{listing_id}}/images",
            "shop_stats": f"/application/shops/{{shop_id}}/stats",
            "shop_reviews": f"/application/shops/{{shop_id}}/reviews"
        }
        
        # HTTP client configuration
        self.headers = {
            "x-api-key": api_key if api_key else "",
            "Content-Type": "application/json",
            "User-Agent": "Helios-Autonomous-Store/1.0"
        }
        
        logger.info(f"✅ Etsy API client initialized for shop: {shop_id}")
    
    async def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        data: Dict[str, Any] = None,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Make HTTP request to Etsy API with rate limiting and retry logic"""
        
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
    
    async def get_shop_listings(self, limit: int = 100) -> Dict[str, Any]:
        """Get active listings from the shop
        
        Args:
            limit: Maximum number of listings to retrieve
        
        Returns:
            List of shop listings
        """
        try:
            if not self.shop_id:
                return {"success": False, "error": "Shop ID not configured"}
            
            params = {"limit": limit}
            
            result = await self._make_request(
                endpoint=self.endpoints["shop_listings"].format(shop_id=self.shop_id),
                method="GET",
                params=params
            )
            
            if result["success"]:
                listings = result["data"].get("results", [])
                logger.info(f"✅ Retrieved {len(listings)} listings from Etsy shop")
                return {
                    "success": True,
                    "listings": listings,
                    "total_count": len(listings)
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Failed to retrieve shop listings: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def create_listing(self, product_data: EtsyProduct) -> Dict[str, Any]:
        """Create a new listing on Etsy
        
        Args:
            product_data: Product information
        
        Returns:
            Listing creation result
        """
        try:
            # Prepare listing payload
            payload = {
                "title": product_data.title,
                "description": product_data.description,
                "price": product_data.price,
                "currency_code": product_data.currency_code,
                "quantity": product_data.quantity,
                "tags": product_data.tags or [],
                "materials": product_data.materials or [],
                "shipping_profile_id": product_data.shipping_profile_id,
                "shop_section_id": product_data.shop_section_id,
                "state": product_data.state,
                "is_supply": product_data.is_supply,
                "is_customizable": product_data.is_customizable,
                "is_digital": product_data.is_digital,
                "language": product_data.language
            }
            
            result = await self._make_request(
                endpoint=self.endpoints["create_listing"],
                method="POST",
                data=payload
            )
            
            if result["success"]:
                listing_info = result["data"]
                logger.info(f"✅ Listing created on Etsy: {listing_info.get('listing_id')}")
                return {
                    "success": True,
                    "listing_id": listing_info.get("listing_id"),
                    "listing_data": listing_info,
                    "status": "created"
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Listing creation failed: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def upload_listing_image(
        self, 
        listing_id: int,
        image_data: bytes,
        file_name: str
    ) -> Dict[str, Any]:
        """Upload image to an Etsy listing
        
        Args:
            listing_id: Etsy listing ID
            image_data: Image bytes
            file_name: Name of the image file
        
        Returns:
            Image upload result
        """
        try:
            # For now, return a placeholder since direct image upload requires OAuth
            logger.info(f"Image upload to Etsy listing {listing_id} would require OAuth 2.0")
            return {
                "success": True,
                "message": "Image upload requires OAuth 2.0 authentication",
                "listing_id": listing_id,
                "file_name": file_name,
                "status": "placeholder"
            }
                
        except Exception as e:
            error_msg = f"Image upload failed: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def get_shop_stats(self, time_range: str = "30d") -> Dict[str, Any]:
        """Get shop statistics and performance metrics
        
        Args:
            time_range: Time range for statistics (7d, 30d, 90d, 1y)
        
        Returns:
            Shop statistics
        """
        try:
            if not self.shop_id:
                return {"success": False, "error": "Shop ID not configured"}
            
            params = {"time_range": time_range}
            
            result = await self._make_request(
                endpoint=self.endpoints["shop_stats"].format(shop_id=self.shop_id),
                method="GET",
                params=params
            )
            
            if result["success"]:
                stats = result["data"]
                logger.info(f"✅ Retrieved shop statistics for {time_range}")
                return {
                    "success": True,
                    "stats": stats,
                    "time_range": time_range
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Failed to retrieve shop stats: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def get_shop_reviews(self, limit: int = 50) -> Dict[str, Any]:
        """Get shop reviews and ratings
        
        Args:
            limit: Maximum number of reviews to retrieve
        
        Returns:
            Shop reviews
        """
        try:
            if not self.shop_id:
                return {"success": False, "error": "Shop ID not configured"}
            
            params = {"limit": limit}
            
            result = await self._make_request(
                endpoint=self.endpoints["shop_reviews"].format(shop_id=self.shop_id),
                method="GET",
                params=params
            )
            
            if result["success"]:
                reviews = result["data"].get("results", [])
                logger.info(f"✅ Retrieved {len(reviews)} shop reviews")
                return {
                    "success": True,
                    "reviews": reviews,
                    "total_count": len(reviews)
                }
            else:
                return result
                
        except Exception as e:
            error_msg = f"Failed to retrieve shop reviews: {e}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health and connectivity"""
        try:
            if not self.shop_id:
                return {"success": False, "status": "unconfigured", "error": "Shop ID not set"}
            
            result = await self.get_shop_listings(limit=1)
            
            if result["success"]:
                return {"success": True, "status": "healthy", "message": "API connection successful"}
            else:
                return {"success": False, "status": "unhealthy", "error": result.get("error")}
                
        except Exception as e:
            return {"success": False, "status": "error", "error": str(e)}


async def get_etsy_shop_listings(
    api_key: str,
    shop_id: str,
    limit: int = 100
) -> Dict[str, Any]:
    """Convenience function to get Etsy shop listings"""
    client = EtsyAPIClient(api_key, shop_id)
    try:
        return await client.get_shop_listings(limit)
    finally:
        await client.close()


async def create_etsy_listing(
    api_key: str,
    product_data: EtsyProduct
) -> Dict[str, Any]:
    """Convenience function to create an Etsy listing"""
    client = EtsyAPIClient(api_key)
    try:
        return await client.create_listing(product_data)
    finally:
        await client.close()
