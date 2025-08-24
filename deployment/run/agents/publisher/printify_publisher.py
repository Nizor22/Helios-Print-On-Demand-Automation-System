from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

# Configure logging
logger = logging.getLogger(__name__)

@dataclass
class VariantConfig:
    variant_id: int
    price_cents: int
    is_enabled: bool = True

@dataclass
class BlueprintProviderInfo:
    blueprint_id: int
    provider_id: int
    blueprint_title: str
    provider_title: str
    variant_count: int
    available_colors: List[str]
    available_sizes: List[str]
    sample_variants: List[Dict[str, Any]]

class PrintifyPublisher:
    BASE_URL = "https://api.printify.com/v1"

    def __init__(self, api_token: str, shop_id: str) -> None:
        self.api_token = api_token
        self.shop_id = shop_id
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "helios-pod-system"
        }
        self._blueprint_cache: Dict[Tuple[int, int], BlueprintProviderInfo] = {}
        self._variants_cache: Dict[Tuple[int, int], List[Dict]] = {}  # Cache for variants

    @retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        response = requests.post(url, headers=self.headers, data=json.dumps(payload), timeout=60)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            # Surface detailed error context to callers (status + body snippet)
            body = None
            try:
                body = response.text
            except Exception:
                body = "<no-body>"
            message = f"POST {url} failed with {response.status_code}: {body[:500]}"  # truncate long bodies
            raise requests.HTTPError(message, response=response) from e
        return response.json()

    @retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        response = requests.get(url, headers=self.headers, params=params, timeout=60)
        try:
            response.raise_for_status()
        except requests.HTTPError as e:
            # Surface detailed error context to callers (status + body snippet)
            body = None
            try:
                body = response.text
            except Exception:
                body = "<no-body>"
            message = f"GET {url} failed with {response.status_code}: {body[:500]}"  # truncate long bodies
            raise requests.HTTPError(message, response=response) from e
        return response.json()

    @retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def _upload(self, file_path: Path) -> Dict[str, Any]:
        """Upload image to Printify using JSON base64 payload (v1 API)."""
        url = f"{self.BASE_URL}/uploads/images.json"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        
        # Clean the filename to avoid special characters that cause API errors
        clean_filename = self._clean_filename(file_path.name)
        
        with open(file_path, "rb") as f:
            import base64
            b64 = base64.b64encode(f.read()).decode("utf-8")
            payload = {
                "file_name": clean_filename,  # Use cleaned filename
                "contents": b64,
            }
            response = requests.post(url, headers=headers, json=payload, timeout=120)  # Use json= instead of data=
            try:
                response.raise_for_status()
            except requests.HTTPError as e:
                body = None
                try:
                    body = response.text
                except Exception:
                    body = "<no-body>"
                message = f"POST {url} failed with {response.status_code}: {body[:500]}"
                raise requests.HTTPError(message, response=response) from e
            return response.json()
    
    def _clean_filename(self, filename: str) -> str:
        """Clean filename to remove special characters that cause Printify API issues"""
        import re
        # Remove or replace problematic characters
        clean_name = re.sub(r'[?:*<>|"\\]', '_', filename)  # Replace with underscore
        clean_name = re.sub(r'[^\w\-_.]', '_', clean_name)  # Keep only alphanumeric, dash, underscore, dot
        clean_name = re.sub(r'_+', '_', clean_name)  # Replace multiple underscores with single
        clean_name = clean_name.strip('_')  # Remove leading/trailing underscores
        
        # Ensure it has .png extension
        if not clean_name.lower().endswith('.png'):
            clean_name = f"{clean_name}.png"
            
        return clean_name

    def get_blueprint_variants(self, blueprint_id: int, provider_id: int) -> List[Dict[str, Any]]:
        """Get variants for a blueprint/provider combination (IncomeStreamSurfer's approach)"""
        cache_key = (blueprint_id, provider_id)
        
        # Check cache first
        if cache_key in self._variants_cache:
            return self._variants_cache[cache_key]
        
        # Fetch variants from API
        path = f"/catalog/blueprints/{blueprint_id}/print_providers/{provider_id}/variants.json"
        try:
            response = self._get(path)
            variants = response.get('variants', [])
            
            # Cache the results
            self._variants_cache[cache_key] = variants
            logger.info(f"✅ Found {len(variants)} variants for blueprint {blueprint_id} + provider {provider_id}")
            
            return variants
        except Exception as e:
            logger.error(f"❌ Failed to get variants for blueprint {blueprint_id} + provider {provider_id}: {e}")
            return []

    def upload_design(self, file_path: Path) -> str:
        payload = self._upload(file_path)
        upload_id = payload.get("id")
        if upload_id:
            logger.info(f"Successfully uploaded design: {file_path.name} -> {upload_id}")
        return upload_id

    @retry(wait=wait_exponential(min=1, max=10), stop=stop_after_attempt(3))
    def upload_design_url(self, image_url: str, file_name: Optional[str] = None) -> str:
        """Upload image to Printify by URL (mirrors reference repo bash flow).

        Args:
            image_url: Publicly accessible image URL.
            file_name: Optional file name for Printify. Defaults to last path segment.
        Returns:
            Upload ID string.
        """
        url = f"{self.BASE_URL}/uploads/images.json"
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
            "User-Agent": "helios-pod-system"
        }
        payload = {
            "file_name": file_name or (image_url.rsplit("/", 1)[-1] or "design.png"),
            "url": image_url,
        }
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=120)
        response.raise_for_status()
        data = response.json()
        upload_id = data.get("id")
        if upload_id:
            logger.info(f"Successfully uploaded design via URL -> {upload_id}")
        return upload_id

    def discover_blueprint_providers(self, limit: int = 50) -> List[BlueprintProviderInfo]:
        """Discover available blueprint/provider combinations with variant information"""
        try:
            blueprints = self._get("/catalog/blueprints.json")
            
            # Prioritize common product types
            priority_keywords = ["bella", "3001", "tee", "t-shirt", "shirt", "gildan", "cotton"]
            
            # Sort blueprints by priority
            sorted_blueprints = []
            for bp in blueprints:
                title = bp.get('title', '').lower()
                priority_score = sum(1 for keyword in priority_keywords if keyword in title)
                sorted_blueprints.append((priority_score, bp))
            
            sorted_blueprints.sort(key=lambda x: x[0], reverse=True)
            
            discovered = []
            for _, blueprint in sorted_blueprints[:limit]:
                blueprint_id = blueprint.get('id')
                if not blueprint_id:
                    continue
                    
                try:
                    providers = self._get(f"/catalog/blueprints/{blueprint_id}/print_providers.json")
                    
                    for provider in providers[:5]:  # Limit providers per blueprint
                        provider_id = provider.get('id')
                        if not provider_id:
                            continue
                            
                        # Get detailed provider info with variants
                        info = self.get_blueprint_provider_info(blueprint_id, provider_id)
                        if info and info.variant_count > 0:
                            discovered.append(info)
                            
                except Exception as e:
                    logger.warning(f"Failed to get providers for blueprint {blueprint_id}: {e}")
                    continue
                    
                if len(discovered) >= limit:
                    break
                    
            logger.info(f"Discovered {len(discovered)} viable blueprint/provider combinations")
            return discovered
            
        except Exception as e:
            logger.error(f"Failed to discover blueprint providers: {e}")
            return []

    def get_blueprint_provider_info(self, blueprint_id: int, provider_id: int) -> Optional[BlueprintProviderInfo]:
        """Get detailed information about a blueprint/provider combination"""
        cache_key = (blueprint_id, provider_id)
        
        # Check cache first
        if cache_key in self._blueprint_cache:
            return self._blueprint_cache[cache_key]
            
        try:
            data = self._get(f"/catalog/blueprints/{blueprint_id}/print_providers/{provider_id}.json")
            
            # Extract options
            color_option = next((opt for opt in data.get('options', []) if opt.get('type') == 'color'), None)
            size_option = next((opt for opt in data.get('options', []) if opt.get('type') == 'size'), None)
            
            # Analyze variants
            variants = data.get('variants', [])
            available_colors = set()
            available_sizes = set()
            sample_variants = []
            
            for variant in variants:
                if not variant.get('available', True):
                    continue
                    
                options = variant.get('options', {})
                
                if color_option:
                    color = options.get(str(color_option['id']))
                    if color:
                        available_colors.add(color)
                        
                if size_option:
                    size = options.get(str(size_option['id']))
                    if size:
                        available_sizes.add(size)
                
                # Keep some sample variants
                if len(sample_variants) < 5:
                    sample_variants.append({
                        'id': variant['id'],
                        'color': options.get(str(color_option['id'])) if color_option else None,
                        'size': options.get(str(size_option['id'])) if size_option else None,
                        'available': variant.get('available', True)
                    })
            
            info = BlueprintProviderInfo(
                blueprint_id=blueprint_id,
                provider_id=provider_id,
                blueprint_title=data.get('title', ''),
                provider_title=data.get('provider', {}).get('title', ''),
                variant_count=len([v for v in variants if v.get('available', True)]),
                available_colors=sorted(list(available_colors)),
                available_sizes=sorted(list(available_sizes)),
                sample_variants=sample_variants
            )
            
            # Cache the result
            self._blueprint_cache[cache_key] = info
            return info
            
        except Exception as e:
            logger.error(f"Failed to get blueprint/provider info for {blueprint_id}/{provider_id}: {e}")
            return None

    def find_best_blueprint_provider(self, preferred_colors: Optional[List[str]] = None, 
                                   preferred_sizes: Optional[List[str]] = None) -> Optional[BlueprintProviderInfo]:
        """Find the best blueprint/provider combination based on preferences"""
        discovered = self.discover_blueprint_providers(limit=30)
        
        if not discovered:
            return None
            
        # Score each option
        scored_options = []
        for info in discovered:
            score = 0
            
            # Base score for variant count
            score += min(info.variant_count, 20)  # Cap at 20
            
            # Bonus for having preferred colors
            if preferred_colors:
                matching_colors = set(preferred_colors) & set(info.available_colors)
                score += len(matching_colors) * 5
                
            # Bonus for having preferred sizes
            if preferred_sizes:
                matching_sizes = set(preferred_sizes) & set(info.available_sizes)
                score += len(matching_sizes) * 3
                
            # Bonus for common product types
            title_lower = info.blueprint_title.lower()
            if any(keyword in title_lower for keyword in ["bella", "3001", "tee", "t-shirt"]):
                score += 10
                
            scored_options.append((score, info))
        
        # Return the highest scoring option
        scored_options.sort(key=lambda x: x[0], reverse=True)
        best_info = scored_options[0][1]
        
        logger.info(f"Selected blueprint/provider: {best_info.blueprint_title} / {best_info.provider_title} "
                   f"(variants: {best_info.variant_count}, colors: {len(best_info.available_colors)}, "
                   f"sizes: {len(best_info.available_sizes)})")
        
        return best_info

    def estimate_price(self, catalog_variant_cost_cents: Optional[int], margin: float, fallback_cents: int = 2499) -> int:
        if catalog_variant_cost_cents is None:
            return int(fallback_cents)
        # price = cost * (1 + margin)
        price = int(round(catalog_variant_cost_cents * (1 + margin)))
        # Ensure ends with .99
        if price % 100 < 99:
            price = price - (price % 100) + 99
        return price

    def create_product_auto(
        self,
        title: str,
        description: str,
        print_area_file_id: str,
        variant_price_cents: int,
        colors: Optional[List[str]] = None,
        sizes: Optional[List[str]] = None,
        blueprint_id: Optional[int] = None,
        print_provider_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create product with automatic blueprint/provider discovery if not specified"""
        
        # If blueprint/provider not specified, find the best one
        if not blueprint_id or not print_provider_id:
            logger.info("Auto-discovering blueprint/provider combination...")
            # Prefer env-provided provider name if available
            import os
            preferred_name = os.getenv("PREFERRED_PROVIDER_NAME")
            if preferred_name:
                # scan providers for the preferred name
                discovered = self.discover_blueprint_providers(limit=50)
                chosen = None
                for info in discovered:
                    if info.provider_title.strip().lower() == preferred_name.strip().lower():
                        chosen = info
                        break
                best_info = chosen or self.find_best_blueprint_provider(
                    preferred_colors=colors or ["Black", "White", "Navy", "Athletic Heather"],
                    preferred_sizes=sizes or ["S", "M", "L", "XL"]
                )
            else:
                best_info = self.find_best_blueprint_provider(
                    preferred_colors=colors or ["Black", "White", "Navy", "Athletic Heather"],
                    preferred_sizes=sizes or ["S", "M", "L", "XL"]
                )
            
            if not best_info:
                raise RuntimeError("Failed to find suitable blueprint/provider combination")
                
            blueprint_id = best_info.blueprint_id
            print_provider_id = best_info.provider_id
            
            logger.info(f"Using blueprint {blueprint_id} / provider {print_provider_id}: "
                       f"{best_info.blueprint_title} / {best_info.provider_title}")
        
        # Use the enhanced create_product method
        return self.create_product(
            title=title,
            description=description,
            blueprint_id=blueprint_id,
            print_provider_id=print_provider_id,
            print_area_file_id=print_area_file_id,
            variant_price_cents=variant_price_cents,
            colors=colors,
            sizes=sizes
        )

    def create_product(
        self,
        title: str,
        description: str,
        blueprint_id: int,
        print_provider_id: int,
        print_area_file_id: str,
        variant_price_cents: int,
        colors: Optional[List[str]] = None,
        sizes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        # Minimal product body for front print
        payload: Dict[str, Any] = {
            "title": title,
            "description": description,
            "blueprint_id": blueprint_id,
            "print_provider_id": print_provider_id,
            "variants": [],
            "print_areas": [
                {
                    "variant_ids": [],
                    "placeholders": [
                        {
                            "position": "front",
                            "images": [
                                {
                                    "id": print_area_file_id,
                                    "x": 0.5,
                                    "y": 0.35,
                                    "scale": 1.0,
                                    "angle": 0,
                                }
                            ],
                        }
                    ],
                }
            ],
            "options": [],
        }

        # Fetch blueprint/provider variants to map colors/sizes to IDs
        # If this fails, we will let Printify auto-enable defaults
        try:
            catalog = self._get(f"/catalog/blueprints/{blueprint_id}/print_providers/{print_provider_id}.json")
            variant_map: Dict[int, Dict[str, Any]] = {v["id"]: v for v in catalog.get("variants", [])}
            color_opt = next((o for o in catalog.get("options", []) if o.get("type") == "color"), None)
            size_opt = next((o for o in catalog.get("options", []) if o.get("type") == "size"), None)

            wanted_colors = set((colors or []) or [])
            wanted_sizes = set((sizes or []) or [])

            enabled_variant_ids: List[int] = []
            for v in catalog.get("variants", []):
                color_name = v.get("options", {}).get(str(color_opt["id"])) if color_opt else None
                size_name = v.get("options", {}).get(str(size_opt["id"])) if size_opt else None
                if (not wanted_colors or color_name in wanted_colors) and (not wanted_sizes or size_name in wanted_sizes):
                    enabled_variant_ids.append(v["id"])

            # Variants
            for vid in enabled_variant_ids[:]:
                payload["variants"].append({
                    "id": vid,
                    "price": variant_price_cents,
                    "is_enabled": True,
                })

            # Print areas should target enabled variants
            if enabled_variant_ids:
                payload["print_areas"][0]["variant_ids"] = enabled_variant_ids

            # Options for storefront filters
            if color_opt and colors:
                payload["options"].append({"name": color_opt["name"], "type": "color", "values": list(wanted_colors)})
            if size_opt and sizes:
                payload["options"].append({"name": size_opt["name"], "type": "size", "values": list(wanted_sizes)})
        except Exception:
            # Proceed without catalog enrichment
            pass

        # Strict mode: if no variants resolved, surface the error for debugging
        if (not payload["variants"]) or (not payload["print_areas"][0].get("variant_ids")):
            raise RuntimeError("No resolved variants for selected blueprint/provider. Verify BLUEPRINT_ID/PRINT_PROVIDER_ID and available variants.")

        product = self._post(f"/shops/{self.shop_id}/products.json", payload)
        return product

    def _get_first_available_variant_id(self, blueprint_id: int, print_provider_id: int) -> Optional[int]:
        """Fetch the first available variant id using the working IncomeStreamSurfer approach."""
        try:
            # Use our new working method
            variants = self.get_blueprint_variants(blueprint_id, print_provider_id)
            if not variants:
                logger.warning(f"No variants found for blueprint {blueprint_id} + provider {print_provider_id}")
                return None
            
            # Use first variant (IncomeStreamSurfer's approach)
            first_variant = variants[0]
            variant_id = first_variant.get("id")
            
            if variant_id:
                logger.info(f"✅ Selected variant {variant_id}: {first_variant.get('title', 'Unknown')}")
            
            return variant_id
        except Exception as e:
            logger.error(f"❌ Failed to get variant ID for blueprint {blueprint_id} + provider {print_provider_id}: {e}")
            return None

    def create_product_minimal(
        self,
        title: str,
        description: str,
        blueprint_id: int,
        print_provider_id: int,
        print_area_file_id: str,
        variant_price_cents: int,
    ) -> Dict[str, Any]:
        """Minimal product creation mirroring the reference repo's bash flow.

        - Picks the first available variant via /variants.json
        - Creates product with a single variant and a single print area
        """
        variant_id = self._get_first_available_variant_id(blueprint_id, print_provider_id)
        if not variant_id:
            raise RuntimeError(f"No variants returned for blueprint/provider {blueprint_id}/{print_provider_id}")

        payload: Dict[str, Any] = {
            "title": title,
            "description": description,
            "blueprint_id": int(blueprint_id),
            "print_provider_id": int(print_provider_id),
            "variants": [
                {"id": int(variant_id), "price": int(variant_price_cents), "is_enabled": True}
            ],
            "print_areas": [
                {
                    "variant_ids": [int(variant_id)],
                    "placeholders": [
                        {
                            "position": "front",
                            "images": [
                                {"id": print_area_file_id, "x": 0.5, "y": 0.5, "scale": 1.0, "angle": 0}
                            ],
                        }
                    ],
                }
            ],
        }
        return self._post(f"/shops/{self.shop_id}/products.json", payload)

    def create_product_with_fallback(
        self,
        title: str,
        description: str,
        print_area_file_id: str,
        variant_price_cents: int,
        blueprint_id: int,
        print_provider_id: int,
        colors: Optional[List[str]] = None,
        sizes: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Use the working minimal approach (IncomeStreamSurfer's method)."""
        # Skip the enhanced method and go directly to the working minimal approach
        logger.info(f"🛒 Using working minimal product creation approach")
        return self.create_product_minimal(
            title=title,
            description=description,
            blueprint_id=blueprint_id,
            print_provider_id=print_provider_id,
            print_area_file_id=print_area_file_id,
            variant_price_cents=variant_price_cents,
        )

    def publish_product(
        self,
        product_id: str,
        publish_to_store: bool = True,
        publish_as_draft: bool = True,
    ) -> Dict[str, Any]:
        # Publish to connected sales channel (e.g., Etsy) via Printify
        payload = {
            "title": True,
            "description": True,
            "images": True,
            "variants": True,
            "tags": True,
            "key_features": True,
            "shipping_template": True,
            "variants_prices": True,
            "send_to_store": publish_to_store,
            "publish": not publish_as_draft,
        }
        return self._post(f"/shops/{self.shop_id}/products/{product_id}/publish.json", payload)
