"""
Petstore MCP Server

This server provides MCP tools for interacting with the Petstore API,
allowing LLMs to browse pets, manage inventory, and handle orders.
"""

import asyncio
import os
from typing import Any, Dict, List
from mcp.server import Server
from mcp.server.stdio import stdio_server
from .client import PetstoreClient

# Initialize the MCP app
app = Server("petstore-mcp")

# Initialize API client
api_base_url = os.getenv("API_BASE_URL", "http://localhost:3002")
client = PetstoreClient(api_base_url)

@app.list_tools()
async def list_tools() -> List[Dict[str, Any]]:
    """List available MCP tools for the Petstore API."""
    return [
        {
            "name": "get_pets_by_status",
            "description": "Find pets by their status (available, pending, sold)",
            "inputSchema": {
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
        },
        {
            "name": "get_pets_by_tags",
            "description": "Find pets by tags",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of tags to search for"
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (required)"
                    }
                },
                "required": ["tags", "auth_token"]
            }
        },
        {
            "name": "get_pet_by_id",
            "description": "Get detailed information about a specific pet",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pet_id": {
                        "type": "integer",
                        "description": "Pet ID to retrieve"
                    }
                },
                "required": ["pet_id"]
            }
        },
        {
            "name": "get_store_inventory",
            "description": "Get inventory counts by pet status",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (required)"
                    }
                },
                "required": ["auth_token"]
            }
        },
        {
            "name": "login_user",
            "description": "Authenticate a user and get access token",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "Username for login"
                    },
                    "password": {
                        "type": "string",
                        "description": "Password for login"
                    }
                },
                "required": ["username", "password"]
            }
        },
        {
            "name": "get_user_profile",
            "description": "Get user profile information",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "username": {
                        "type": "string",
                        "description": "Username to retrieve"
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (required)"
                    }
                },
                "required": ["username", "auth_token"]
            }
        },
        {
            "name": "create_pet",
            "description": "Add a new pet to the store (store_owner/admin only)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Pet name"
                    },
                    "category": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"}
                        },
                        "description": "Pet category"
                    },
                    "photo_urls": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "URLs of pet photos"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "object", "properties": {"name": {"type": "string"}}},
                        "description": "Pet tags"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["available", "pending", "sold"],
                        "description": "Pet status"
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (required)"
                    }
                },
                "required": ["name", "auth_token"]
            }
        },
        {
            "name": "place_order",
            "description": "Place an order for a pet (authenticated users only)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "pet_id": {
                        "type": "integer",
                        "description": "ID of pet to order"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Quantity (must be 1 for live animals)",
                        "default": 1
                    },
                    "ship_date": {
                        "type": "string",
                        "description": "Shipping date (ISO format)"
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (required)"
                    }
                },
                "required": ["pet_id", "auth_token"]
            }
        },
        {
            "name": "get_order",
            "description": "Get order details by ID",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "order_id": {
                        "type": "integer",
                        "description": "Order ID to retrieve"
                    },
                    "auth_token": {
                        "type": "string",
                        "description": "JWT authentication token (required)"
                    }
                },
                "required": ["order_id", "auth_token"]
            }
        }
    ]

