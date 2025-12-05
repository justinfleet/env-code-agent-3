# Swagger Petstore MCP Server

This is an MCP (Model Context Protocol) server for the Swagger Petstore API. It provides tools for interacting with pets, orders, and users in the petstore system.

## Features

- **Pet Management**: Browse pets by status/tags, view pet details
- **Order Management**: Place orders, view/cancel orders  
- **User Management**: Create accounts, login, manage profiles
- **Store Operations**: Check inventory, manage store data
- **Role-Based Access**: Supports guest, customer, store_owner, and admin roles

## Installation

Install dependencies using uv:

```bash
uv install
```

## Configuration

Set environment variables:

```bash
# For local development
export APP_ENV=local
export API_BASE_URL=http://localhost:3002

# For production
export APP_ENV=production  
export API_BASE_URL=https://your-petstore-api.com
```

## Usage

Run the MCP server:

```bash
uv run python -m swagger_petstore_mcp.server
```

The server will start and listen for MCP protocol messages on stdin/stdout.

## Available Tools

### Pet Tools
- `get_all_pets_by_status` - Get pets by status (available/pending/sold)
- `get_pet_by_id` - Get specific pet details
- `find_pets_by_tags` - Find pets with specific tags
- `add_pet` - Add new pet (requires auth, store_owner/admin only)

### Store Tools  
- `get_store_inventory` - Get inventory counts by status
- `place_order` - Place an order for a pet
- `get_order` - Get order details
- `cancel_order` - Cancel an order

### User Tools
- `create_user` - Create new user account
- `login_user` - Login and get auth token
- `get_user_profile` - View user profile

### System Tools
- `health_check` - Check API health status

## Authentication

Most operations require authentication. Use `login_user` tool first to get a token:

```json
{
  "username": "customer1", 
  "password": "password"
}
```

Then use the returned token for authenticated operations.

## Role Permissions

- **Guest**: Browse pets, view inventory (no auth required)
- **Customer**: Place/cancel orders, manage own profile
- **Store Owner**: Manage pets, view all orders, approve orders
- **Admin**: Full access, delete users, change roles

## Example Usage

1. Check health:
```json
{"tool": "health_check", "arguments": {}}
```

2. Browse available pets:
```json
{"tool": "get_all_pets_by_status", "arguments": {"status": "available"}}
```

3. Login as customer:
```json
{"tool": "login_user", "arguments": {"username": "customer1", "password": "password"}}
```

4. Place order:
```json
{
  "tool": "place_order",
  "arguments": {
    "pet_id": 1,
    "token": "your_jwt_token_here"
  }
}
```

## Development

The MCP server connects to the local petstore API server. Make sure the API server is running on the configured port (default: 3002).

For development with the included sample data:
- Admin user: `admin` / `password`
- Store owner: `storeowner` / `password`  
- Customer: `customer1` / `password`