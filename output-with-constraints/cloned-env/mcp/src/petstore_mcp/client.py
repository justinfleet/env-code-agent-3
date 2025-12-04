"""HTTP client for Petstore API."""

import os
from typing import Dict, Any, Optional
import httpx

class PetstoreClient:
    """Client for interacting with the Petstore API."""
    
    def __init__(self, base_url: Optional[str] = None):
        """Initialize the client."""
        if base_url:
            self.base_url = base_url
        else:
            app_env = os.getenv("APP_ENV", "local")
            if app_env == "local":
                self.base_url = os.getenv("API_BASE_URL", "http://localhost:3002")
            else:
                self.base_url = os.getenv("API_BASE_URL", "https://api.example.com")
                
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
        
    async def get_pet(self, pet_id: int) -> Dict[str, Any]:
        """Get pet by ID."""
        response = await self.client.get(f"{self.base_url}/api/v3/pet/{pet_id}")
        response.raise_for_status()
        return response.json()
        
    async def find_pets_by_status(self, status: str, auth_token: str) -> Dict[str, Any]:
        """Find pets by status."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v3/pet/findByStatus?status={status}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
        
    async def find_pets_by_tags(self, tags: str, auth_token: str) -> Dict[str, Any]:
        """Find pets by tags."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v3/pet/findByTags?tags={tags}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
        
    async def get_inventory(self) -> Dict[str, Any]:
        """Get store inventory."""
        response = await self.client.get(f"{self.base_url}/api/v3/store/inventory")
        response.raise_for_status()
        return response.json()
        
    async def place_order(self, pet_id: int, auth_token: str, quantity: int = 1) -> Dict[str, Any]:
        """Place an order."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        order_data = {"petId": pet_id, "quantity": quantity}
        
        response = await self.client.post(
            f"{self.base_url}/api/v3/store/order",
            headers=headers,
            json=order_data
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
        
    async def login(self, username: str, password: str) -> Dict[str, Any]:
        """Login user."""
        response = await self.client.get(
            f"{self.base_url}/api/v3/user/login?username={username}&password={password}"
        )
        response.raise_for_status()
        return response.json()
        
    async def get_user(self, username: str, auth_token: str) -> Dict[str, Any]:
        """Get user by username."""
        headers = {"Authorization": f"Bearer {auth_token}"}
        response = await self.client.get(
            f"{self.base_url}/api/v3/user/{username}",
            headers=headers
        )
        response.raise_for_status()
        return response.json()
        
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user."""
        response = await self.client.post(
            f"{self.base_url}/api/v3/user",
            json=user_data
        )
        response.raise_for_status()
        return response.json()