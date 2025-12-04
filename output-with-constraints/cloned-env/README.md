# Petstore Fleet Environment

A complete Fleet environment for the Swagger Petstore API with comprehensive role-based authentication, business logic, and state management.

## 🚀 Quick Start

### Prerequisites
- Node.js 20.9.0 or higher
- pnpm 9.15.1
- Python 3.11+ (for MCP server)
- uv (Python package manager)

### 1. Install Dependencies

```bash
# Install Node.js dependencies
pnpm install

# Install Python dependencies for MCP
cd mcp
uv install
cd ..
```

### 2. Set Environment Variables

```bash
# Required for JWT authentication
export JWT_SECRET="your-jwt-secret-key-here"

# Optional: Custom database path
# export DATABASE_PATH="/path/to/your/database.sqlite"
```

### 3. Start the Environment

#### Option A: Start everything with mprocs
```bash
pnpm dev
```

#### Option B: Start services individually
```bash
# Terminal 1: Start the API server
cd server
pnpm dev

# Terminal 2: Start the MCP server  
cd mcp
uv run python -m petstore_mcp.server
```

The API server will be available at: **http://localhost:3002**

## 📊 API Features

### Core Business Logic
- **Role-based authentication** with JWT tokens
- **Complex state transitions** (available → pending → sold)
- **Ownership-based authorization** for orders and profiles
- **Pre-condition validation** preventing invalid operations
- **Business rule enforcement** (quantity limits, pet availability)

### User Roles
- **Guest**: Browse pets, view inventory, register
- **Customer**: Place orders, view own orders, manage profile
- **Store Owner**: Manage pets, process all orders, upload images
- **Admin**: Full access, manage users, relist sold pets

### Key Endpoints
- `GET /api/v3/pet/{id}` - View pet details
- `GET /api/v3/pet/findByStatus` - Filter pets by status
- `POST /api/v3/store/order` - Place pet orders (with state transitions)
- `GET /api/v3/user/login` - Authenticate and get JWT token
- `GET /api/v3/store/inventory` - View inventory counts

## 🗄️ Database

Uses SQLite with:
- **WAL mode** enabled for better concurrency
- **Foreign key constraints** enforced
- **Automatic seed data** with sample pets, users, and orders
- **Path precedence**: DATABASE_PATH → ENV_DB_DIR → ./data/current.sqlite

### Sample Users
- **admin** / password (Admin role)
- **store_owner** / password (Store Owner role) 
- **customer1** / password (Customer role)
- **customer2** / password (Customer role)

*All passwords use bcrypt hashing*

## 🤖 MCP Server

The included MCP server provides LLM-friendly tools:

```bash
cd mcp
uv run python -m petstore_mcp.server
```

**Available Tools:**
- `get_all_pets` - Browse available pets
- `get_pet_by_id` - Get pet details
- `search_pets_by_tags` - Find pets by tags
- `get_store_inventory` - View stock levels
- `login_user` - Authenticate users
- `get_order_by_id` - View order details

## 🏗️ Project Structure

```
petstore-fleet/
├── server/                 # Node.js API server
│   ├── src/
│   │   ├── lib/
│   │   │   ├── db.ts      # SQLite connection with path precedence
│   │   │   └── auth.ts    # JWT auth & role-based access control
│   │   ├── routes/        # API route handlers
│   │   │   ├── pets.ts    # Pet management endpoints
│   │   │   ├── store.ts   # Order/inventory endpoints  
│   │   │   └── users.ts   # User management endpoints
│   │   └── index.ts       # Express server setup
│   ├── package.json
│   └── tsconfig.json
├── mcp/                   # Python MCP server
│   ├── src/petstore_mcp/
│   │   ├── server.py      # MCP server implementation
│   │   ├── client.py      # API client
│   │   └── __init__.py
│   ├── pyproject.toml
│   └── README.md
├── data/
│   ├── schema.sql         # Database schema with sample data
│   └── seed.db           # Pre-built database (auto-generated)
├── mprocs.yaml           # Multi-process development config
├── package.json          # Root workspace config
├── pnpm-workspace.yaml   # pnpm workspace definition
└── README.md
```

## 🔐 Authentication Examples

### Login and Get Token
```bash
curl "http://localhost:3002/api/v3/user/login?username=customer1&password=password"
```

### Use Token for Authenticated Requests
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  "http://localhost:3002/api/v3/store/inventory"
```

### Place an Order (Customer)
```bash
curl -X POST "http://localhost:3002/api/v3/store/order" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"petId": 1, "quantity": 1}'
```

## 📋 Business Rules Enforced

### Order Management
- ✅ Pet must be 'available' to place order
- ✅ Quantity must be exactly 1 (live animals)
- ✅ No duplicate active orders per pet
- ✅ Only 'placed' orders can be cancelled
- ✅ Delivered orders cannot be modified

### State Transitions  
- ✅ Order creation: pet available → pending
- ✅ Order delivery: pet pending → sold
- ✅ Order cancellation: pet pending → available

### Authorization Rules
- ✅ Customers see only their own orders/profile
- ✅ Store owners can manage pets and all orders
- ✅ Only admins can relist sold pets
- ✅ Only admins can delete users/change roles

### Validation & Pre-conditions
- ✅ Cannot delete pets with active orders
- ✅ Cannot delete users with active orders  
- ✅ Username uniqueness enforced
- ✅ Role changes restricted to admins

## 🚀 Production Deployment

### Docker Build
```bash
docker build -t petstore-api .
docker run -p 3002:3002 -e JWT_SECRET="your-secret" petstore-api
```

### Environment Variables
- `PORT` - Server port (default: 3002)
- `JWT_SECRET` - Required for authentication
- `DATABASE_PATH` - Custom database location
- `ENV_DB_DIR` - Directory containing current.sqlite
- `NODE_ENV` - Environment mode

## 📖 API Documentation

See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for complete endpoint documentation, including:
- Detailed request/response schemas
- Authentication requirements per endpoint
- Business rule explanations
- Error response formats
- State transition diagrams

## 🧪 Testing the API

The environment includes comprehensive validation that tests:
- ✅ All endpoints match specification
- ✅ Authentication/authorization logic
- ✅ Business rule enforcement
- ✅ State transition correctness
- ✅ Error handling scenarios

Run validation manually:
```bash
# This runs install, build, dev server start, and API tests
pnpm install && pnpm build && pnpm dev
```

## 🔧 Development

### Database Management
- Database auto-copies from `seed.db` to `current.sqlite` on first run
- Modify `data/schema.sql` and regenerate with new sample data
- Foreign keys and WAL mode enabled automatically

### Adding New Endpoints
1. Add route handler in appropriate `server/src/routes/` file
2. Implement authentication/authorization logic
3. Add business rule validation
4. Update API documentation

### Code Style
- TypeScript with strict mode enabled
- Consistent error handling with try/catch
- JWT-based authentication throughout
- RESTful API design principles