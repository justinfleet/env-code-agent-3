"""MCP server for Petstore API."""

import asyncio
import os
from typing import Any, Dict, List, Optional
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent
import httpx

# Initialize the MCP server
app = Server("petstore-mcp")

# Configuration
APP_ENV = os.getenv("APP_ENV", "local")
if APP_ENV == "local":
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:3002")
else:
    API_BASE_URL = os.getenv("API_BASE_URL", "https://api.example.com")

# HTTP client
client = httpx.AsyncClient(timeout=30.0)

@app.list_resources()
async def list_resources() -> List[Resource]:
    """List available resources."""
    return [
        Resource(
            uri="petstore://pets",
            name="Pets",
            description="Pet inventory and management",
            mimeType="application/json"
        ),
        Resource(
            uri="petstore://orders",
            name="Orders", 
            description="Pet orders and purchases",
            mimeType="application/json"
        ),
        Resource(
            uri="petstore://users",
            name="Users",
            description="User accounts and profiles",
            mimeType="application/json"
        ),
        Resource(
            uri="petstore://inventory",
            name="Store Inventory",
            description="Pet store inventory by status",
            mimeType="application/json"
        )
    ]

@app.read_resource()
async def read_resource(uri: str) -> str:
    """Read a specific resource."""
    try:
        if uri == "petstore://pets":
            response = await client.get(f"{API_BASE_URL}/api/v3/pet/findByStatus?status=available")
            response.raise_for_status()
            return response.text
            
        elif uri == "petstore://inventory":
            response = await client.get(f"{API_BASE_URL}/api/v3/store/inventory")
            response.raise_for_status()
            return response.text
            
        else:
            return f"Resource not found: {uri}"
            
    except Exception as e:
        return f"Error reading resource {uri}: {str(e)}"

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_pet_by_id",
            description="Get a specific pet by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "pet_id": {
                        "type": "integer",
                        "description": "The ID of the pet to retrieve"
                    }
                },
                "required": ["pet_id"]
            }
        ),
        Tool(
            name="find_pets_by_status",
            description="Find pets by status (available, pending, sold)",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": ["available", "pending", "sold"],
                        "description": "Pet status to filter by"
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (required)"
                    }
                },
                "required": ["status", "auth_token"]
            }
        ),
        Tool(
            name="find_pets_by_tags",
            description="Find pets by tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "string",
                        "description": "Comma-separated list of tags"
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (required)"
                    }
                },
                "required": ["tags", "auth_token"]
            }
        ),
        Tool(
            name="get_store_inventory",
            description="Get pet store inventory counts by status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_order_by_id",
            description="Get order details by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "integer",
                        "description": "The order ID"
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (required)"
                    }
                },
                "required": ["order_id", "auth_token"]
            }
        ),
        Tool(
            name="place_order",
            description="Place an order for a pet",
            inputSchema={
                "type": "object",
                "properties": {
                    "pet_id": {
                        "type": "integer",
                        "description": "ID of pet to order"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Quantity (must be 1 for live animals)"
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (required)"
                    }
                },
                "required": ["pet_id", "auth_token"]
            }
        ),
        Tool(
            name="get_user",
            description="Get user information by username",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "Username to lookup"
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (required)"
                    }
                },
                "required": ["username", "auth_token"]
            }
        ),
        Tool(
            name="login",
            description="Login to get authentication token",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "Username"
                    },
                    "password": {
                        "type": "string",
                        "description": "Password"
                    }
                },
                "required": ["username", "password"]
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "get_pet_by_id":
            pet_id = arguments["pet_id"]
            response = await client.get(f"{API_BASE_URL}/api/v3/pet/{pet_id}")
            
            if response.status_code == 404:
                return [TextContent(type="text", text="Pet not found")]
            elif response.status_code == 200:
                return [TextContent(type="text", text=response.text)]
            else:
                return [TextContent(type="text", text=f"Error: {response.status_code} - {response.text}")]
                
        elif name == "find_pets_by_status":
            status = arguments["status"]
            auth_token = arguments["auth_token"]
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            response = await client.get(
                f"{API_BASE_URL}/api/v3/pet/findByStatus?status={status}",
                headers=headers
            )
            
            if response.status_code == 200:
                return [TextContent(type="text", text=response.text)]
            else:
                return [TextContent(type="text", text=f"Error: {response.status_code} - {response.text}")]
                
        elif name == "find_pets_by_tags":
            tags = arguments["tags"]
            auth_token = arguments["auth_token"]
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            response = await client.get(
                f"{API_BASE_URL}/api/v3/pet/findByTags?tags={tags}",
                headers=headers
            )
            
            if response.status_code == 200:
                return [TextContent(type="text", text=response.text)]
            else:
                return [TextContent(type="text", text=f"Error: {response.status_code} - {response.text}")]
                
        elif name == "get_store_inventory":
            response = await client.get(f"{API_BASE_URL}/api/v3/store/inventory")
            
            if response.status_code == 200:
                return [TextContent(type="text", text=response.text)]
            else:
                return [TextContent(type="text", text=f"Error: {response.status_code} - {response.text}")]
                
        elif name == "get_order_by_id":
            order_id = arguments["order_id"]
            auth_token = arguments["auth_token"]
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            response = await client.get(
                f"{API_BASE_URL}/api/v3/store/order/{order_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                return [TextContent(type="text", text=response.text)]
            elif response.status_code == 404:
                return [TextContent(type="text", text="Order not found")]
            else:
                return [TextContent(type="text", text=f"Error: {response.status_code} - {response.text}")]
                
        elif name == "place_order":
            pet_id = arguments["pet_id"]
            quantity = arguments.get("quantity", 1)
            auth_token = arguments["auth_token"]
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            order_data = {
                "petId": pet_id,
                "quantity": quantity
            }
            
            response = await client.post(
                f"{API_BASE_URL}/api/v3/store/order",
                headers=headers,
                json=order_data
            )
            
            if response.status_code == 201:
                return [TextContent(type="text", text=f"Order created successfully: {response.text}")]
            else:
                return [TextContent(type="text", text=f"Error: {response.status_code} - {response.text}")]
                
        elif name == "get_user":
            username = arguments["username"]
            auth_token = arguments["auth_token"]
            headers = {"Authorization": f"Bearer {auth_token}"}
            
            response = await client.get(
                f"{API_BASE_URL}/api/v3/user/{username}",
                headers=headers
            )
            
            if response.status_code == 200:
                return [TextContent(type="text", text=response.text)]
            elif response.status_code == 404:
                return [TextContent(type="text", text="User not found")]
            else:
                return [TextContent(type="text", text=f"Error: {response.status_code} - {response.text}")]
                
        elif name == "login":
            username = arguments["username"]
            password = arguments["password"]
            
            response = await client.get(
                f"{API_BASE_URL}/api/v3/user/login?username={username}&password={password}"
            )
            
            if response.status_code == 200:
                return [TextContent(type="text", text=response.text)]
            else:
                return [TextContent(type="text", text=f"Login failed: {response.status_code} - {response.text}")]
                
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
            
    except Exception as e:
        return [TextContent(type="text", text=f"Error calling {name}: {str(e)}")]

async def main():
    """Main entry point for the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())