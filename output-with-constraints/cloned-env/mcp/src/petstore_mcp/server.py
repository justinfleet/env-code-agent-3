"""MCP server for Swagger Petstore API."""

import asyncio
import os
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from .client import PetstoreClient

app = Server("petstore-mcp")

# Initialize the API client
api_base_url = os.getenv("API_BASE_URL", "http://localhost:3002")
client = PetstoreClient(api_base_url)

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools."""
    return [
        Tool(
            name="get_all_pets",
            description="Get all pets, optionally filtered by status",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Filter pets by status (available, pending, sold)",
                        "enum": ["available", "pending", "sold"]
                    }
                }
            }
        ),
        Tool(
            name="get_pet_by_id",
            description="Get a specific pet by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "pet_id": {
                        "type": "integer",
                        "description": "Pet ID to retrieve"
                    }
                },
                "required": ["pet_id"]
            }
        ),
        Tool(
            name="search_pets_by_tags",
            description="Find pets by tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "string",
                        "description": "Comma-separated list of tags to search for"
                    }
                },
                "required": ["tags"]
            }
        ),
        Tool(
            name="get_store_inventory",
            description="Get store inventory counts by pet status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="get_order_by_id",
            description="Get a specific order by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "integer",
                        "description": "Order ID to retrieve"
                    }
                },
                "required": ["order_id"]
            }
        ),
        Tool(
            name="get_user_by_username",
            description="Get a user by username",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "Username to look up"
                    }
                },
                "required": ["username"]
            }
        ),
        Tool(
            name="login_user",
            description="Login a user and get authentication token",
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
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "get_all_pets":
            status = arguments.get("status")
            if status:
                result = await client.find_pets_by_status(status)
            else:
                # Get all available pets by default
                result = await client.find_pets_by_status("available")
            return [TextContent(type="text", text=f"Pets: {result}")]
        
        elif name == "get_pet_by_id":
            pet_id = arguments["pet_id"]
            result = await client.get_pet_by_id(pet_id)
            return [TextContent(type="text", text=f"Pet details: {result}")]
        
        elif name == "search_pets_by_tags":
            tags = arguments["tags"]
            result = await client.find_pets_by_tags(tags)
            return [TextContent(type="text", text=f"Pets matching tags '{tags}': {result}")]
        
        elif name == "get_store_inventory":
            result = await client.get_store_inventory()
            return [TextContent(type="text", text=f"Store inventory: {result}")]
        
        elif name == "get_order_by_id":
            order_id = arguments["order_id"]
            result = await client.get_order_by_id(order_id)
            return [TextContent(type="text", text=f"Order details: {result}")]
        
        elif name == "get_user_by_username":
            username = arguments["username"]
            result = await client.get_user_by_username(username)
            return [TextContent(type="text", text=f"User details: {result}")]
        
        elif name == "login_user":
            username = arguments["username"]
            password = arguments["password"]
            result = await client.login_user(username, password)
            return [TextContent(type="text", text=f"Login result: {result}")]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        return [TextContent(type="text", text=f"Error calling {name}: {str(e)}")]

async def main():
    """Main function to run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())