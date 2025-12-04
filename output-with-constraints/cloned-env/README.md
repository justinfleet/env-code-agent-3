# Petstore Fleet Environment

A complete Fleet environment implementation of the Swagger Petstore API with JWT authentication, role-based access control, and full business rule enforcement.

## Features

- **Full API Implementation**: All Swagger Petstore endpoints with proper authentication
- **Role-Based Access Control**: guest, customer, store_owner, admin roles with appropriate permissions  
- **Business Rule Enforcement**: State transitions, ownership checks, and validation rules
- **JWT Authentication**: Secure token-based authentication with bcrypt password hashing
- **Database**: SQLite with WAL mode, foreign key constraints, and automatic state management
- **MCP Server**: Model Context Protocol server for LLM integration
- **Production Ready**: Docker support, CI/CD workflows, proper error handling

## Architecture

- **Server**: TypeScript + Express API server on port 3002
- **Database**: SQLite with automatic seed data and business rules
- **MCP**: Python-based Model Context Protocol server
- **Monorepo**: pnpm workspace with proper dependency management

## Quick Start

1. **Prerequisites**:
   - Node.js 20+ 
   - pnpm 9.15.1
   - Python 3.11+ with uv

2. **Clone and Install**:
   ```bash
   pnpm install
   ```

3. **Start Development**:
   ```bash
   # Start all services
   pnpm dev
   # OR use mprocs for multi-process management
   mprocs
   ```

4. **Verify Setup**:
   ```bash
   # Health check
   curl http://localhost:3002/health
   
   # Login to get token
   curl "http://localhost:3002/api/v3/user/login?username=customer&password=customer123"
   
   # Find available pets (requires token)
   curl -H "Authorization: Bearer <token>" \
     "http://localhost:3002/api/v3/pet/findByStatus?status=available"
   ```

## API Usage

### Sample Users
The system includes pre-configured users:

- **admin** (password: admin123) - Full system access
- **store_owner** (password: store123) - Manage pets and orders
- **customer** (password: customer123) - Place orders and manage profile

### Authentication Flow
```bash
# 1. Login
TOKEN=$(curl -s "http://localhost:3002/api/v3/user/login?username=customer&password=customer123" | jq -r '.data.token')

# 2. Use token in requests
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:3002/api/v3/pet/findByStatus?status=available"

# 3. Place an order
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"petId": 1, "quantity": 1}' \
  "http://localhost:3002/api/v3/store/order"
```

## Business Rules

The API enforces comprehensive business logic:

### Role-Based Access
- **Guests**: Can browse pets and inventory (no auth required)
- **Customers**: Can place orders, view/edit own profile, cancel own orders
- **Store Owners**: Can manage all pets, approve/deliver orders, view all profiles
- **Admins**: Full system access, can delete users, change roles, relist sold pets

### State Transitions
- Placing order: Pet status changes available → pending
- Canceling placed order: Pet status changes pending → available  
- Delivering order: Pet status changes pending → sold
- Only admins can change sold pets back to available

### Validation Rules
- Orders require quantity of 1 (live animals)
- Pets must be available to place orders
- Cannot delete pets/users with active orders
- Username uniqueness enforced
- Only admins can change user roles

## MCP Server

The Model Context Protocol server enables LLM integration:

```bash
cd mcp
APP_ENV=local uv run python -m petstore_mcp.server
```

Available MCP tools:
- `login` - Authenticate and get JWT token
- `get_pet_by_id` - Get specific pet details
- `find_pets_by_status` - Find pets by status
- `find_pets_by_tags` - Find pets by tags  
- `get_store_inventory` - Get inventory counts
- `place_order` - Place order for pet
- `get_order_by_id` - Get order details
- `get_user` - Get user profile

## Development

### Project Structure
```
petstore-env/
├── server/              # TypeScript API server
│   ├── src/
│   │   ├── lib/         # Database and auth utilities
│   │   ├── routes/      # API route handlers
│   │   └── index.ts     # Main server entry
├── mcp/                 # Python MCP server
│   └── src/petstore_mcp/
├── data/               # Database files
│   ├── schema.sql      # Database schema
│   └── seed.db         # Pre-populated database
└── docs/               # Documentation
```

### Environment Variables
- `PORT` - Server port (default: 3002)
- `JWT_SECRET` - JWT signing secret (required for production)
- `DATABASE_PATH` - Custom database path (optional)
- `ENV_DB_DIR` - Custom database directory (optional)

### Database
- **Development**: Uses `data/current.sqlite` (auto-copied from seed.db)
- **WAL Mode**: Enabled for concurrent access
- **Foreign Keys**: Enforced for data integrity
- **Auto-migration**: Copies seed.db if current.sqlite doesn't exist

### Testing Endpoints
The system includes comprehensive endpoint validation. All business rules are enforced:

```bash
# Test role restrictions (should fail without proper role)
curl -X POST -H "Authorization: Bearer <customer-token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "New Pet", "status": "available"}' \
  "http://localhost:3002/api/v3/pet"

# Test business rules (should fail - sold pet relist)
curl -X PUT -H "Authorization: Bearer <store-owner-token>" \
  -H "Content-Type: application/json" \
  -d '{"id": 4, "name": "Nemo", "status": "available"}' \
  "http://localhost:3002/api/v3/pet"
```

## Production Deployment

### Docker
```bash
docker build -t petstore-api .
docker run -p 3002:3002 -e JWT_SECRET="your-secret" petstore-api
```

### Environment Setup
```bash
# Required for production
export JWT_SECRET="your-secure-secret-key"
export NODE_ENV="production"

# Optional database configuration  
export DATABASE_PATH="/app/data/production.sqlite"
```

## API Documentation

See [API_DOCUMENTATION.md](API_DOCUMENTATION.md) for complete endpoint documentation with request/response examples and business rules.

## License

MIT License - see LICENSE file for details.