# Petstore MCP Server

This is an MCP (Model Context Protocol) server for the Swagger Petstore API. It allows LLMs to interact with the Petstore API through a standardized interface.

## Setup

1. **Install dependencies using uv:**
   ```bash
   cd mcp
   uv install
   ```

2. **Set environment variables:**
   ```bash
   export API_BASE_URL="http://localhost:3002"  # For local development
   # OR
   export API_BASE_URL="https://your-production-api.com"  # For production
   ```

3. **Run the MCP server:**
   ```bash
   uv run python -m petstore_mcp.server
   ```

## Available Tools

The MCP server provides the following tools for LLM interaction:

- **get_all_pets** - Get all pets, optionally filtered by status (available, pending, sold)
- **get_pet_by_id** - Get a specific pet by ID
- **search_pets_by_tags** - Find pets by tags (comma-separated)
- **get_store_inventory** - Get store inventory counts by pet status
- **get_order_by_id** - Get a specific order by ID (requires authentication)
- **get_user_by_username** - Get a user by username (requires authentication)
- **login_user** - Login a user and get authentication token

## Configuration

The MCP server automatically detects the environment:
- **Development**: Set `APP_ENV=local` to use `http://localhost:3002`
- **Production**: Set `APP_ENV=production` and provide production API URL

## Usage with Claude Desktop

Add this to your Claude Desktop config file:

```json
{
  "mcpServers": {
    "petstore": {
      "command": "uv",
      "args": ["run", "python", "-m", "petstore_mcp.server"],
      "cwd": "/path/to/your/project/mcp",
      "env": {
        "API_BASE_URL": "http://localhost:3002"
      }
    }
  }
}
```

## Authentication

Some API endpoints require authentication. Use the `login_user` tool first to get a token, then the client will handle authentication for subsequent requests.