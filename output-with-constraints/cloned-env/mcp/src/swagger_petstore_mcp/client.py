"""API client for Swagger Petstore"""

import os
import httpx
from typing import Any, Dict, List, Optional, Union

class PetstoreAPIClient:
    def __init__(self):
        self.app_env = os.getenv("APP_ENV", "local")
        
        if self.app_env == "local":
            self.base_url = os.getenv("API_BASE_URL", "http://localhost:3002")
        else:
            # Production URL would be set here
            self.base_url = os.getenv("API_BASE_URL", "https://api.petstore.example.com")
        
        self.api_base = f"{self.base_url}/api/v3"
        
    async def _request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request to the API"""
        url = f"{self.api_base}{endpoint}"
        
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, **kwargs)
            
            if response.status_code == 404:
                return {"error": "Not found", "status_code": 404}
            elif response.status_code >= 400:
                return {"error": f"HTTP {response.status_code}", "status_code": response.status_code}
            
            try:
                return response.json()
            except:
                return {"data": response.text}
    
    # Pet endpoints
    async def get_pet_by_id(self, pet_id: int) -> Dict[str, Any]:
        """Get pet by ID"""
        return await self._request("GET", f"/pet/{pet_id}")
    
    async def find_pets_by_status(self, status: Union[str, List[str]]) -> Dict[str, Any]:
        """Find pets by status"""
        if isinstance(status, list):
            status = ",".join(status)
        return await self._request("GET", f"/pet/findByStatus", params={"status": status})
    
    async def find_pets_by_tags(self, tags: Union[str, List[str]]) -> Dict[str, Any]:
        """Find pets by tags"""
        if isinstance(tags, list):
            tags = ",".join(tags)
        return await self._request("GET", f"/pet/findByTags", params={"tags": tags})
    
    async def add_pet(self, pet_data: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Add a new pet"""
        headers = {"Authorization": f"Bearer {token}"}
        return await self._request("POST", "/pet", json=pet_data, headers=headers)
    
    async def update_pet(self, pet_data: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Update existing pet"""
        headers = {"Authorization": f"Bearer {token}"}
        return await self._request("PUT", "/pet", json=pet_data, headers=headers)
    
    async def delete_pet(self, pet_id: int, token: str) -> Dict[str, Any]:
        """Delete pet"""
        headers = {"Authorization": f"Bearer {token}"}
        return await self._request("DELETE", f"/pet/{pet_id}", headers=headers)
    
    # Store endpoints
    async def get_inventory(self, token: str) -> Dict[str, Any]:
        """Get store inventory"""
        headers = {"Authorization": f"Bearer {token}"}
        return await self._request("GET", "/store/inventory", headers=headers)
    
    async def place_order(self, order_data: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Place an order"""
        headers = {"Authorization": f"Bearer {token}"}
        return await self._request("POST", "/store/order", json=order_data, headers=headers)
    
    async def get_order_by_id(self, order_id: int, token: str) -> Dict[str, Any]:
        """Get order by ID"""
        headers = {"Authorization": f"Bearer {token}"}
        return await self._request("GET", f"/store/order/{order_id}", headers=headers)
    
    async def delete_order(self, order_id: int, token: str) -> Dict[str, Any]:
        """Cancel order"""
        headers = {"Authorization": f"Bearer {token}"}
        return await self._request("DELETE", f"/store/order/{order_id}", headers=headers)
    
    # User endpoints
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create user"""
        return await self._request("POST", "/user", json=user_data)
    
    async def login_user(self, username: str, password: str) -> Dict[str, Any]:
        """Login user"""
        return await self._request("GET", "/user/login", params={"username": username, "password": password})
    
    async def logout_user(self, token: str) -> Dict[str, Any]:
        """Logout user"""
        headers = {"Authorization": f"Bearer {token}"}
        return await self._request("GET", "/user/logout", headers=headers)
    
    async def get_user_by_username(self, username: str, token: str) -> Dict[str, Any]:
        """Get user by username"""
        headers = {"Authorization": f"Bearer {token}"}
        return await self._request("GET", f"/user/{username}", headers=headers)
    
    async def update_user(self, username: str, user_data: Dict[str, Any], token: str) -> Dict[str, Any]:
        """Update user"""
        headers = {"Authorization": f"Bearer {token}"}
        return await self._request("PUT", f"/user/{username}", json=user_data, headers=headers)
    
    async def delete_user(self, username: str, token: str) -> Dict[str, Any]:
        """Delete user"""
        headers = {"Authorization": f"Bearer {token}"}
        return await self._request("DELETE", f"/user/{username}", headers=headers)
    
    # Health check
    async def health_check(self) -> Dict[str, Any]:
        """Check API health"""
        url = f"{self.base_url}/health"
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url)
                return response.json()
            except Exception as e:
                return {"error": str(e), "status": "unhealthy"}