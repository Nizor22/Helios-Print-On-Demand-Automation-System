from __future__ import annotations

import time
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Dict, List

from ..publisher.printify_publisher import PrintifyPublisher


@dataclass
class PublicationResult:
    product_title: str
    printify_product_id: str | None
    image_upload_id: str | None
    status: str
    final_price_cents: int
    error_details: str | None = None


class PrintifyPublisherAgent:
    def __init__(self, api_token: str, shop_id: str) -> None:
        self.publisher = PrintifyPublisher(api_token=api_token, shop_id=shop_id)

    def run_batch(
        self,
        listings: List[Dict[str, Any]],
        margin: float,
        draft: bool,
    ) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = []
        for item in listings:
            try:
                # 1) Upload image (prefer URL if provided; else local file path)
                image_id: str | None = None
                image_url = item.get("image_url")
                if image_url:
                    image_id = self.publisher.upload_design_url(image_url, file_name=Path(item.get("image_path", "design.png")).name)
                elif "image_path" in item and item["image_path"]:
                    image_id = self.publisher.upload_design(Path(item["image_path"]))
                else:
                    # Skip if no image source provided
                    print(f"Warning: No image_url or image_path provided for item: {item.get('title', 'unknown')}")
                    continue
                time.sleep(2)
                # 2) Create product
                price_cents = int(round(2499 * (1 + margin)))
                if price_cents % 100 < 99:
                    price_cents = price_cents - (price_cents % 100) + 99
                blueprint_id = item.get("blueprint_id")
                provider_id = item.get("print_provider_id")
                # If not provided, try env, else auto-select
                if not blueprint_id:
                    try:
                        blueprint_id = int(os.getenv("BLUEPRINT_ID", "") or 0) or None
                    except Exception:
                        blueprint_id = None
                if not provider_id:
                    try:
                        provider_id = int(os.getenv("PRINT_PROVIDER_ID", "") or 0) or None
                    except Exception:
                        provider_id = None

                if blueprint_id and provider_id:
                    product = self.publisher.create_product_with_fallback(
                        title=item["title"],
                        description=item["description"],
                        blueprint_id=int(blueprint_id),
                        print_provider_id=int(provider_id),
                        print_area_file_id=image_id,
                        variant_price_cents=price_cents,
                        colors=item.get("colors"),
                        sizes=item.get("sizes"),
                    )
                else:
                    product = self.publisher.create_product_auto(
                        title=item["title"],
                        description=item["description"],
                        print_area_file_id=image_id,
                        variant_price_cents=price_cents,
                        colors=item.get("colors"),
                        sizes=item.get("sizes"),
                    )
                product_id = product.get("id") or product.get("product_id")
                if not product_id:
                    raise RuntimeError(f"No product id returned: {product}")
                time.sleep(2)
                # 3) Publish to Etsy via Printify
                publish = self.publisher.publish_product(product_id=str(product_id), publish_to_store=True, publish_as_draft=draft)
                results.append({
                    "design_id": Path(item["image_path"]).name,
                    "product_title": item["title"],
                    "printify_product_id": str(product_id),
                    "image_upload_id": image_id,
                    "status": "published" if publish else "pending",
                    "sales_channels": ["etsy"],
                    "final_price": price_cents / 100.0,
                    "profit_margin": margin,
                    "publication_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "error_details": None,
                })
            except Exception as e:
                # Unwrap tenacity RetryError to expose inner HTTP error details when present
                error_message = str(e)
                try:
                    from tenacity import RetryError
                    if isinstance(e, RetryError) and getattr(e, 'last_attempt', None):
                        inner = e.last_attempt.exception()
                        if inner:
                            error_message = str(inner)
                except Exception:
                    pass
                results.append({
                    "design_id": Path(item["image_path"]).name,
                    "product_title": item["title"],
                    "printify_product_id": None,
                    "image_upload_id": None,
                    "status": "failed",
                    "sales_channels": ["etsy"],
                    "final_price": 0,
                    "profit_margin": margin,
                    "publication_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "error_details": error_message,
                })
                continue
        return {
            "publication_results": results,
            "batch_summary": {
                "total_processed": len(results),
                "successful_publications": sum(1 for r in results if r["status"] == "published"),
                "failed_publications": sum(1 for r in results if r["status"] == "failed"),
            },
        }

    async def publish_batch(self, products_to_publish: List[Dict[str, Any]], *, draft: bool = True, margin: float = 0.5) -> List[Dict[str, Any]]:
        """Publish a batch of products to Printify.

        Args:
            products_to_publish: Prepared product payloads.
            draft: Whether to publish as draft listings.
            margin: Profit margin fraction used to set variant prices.
        """
        try:
            # Convert to the format expected by run_batch
            listings = []
            for product_data in products_to_publish:
                design = product_data.get("design", {})
                product = product_data.get("product", {})
                marketing = product_data.get("marketing", {})
                # Support flat payloads
                if not design and ("images" in product_data or "image_url" in product_data):
                    first_url = None
                    images = product_data.get("images")
                    if isinstance(images, list) and images:
                        first_url = images[0]
                    design = {
                        "image_url": product_data.get("image_url") or first_url,
                        "image_path": product_data.get("image_path", ""),
                        "title": product_data.get("title"),
                        "description": product_data.get("description"),
                    }
                    product = {
                        "blueprint_id": product_data.get("blueprint_id"),
                        "print_provider_id": product_data.get("print_provider_id"),
                        "colors": product_data.get("colors"),
                        "sizes": product_data.get("sizes"),
                    }
                    marketing = {"product_description": product_data.get("description", "")}
                
                # Create listing format
                listing = {
                    # Prefer URL for stateless Cloud Run operation
                    "image_url": design.get("image_url") or design.get("gcs_url"),
                    "image_path": design.get("image_path", ""),
                    "title": design.get("title", product.get("name", "Unknown Product")),
                    "description": marketing.get("product_description", design.get("description", "")),
                    "blueprint_id": product.get("blueprint_id") or os.getenv("BLUEPRINT_ID"),
                    "print_provider_id": product.get("print_provider_id") or os.getenv("PRINT_PROVIDER_ID"),
                    "colors": product.get("colors") or [c.strip() for c in os.getenv("DEFAULT_COLORS", "White,Black,Navy").split(",") if c.strip()],
                    "sizes": product.get("sizes") or [s.strip() for s in os.getenv("DEFAULT_SIZES", "S,M,L,XL").split(",") if s.strip()],
                    "marketing_copy": marketing
                }
                listings.append(listing)
            
            # Use existing run_batch method
            result = self.run_batch(listings, margin=margin, draft=draft)
            
            return result.get("publication_results", [])
            
        except Exception as e:
            # Unwrap tenacity RetryError to expose inner HTTP error details when present
            error_message = str(e)
            try:
                from tenacity import RetryError
                if isinstance(e, RetryError) and getattr(e, 'last_attempt', None):
                    inner = e.last_attempt.exception()
                    if inner:
                        error_message = str(inner)
            except Exception:
                pass
            print(f"Error in batch publishing: {error_message}")
            return []

    async def publish_product(self, product_data: Dict[str, Any], *, draft: bool = True, margin: float = 0.5) -> Dict[str, Any]:
        """Publish a single product to Printify"""
        try:
            design = product_data.get("design", {})
            product = product_data.get("product", {})
            marketing = product_data.get("marketing", {})
            # Support flat payloads
            if not design and ("images" in product_data or "image_url" in product_data):
                first_url = None
                images = product_data.get("images")
                if isinstance(images, list) and images:
                    first_url = images[0]
                design = {
                    "image_url": product_data.get("image_url") or first_url,
                    "image_path": product_data.get("image_path", ""),
                    "title": product_data.get("title"),
                    "description": product_data.get("description"),
                }
                product = {
                    "blueprint_id": product_data.get("blueprint_id"),
                    "print_provider_id": product_data.get("print_provider_id"),
                    "colors": product_data.get("colors"),
                    "sizes": product_data.get("sizes"),
                }
                marketing = {"product_description": product_data.get("description", "")}
            
            # Create listing format
            listing = {
                "image_url": design.get("image_url") or design.get("gcs_url"),
                "image_path": design.get("image_path", ""),
                "title": design.get("title", product.get("name", "Unknown Product")),
                "description": marketing.get("product_description", design.get("description", "")),
                "blueprint_id": product.get("blueprint_id") or os.getenv("BLUEPRINT_ID"),
                "print_provider_id": product.get("print_provider_id") or os.getenv("PRINT_PROVIDER_ID"),
                "colors": product.get("colors") or [c.strip() for c in os.getenv("DEFAULT_COLORS", "White,Black,Navy").split(",") if c.strip()],
                "sizes": product.get("sizes") or [s.strip() for s in os.getenv("DEFAULT_SIZES", "S,M,L,XL").split(",") if s.strip()],
                "marketing_copy": marketing
            }
            
            # Use existing run_batch method with single item
            result = self.run_batch([listing], margin=margin, draft=draft)
            
            if result.get("publication_results"):
                return result["publication_results"][0]
            else:
                return {
                    "design_id": design.get("id", "unknown"),
                    "product_title": listing["title"],
                    "printify_product_id": None,
                    "image_upload_id": None,
                    "status": "failed",
                    "sales_channels": ["etsy"],
                    "final_price": 0,
                    "profit_margin": 0.5,
                    "publication_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "error_details": "No result returned from batch processing"
                }
                
        except Exception as e:
            # Unwrap tenacity RetryError to expose inner HTTP error details when present
            error_message = str(e)
            try:
                from tenacity import RetryError
                if isinstance(e, RetryError) and getattr(e, 'last_attempt', None):
                    inner = e.last_attempt.exception()
                    if inner:
                        error_message = str(inner)
            except Exception:
                pass
            print(f"Error publishing single product: {error_message}")
            return {
                "design_id": product_data.get("design", {}).get("id", "unknown"),
                "product_title": "Unknown Product",
                "printify_product_id": None,
                "image_upload_id": None,
                "status": "failed",
                "sales_channels": ["etsy"],
                "final_price": 0,
                "profit_margin": 0.5,
                "publication_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "error_details": error_message
            }
