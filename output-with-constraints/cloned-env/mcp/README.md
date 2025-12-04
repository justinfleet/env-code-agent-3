# Petstore MCP Server

Model Context Protocol (MCP) server for the Swagger Petstore API.

## Setup

1. Install dependencies with uv:
```bash
cd mcp
uv sync
```

2. Run the MCP server:
```bash
# For local development (connects to http://localhost:3002)
APP_ENV=local uv run python -m petstore_mcp.server

# For production
APP_ENV=production API_BASE_URL=https://your-api-url.com uv run python -m petstore_mcp.server
```

## Available Tools

### Authentication
- `login` - Login to get JWT token

### Pet Management  
- `get_pet_by_id` - Get specific pet details
- `find_pets_by_status` - Find pets by status (available/pending/sold)
- `find_pets_by_tags` - Find pets by tags

### Store Operations
- `get_store_inventory` - Get inventory counts by pet status
- `get_order_by_id` - Get order details
- `place_order` - Place order for a pet

### User Management
- `get_user` - Get user profile information

## Authentication

Most operations require authentication. First login to get a JWT token:

```json
{
  "tool": "login",
  "arguments": {
    "username": "customer",
    "password": "customer123"
  }
}
```

Then use the returned token in subsequent requests:

```json
{
  "tool": "find_pets_by_status", 
  "arguments": {
    "status": "available",
    "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

## Environment Variables

- `APP_ENV` - Set to "local" for development, "production" for production
- `API_BASE_URL` - Base URL for the Petstore API (defaults to http://localhost:3002)

## Sample Users

The system includes these pre-configured users:

- **admin** (password: admin123) - Full system access
- **store_owner** (password: store123) - Manage pets and orders  
- **customer** (password: customer123) - Place orders and view profile