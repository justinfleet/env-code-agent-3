"""MCP Server for Swagger Petstore API"""

import asyncio
import json
from typing import Any, Dict, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client import PetstoreAPIClient

app = Server("swagger-petstore-mcp")
client = PetstoreAPIClient()

@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available tools"""
    return [
        Tool(
            name="get_all_pets_by_status",
            description="Get all pets filtered by status (available, pending, sold)",
            inputSchema={
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "description": "Pet status to filter by",
                        "enum": ["available", "pending", "sold"]
                    }
                },
                "required": ["status"]
            }
        ),
        Tool(
            name="get_pet_by_id",
            description="Get detailed information about a specific pet by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "pet_id": {
                        "type": "integer",
                        "description": "ID of the pet to retrieve"
                    }
                },
                "required": ["pet_id"]
            }
        ),
        Tool(
            name="find_pets_by_tags",
            description="Find pets that have specific tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tags to search for"
                    }
                },
                "required": ["tags"]
            }
        ),
        Tool(
            name="get_store_inventory",
            description="Get current store inventory counts by pet status",
            inputSchema={
                "type": "object",
                "properties": {
                    "token": {
                        "type": "string",
                        "description": "Authentication token"
                    }
                },
                "required": ["token"]
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
                        "description": "ID of the pet to order"
                    },
                    "token": {
                        "type": "string",
                        "description": "Authentication token"
                    },
                    "ship_date": {
                        "type": "string",
                        "description": "Shipping date (optional)"
                    }
                },
                "required": ["pet_id", "token"]
            }
        ),
        Tool(
            name="get_order",
            description="Get order details by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "integer",
                        "description": "ID of the order"
                    },
                    "token": {
                        "type": "string",
                        "description": "Authentication token"
                    }
                },
                "required": ["order_id", "token"]
            }
        ),
        Tool(
            name="cancel_order",
            description="Cancel an order",
            inputSchema={
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "integer",
                        "description": "ID of the order to cancel"
                    },
                    "token": {
                        "type": "string",
                        "description": "Authentication token"
                    }
                },
                "required": ["order_id", "token"]
            }
        ),
        Tool(
            name="create_user",
            description="Create a new user account",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "Username for the account"
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for the account"
                    },
                    "email": {
                        "type": "string",
                        "description": "Email address"
                    },
                    "firstName": {
                        "type": "string",
                        "description": "First name"
                    },
                    "lastName": {
                        "type": "string",
                        "description": "Last name"
                    },
                    "phone": {
                        "type": "string",
                        "description": "Phone number"
                    }
                },
                "required": ["username", "password"]
            }
        ),
        Tool(
            name="login_user",
            description="Login and get authentication token",
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
        ),
        Tool(
            name="get_user_profile",
            description="Get user profile information",
            inputSchema={
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "Username to look up"
                    },
                    "token": {
                        "type": "string",
                        "description": "Authentication token"
                    }
                },
                "required": ["username", "token"]
            }
        ),
        Tool(
            name="add_pet",
            description="Add a new pet to the store (store_owner/admin only)",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the pet"
                    },
                    "category": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"}
                        },
                        "description": "Category of the pet"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["available", "pending", "sold"],
                        "description": "Pet status"
                    },
                    "photoUrls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Photo URLs"
                    },
                    "tags": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"}
                            }
                        },
                        "description": "Tags for the pet"
                    },
                    "token": {
                        "type": "string",
                        "description": "Authentication token"
                    }
                },
                "required": ["name", "token"]
            }
        ),
        Tool(
            name="health_check",
            description="Check if the API is healthy and accessible",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> List[TextContent]:
    """Handle tool calls"""
    
    try:
        if name == "get_all_pets_by_status":
            result = await client.find_pets_by_status(arguments["status"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_pet_by_id":
            result = await client.get_pet_by_id(arguments["pet_id"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "find_pets_by_tags":
            result = await client.find_pets_by_tags(arguments["tags"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_store_inventory":
            result = await client.get_inventory(arguments["token"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "place_order":
            order_data = {
                "petId": arguments["pet_id"],
                "quantity": 1,
                "status": "placed"
            }
            if "ship_date" in arguments:
                order_data["shipDate"] = arguments["ship_date"]
            
            result = await client.place_order(order_data, arguments["token"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_order":
            result = await client.get_order_by_id(arguments["order_id"], arguments["token"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "cancel_order":
            result = await client.delete_order(arguments["order_id"], arguments["token"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "create_user":
            result = await client.create_user(arguments)
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "login_user":
            result = await client.login_user(arguments["username"], arguments["password"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "get_user_profile":
            result = await client.get_user_by_username(arguments["username"], arguments["token"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "add_pet":
            pet_data = {
                "name": arguments["name"],
                "status": arguments.get("status", "available")
            }
            
            if "category" in arguments:
                pet_data["category"] = arguments["category"]
            if "photoUrls" in arguments:
                pet_data["photoUrls"] = arguments["photoUrls"]
            if "tags" in arguments:
                pet_data["tags"] = arguments["tags"]
            
            result = await client.add_pet(pet_data, arguments["token"])
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        elif name == "health_check":
            result = await client.health_check()
            return [TextContent(type="text", text=json.dumps(result, indent=2))]
        
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    
    except Exception as e:
        error_msg = f"Error executing {name}: {str(e)}"
        return [TextContent(type="text", text=error_msg)]

async def main():
    """Main entry point"""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())