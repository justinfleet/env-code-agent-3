# Swagger Petstore Fleet Environment

A complete Fleet environment implementation of the Swagger Petstore API with comprehensive business logic, role-based access control, and state management.

## Features

- **Role-Based Access Control**: Guest, Customer, Store Owner, and Admin roles
- **Business Logic Enforcement**: State transitions, validation rules, ownership checks
- **JWT Authentication**: Secure token-based authentication system
- **Database State Management**: Automatic pet status transitions with orders
- **MCP Integration**: Model Context Protocol server for LLM interactions
- **Production Ready**: Docker deployment, CI/CD pipeline, health monitoring

## Architecture

- **Server**: TypeScript + Express API server (port 3002)
- **Database**: SQLite with WAL mode, foreign key constraints
- **MCP Server**: Python-based MCP server for LLM tool integration
- **Monorepo**: pnpm workspace with TypeScript and Python packages

## Quick Start

### Prerequisites

- Node.js 20.9.0+ 
- pnpm 9.15.1+
- Python 3.11+
- uv (for Python dependencies)

### Installation

1. **Clone and install dependencies:**
```bash
pnpm install
cd mcp && uv install && cd ..
```

2. **Start all services:**
```bash
pnpm dev
# OR individually:
# pnpm --filter server dev  # API server
# cd mcp && uv run python -m swagger_petstore_mcp.server  # MCP server
```

3. **Verify health:**
```bash
curl http://localhost:3002/health
```

## API Overview

**Base URL:** `http://localhost:3002/api/v3`

### Authentication

Login to get a JWT token:
```bash
curl "http://localhost:3002/api/v3/user/login?username=customer1&password=password"
```

Use the token in subsequent requests:
```bash
curl -H "Authorization: Bearer <token>" http://localhost:3002/api/v3/store/inventory
```

### Sample Users

| Username | Password | Role | Permissions |
|----------|----------|------|------------|
| `admin` | `password` | admin | Full access, user management |
| `storeowner` | `password` | store_owner | Manage pets, approve orders |
| `customer1` | `password` | customer | Place orders, manage profile |
| `customer2` | `password` | customer | Place orders, manage profile |

## Business Logic

### Role Permissions

- **Guest**: Browse pets and inventory (no auth required)
- **Customer**: Place/cancel own orders, manage own profile  
- **Store Owner**: Manage pets, view all orders, upload images
- **Admin**: Full access, user management, override ownership

### State Transitions

1. **Order Placement**: Pet status: available → pending
2. **Order Cancellation**: Pet status: pending → available  
3. **Order Delivery**: Pet status: pending → sold

### Validation Rules

- Orders: Pet must be available, quantity must be 1
- Pets: Only admin can relist sold pets as available
- Users: Only admin can change user roles
- Ownership: Users can only access their own data (unless bypass role)

### Pre-conditions

- Cannot delete pets with active orders
- Cannot delete users with active orders
- Cannot cancel non-placed orders

## Key Endpoints

### Pets
- `GET /api/v3/pet/{id}` - Get pet details (public)
- `GET /api/v3/pet/findByStatus?status=available` - Find by status (auth required)
- `POST /api/v3/pet` - Add pet (store_owner, admin)
- `PUT /api/v3/pet` - Update pet (store_owner, admin)
- `DELETE /api/v3/pet/{id}` - Delete pet (store_owner, admin)

### Orders  
- `POST /api/v3/store/order` - Place order (customer+)
- `GET /api/v3/store/order/{id}` - Get order (ownership check)
- `DELETE /api/v3/store/order/{id}` - Cancel order (ownership check)
- `GET /api/v3/store/inventory` - Get inventory (auth required)

### Users
- `POST /api/v3/user` - Create user (public)
- `GET /api/v3/user/login` - Login (public)
- `GET /api/v3/user/{username}` - Get profile (ownership check)
- `PUT /api/v3/user/{username}` - Update profile (ownership check)
- `DELETE /api/v3/user/{username}` - Delete user (admin only)

## MCP Server

The Model Context Protocol server enables LLM interactions with the API.

### Available Tools

- **Pet Tools**: `get_pet_by_id`, `get_all_pets_by_status`, `find_pets_by_tags`, `add_pet`
- **Order Tools**: `place_order`, `get_order`, `cancel_order`
- **Store Tools**: `get_store_inventory`  
- **User Tools**: `create_user`, `login_user`, `get_user_profile`
- **System Tools**: `health_check`

### MCP Usage

```bash
# Start MCP server
cd mcp && uv run python -m swagger_petstore_mcp.server

# Example: Check health
echo '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"health_check","arguments":{}},"id":1}' | uv run python -m swagger_petstore_mcp.server
```

## Database Schema

### Core Tables

- **users**: User accounts with roles and authentication
- **pets**: Pet inventory with status tracking
- **categories**: Pet categories (Dogs, Cats, etc.)
- **tags**: Pet tags for classification
- **pet_tags**: Many-to-many pet-tag relationships
- **orders**: Purchase orders with state tracking

### Key Features

- **Foreign Key Constraints**: Enforced referential integrity
- **WAL Mode**: Better concurrent access performance
- **Auto-copy**: seed.db → current.sqlite on first run
- **Path Precedence**: DATABASE_PATH → ENV_DB_DIR → default

## Development

### File Structure

```
├── data/
│   ├── schema.sql          # Database schema
│   └── seed.db            # Source database with sample data
├── server/                 # TypeScript API server
│   ├── src/
│   │   ├── lib/           # Database, auth utilities
│   │   ├── routes/        # API route handlers
│   │   └── index.ts       # Express server entry
│   └── package.json
├── mcp/                   # Python MCP server
│   ├── src/swagger_petstore_mcp/
│   │   ├── server.py      # MCP protocol server
│   │   └── client.py      # API client
│   └── pyproject.toml
└── package.json           # Root workspace config
```

### Environment Variables

```bash
# Server
PORT=3002                  # API server port
JWT_SECRET=your-secret-key # JWT signing key
DATABASE_PATH=/path/to/db  # Custom database location

# MCP  
APP_ENV=local             # local|production
API_BASE_URL=http://localhost:3002  # API endpoint
```

### Testing API

```bash
# Health check
curl http://localhost:3002/health

# Login
curl "http://localhost:3002/api/v3/user/login?username=customer1&password=password"

# Get available pets (requires auth)
curl -H "Authorization: Bearer <token>" "http://localhost:3002/api/v3/pet/findByStatus?status=available"

# Place order
curl -X POST -H "Authorization: Bearer <token>" \
     -H "Content-Type: application/json" \
     -d '{"petId": 1, "quantity": 1}' \
     http://localhost:3002/api/v3/store/order
```

## Deployment

### Docker

```bash
# Build image
docker build -t petstore-api .

# Run container
docker run -p 3002:3002 -e JWT_SECRET=production-secret petstore-api
```

### Production Considerations

- Set strong `JWT_SECRET` environment variable
- Configure proper CORS origins
- Set up SSL/TLS termination
- Use production database (PostgreSQL recommended)
- Configure log aggregation and monitoring
- Set up backup strategy for database

## API Documentation

See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for detailed endpoint documentation.

## License

This is a demonstration/educational implementation of the OpenAPI Petstore specification.