@app.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Handle MCP tool calls."""
    
    try:
        if name == "get_pets_by_status":
            result = await client.get_pets_by_status(
                status=arguments["status"],
                auth_token=arguments["auth_token"]
            )
            return [{"type": "text", "text": f"Found {len(result)} pets with status '{arguments['status']}':\n\n" + 
                    "\n".join([f"- {pet['name']} (ID: {pet['id']}, Category: {pet['category']['name'] if pet.get('category') else 'None'})" 
                              for pet in result])}]
                              
        elif name == "get_pets_by_tags":
            result = await client.get_pets_by_tags(
                tags=arguments["tags"],
                auth_token=arguments["auth_token"]
            )
            return [{"type": "text", "text": f"Found {len(result)} pets with tags {arguments['tags']}:\n\n" + 
                    "\n".join([f"- {pet['name']} (ID: {pet['id']}, Status: {pet['status']})" 
                              for pet in result])}]
                              
        elif name == "get_pet_by_id":
            result = await client.get_pet_by_id(pet_id=arguments["pet_id"])
            pet = result
            return [{"type": "text", "text": f"Pet Details:\n" +
                    f"ID: {pet['id']}\n" +
                    f"Name: {pet['name']}\n" +
                    f"Status: {pet['status']}\n" +
                    f"Category: {pet['category']['name'] if pet.get('category') else 'None'}\n" +
                    f"Tags: {', '.join([tag['name'] for tag in pet.get('tags', [])])}\n" +
                    f"Photo URLs: {', '.join(pet.get('photoUrls', []))}"
            }]
                    
        elif name == "get_store_inventory":
            result = await client.get_store_inventory(auth_token=arguments["auth_token"])
            return [{"type": "text", "text": f"Store Inventory:\n" +
                    f"Available: {result.get('available', 0)}\n" +
                    f"Pending: {result.get('pending', 0)}\n" +
                    f"Sold: {result.get('sold', 0)}"
            }]
            
        elif name == "login_user":
            result = await client.login_user(
                username=arguments["username"],
                password=arguments["password"]
            )
            return [{"type": "text", "text": f"Login successful!\nToken: {result['token']}\nExpires: {result['expires']}"}]
            
        elif name == "get_user_profile":
            result = await client.get_user_profile(
                username=arguments["username"],
                auth_token=arguments["auth_token"]
            )
            return [{"type": "text", "text": f"User Profile:\n" +
                    f"ID: {result['id']}\n" +
                    f"Username: {result['username']}\n" +
                    f"Name: {result.get('firstName', '')} {result.get('lastName', '')}\n" +
                    f"Email: {result.get('email', 'N/A')}\n" +
                    f"Phone: {result.get('phone', 'N/A')}\n" +
                    f"Status: {result.get('userStatus', 0)}"
            }]
            
        elif name == "create_pet":
            result = await client.create_pet(
                name=arguments["name"],
                category=arguments.get("category"),
                photo_urls=arguments.get("photo_urls", []),
                tags=arguments.get("tags", []),
                status=arguments.get("status", "available"),
                auth_token=arguments["auth_token"]
            )
            return [{"type": "text", "text": f"Pet created successfully!\n" +
                    f"ID: {result['id']}\n" +
                    f"Name: {result['name']}\n" +
                    f"Status: {result['status']}"
            }]
            
        elif name == "place_order":
            result = await client.place_order(
                pet_id=arguments["pet_id"],
                quantity=arguments.get("quantity", 1),
                ship_date=arguments.get("ship_date"),
                auth_token=arguments["auth_token"]
            )
            return [{"type": "text", "text": f"Order placed successfully!\n" +
                    f"Order ID: {result['id']}\n" +
                    f"Pet ID: {result['petId']}\n" +
                    f"Quantity: {result['quantity']}\n" +
                    f"Status: {result['status']}"
            }]
            
        elif name == "get_order":
            result = await client.get_order(
                order_id=arguments["order_id"],
                auth_token=arguments["auth_token"]
            )
            return [{"type": "text", "text": f"Order Details:\n" +
                    f"ID: {result['id']}\n" +
                    f"Pet ID: {result['petId']}\n" +
                    f"Quantity: {result['quantity']}\n" +
                    f"Status: {result['status']}\n" +
                    f"Complete: {result['complete']}\n" +
                    f"Ship Date: {result.get('shipDate', 'N/A')}"
            }]
            
        else:
            return [{"type": "text", "text": f"Unknown tool: {name}"}]
            
    except Exception as e:
        error_msg = str(e)
        return [{"type": "text", "text": f"Error calling {name}: {error_msg}"}]

async def main():
    """Main entry point for the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())