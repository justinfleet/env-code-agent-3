"""HTTP client for Petstore API."""

import httpx
import json
from typing import Optional, Dict, Any, List


class PetstoreClient:
    """Client for interacting with the Petstore API."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.client = httpx.AsyncClient()
    
    async def get_pet_by_id(self, pet_id: int) -> Dict[str, Any]:
        """Get a pet by ID."""
        try:
            response = await self.client.get(f"{self.base_url}/api/v3/pet/{pet_id}")
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def find_pets_by_status(self, status: str, auth_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find pets by status."""
        try:
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            response = await self.client.get(
                f"{self.base_url}/api/v3/pet/findByStatus",
                params={"status": status},
                headers=headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                return [{"error": f"HTTP {response.status_code}: {response.text}"}]
        except Exception as e:
            return [{"error": str(e)}]
    
    async def find_pets_by_tags(self, tags: str, auth_token: Optional[str] = None) -> List[Dict[str, Any]]:
        """Find pets by tags."""
        try:
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            response = await self.client.get(
                f"{self.base_url}/api/v3/pet/findByTags",
                params={"tags": tags},
                headers=headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                return [{"error": f"HTTP {response.status_code}: {response.text}"}]
        except Exception as e:
            return [{"error": str(e)}]
    
    async def get_store_inventory(self, auth_token: Optional[str] = None) -> Dict[str, Any]:
        """Get store inventory."""
        try:
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            response = await self.client.get(
                f"{self.base_url}/api/v3/store/inventory",
                headers=headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_order_by_id(self, order_id: int, auth_token: Optional[str] = None) -> Dict[str, Any]:
        """Get an order by ID."""
        try:
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            response = await self.client.get(
                f"{self.base_url}/api/v3/store/order/{order_id}",
                headers=headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def get_user_by_username(self, username: str, auth_token: Optional[str] = None) -> Dict[str, Any]:
        """Get a user by username."""
        try:
            headers = {}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"
            
            response = await self.client.get(
                f"{self.base_url}/api/v3/user/{username}",
                headers=headers
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """Login a user and get authentication token."""
        try:
            response = await self.client.get(
                f"{self.base_url}/api/v3/user/login",
                params={"username": username, "password": password}
            )
            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
        except Exception as e:
            return {"error": str(e)}
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()