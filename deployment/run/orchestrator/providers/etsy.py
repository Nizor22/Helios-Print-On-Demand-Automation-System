from __future__ import annotations

import httpx
from typing import Any, Optional

BASE_URL = "https://openapi.etsy.com"

class EtsyClient:
    def __init__(self, api_key: str, oauth_token: Optional[str] = None):
        self.api_key = api_key
        self.oauth_token = oauth_token

    def _headers(self) -> dict[str, str]:
        headers = {"x-api-key": self.api_key}
        if self.oauth_token:
            headers["Authorization"] = f"Bearer {self.oauth_token}"
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        return headers

    async def get(self, path: str, params: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        url = f"{BASE_URL}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params or {}, headers=self._headers())
            resp.raise_for_status()
            return resp.json()

    async def get_me(self) -> dict[str, Any]:
        return await self.get("/v3/application/users/me")

    async def get_shops_by_user(self, user_id: int) -> dict[str, Any]:
        return await self.get(f"/v3/application/users/{user_id}/shops")

    async def get_buyer_taxonomy_nodes(self) -> dict[str, Any]:
        return await self.get("/v3/application/buyer-taxonomy/nodes")

    async def get_seller_taxonomy_nodes(self) -> dict[str, Any]:
        return await self.get("/v3/application/seller-taxonomy/nodes")

    async def get_shipping_profiles(self, shop_id: int) -> dict[str, Any]:
        return await self.get(f"/v3/application/shops/{shop_id}/shipping-profiles")

    async def get_return_policies(self, shop_id: int) -> dict[str, Any]:
        return await self.get(f"/v3/application/shops/{shop_id}/policies/return")

    async def create_draft_listing(
        self,
        shop_id: str,
        title: str,
        description: str,
        price: float,
        taxonomy_id: int,
        shipping_profile_id: Optional[int] = None,
        return_policy_id: Optional[int] = None,
        tags: Optional[list[str]] = None,
        who_made: str = "i_did",
        when_made: str = "made_to_order",
        is_supply: bool = False,
        quantity: int = 1,
    ) -> dict[str, Any]:
        url = f"{BASE_URL}/v3/application/shops/{shop_id}/listings"
        data: dict[str, Any] = {
            "quantity": quantity,
            "title": title,
            "description": description,
            "price": price,
            "who_made": who_made,
            "when_made": when_made,
            "taxonomy_id": taxonomy_id,
            "is_supply": is_supply,
            "type": "physical",
        }
        if shipping_profile_id:
            data["shipping_profile_id"] = shipping_profile_id
        if return_policy_id:
            data["return_policy_id"] = return_policy_id
        if tags:
            for i, t in enumerate(tags):
                data[f"tags[{i}]"] = t
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, data=data, headers=self._headers())
            resp.raise_for_status()
            return resp.json()
