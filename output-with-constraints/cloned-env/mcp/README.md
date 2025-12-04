# Petstore MCP Server

Model Context Protocol (MCP) server for the Petstore API. This server provides tools that allow LLMs to interact with the Petstore API, including browsing pets, managing inventory, and handling orders.

## Features

- **Pet Management**: Browse pets by status or tags, get detailed pet information
- **Inventory**: Check store inventory counts
- **User Authentication**: Login and manage user profiles
- **Order Management**: Place orders and track order status
- **Role-based Access**: Respects API role permissions (customer, store_owner, admin)

## Setup

1. Install dependencies using uv:
```bash
cd mcp
uv sync
```

2. Set environment variables:
```bash
export API_BASE_URL=http://localhost:3002  # Petstore API URL
```

3. Run the MCP server:
```bash
uv run python -m petstore_mcp.server
```

## Available Tools

### Public Tools (no authentication required)
- `get_pet_by_id`: Get detailed information about a specific pet

### Authenticated Tools (requires auth_token)
- `login_user`: Authenticate and get access token
- `get_pets_by_status`: Find pets by status (available, pending, sold)
- `get_pets_by_tags`: Find pets by tags
- `get_store_inventory`: Get inventory counts by status
- `get_user_profile`: Get user profile information
- `get_order`: Get order details
- `place_order`: Place an order for a pet

### Privileged Tools (store_owner/admin only)
- `create_pet`: Add new pets to the store

## Authentication

Most tools require authentication. Use the `login_user` tool first to get an auth token:

```json
{
  "tool": "login_user",
  "arguments": {
    "username": "customer1",
    "password": "password"
  }
}
```

Then use the returned token in other tool calls:

```json
{
  "tool": "get_pets_by_status",
  "arguments": {
    "status": "available",
    "auth_token": "your-jwt-token-here"
  }
}
```

## Test Users

The system includes these test users (password: "password"):
- `admin` (role: admin) - Full access
- `storeowner` (role: store_owner) - Manage pets and orders
- `customer1` (role: customer) - Place and view own orders
- `customer2` (role: customer) - Place and view own orders

## Example Usage

1. **Login as a customer:**
```json
{"tool": "login_user", "arguments": {"username": "customer1", "password": "password"}}
```

2. **Browse available pets:**
```json
{"tool": "get_pets_by_status", "arguments": {"status": "available", "auth_token": "..."}}
```

3. **Place an order:**
```json
{"tool": "place_order", "arguments": {"pet_id": 1, "auth_token": "..."}}
```

4. **Check inventory (as store owner):**
```json
{"tool": "get_store_inventory", "arguments": {"auth_token": "..."}}
```