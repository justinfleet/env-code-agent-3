"""
Petstore API Client

HTTP client for interacting with the Petstore API endpoints.
"""

import httpx
from typing import Any, Dict, List, Optional

class PetstoreClient:
    """HTTP client for the Petstore API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient()
    
    async def get_pets_by_status(self, status: str, auth_token: str) -> List[Dict[str, Any]]:
        """Find pets by status."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v3/pet/findByStatus",
            params={"status": status},
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_pets_by_tags(self, tags: List[str], auth_token: str) -> List[Dict[str, Any]]:
        """Find pets by tags."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v3/pet/findByTags",
            params={"tags": tags},
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_pet_by_id(self, pet_id: int) -> Dict[str, Any]:
        """Get pet by ID."""
        response = await self.client.get(f"{self.base_url}/api/v3/pet/{pet_id}")
        response.raise_for_status()
        return response.json()
    
    async def get_store_inventory(self, auth_token: str) -> Dict[str, int]:
        """Get store inventory."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v3/store/inventory",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def login_user(self, username: str, password: str) -> Dict[str, str]:
        """Login user."""
        response = await self.client.get(
            f"{self.base_url}/api/v3/user/login",
            params={"username": username, "password": password}
        )
        response.raise_for_status()
        return response.json()
    
    async def get_user_profile(self, username: str, auth_token: str) -> Dict[str, Any]:
        """Get user profile."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v3/user/{username}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def create_pet(self, name: str, auth_token: str, category: Optional[Dict] = None, 
                        photo_urls: Optional[List[str]] = None, tags: Optional[List[Dict]] = None,
                        status: str = "available") -> Dict[str, Any]:
        """Create a new pet."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        data = {
            "name": name,
            "status": status
        }
        if category:
            data["category"] = category
        if photo_urls:
            data["photoUrls"] = photo_urls
        if tags:
            data["tags"] = tags
            
        response = await self.client.post(
            f"{self.base_url}/api/v3/pet",
            json=data,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def place_order(self, pet_id: int, auth_token: str, quantity: int = 1, 
                         ship_date: Optional[str] = None) -> Dict[str, Any]:
        """Place an order for a pet."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        data = {
            "petId": pet_id,
            "quantity": quantity,
            "status": "placed"
        }
        if ship_date:
            data["shipDate"] = ship_date
            
        response = await self.client.post(
            f"{self.base_url}/api/v3/store/order",
            json=data,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def get_order(self, order_id: int, auth_token: str) -> Dict[str, Any]:
        """Get order by ID."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v3/store/order/{order_id}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()