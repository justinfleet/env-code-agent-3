# Petstore API Fleet Environment

A complete production-ready environment for the Swagger Petstore API with authentication, authorization, and business logic enforcement.

## Features

- **RESTful API Server** (TypeScript + Express) on port 3002
- **JWT Authentication** with role-based access control
- **SQLite Database** with WAL mode and foreign key constraints
- **MCP Server** (Python) for LLM integration
- **Comprehensive Business Logic** including state transitions and validation
- **Role-based Permissions** (guest, customer, store_owner, admin)

## Quick Start

### Prerequisites
- Node.js 20+ and pnpm 9.15.1
- Python 3.11+ with uv

### Setup

1. **Install dependencies:**
```bash
pnpm install
```

2. **Start all services:**
```bash
pnpm dev
```

This starts:
- API server on http://localhost:3002
- MCP server for LLM integration

3. **Test the API:**
```bash
# Health check
curl http://localhost:3002/health

# Login to get token
curl "http://localhost:3002/api/v3/user/login?username=customer1&password=password"

# Browse available pets (use token from login)
curl -H "Authorization: Bearer <token>" "http://localhost:3002/api/v3/pet/findByStatus?status=available"
```

## Architecture

### Server (TypeScript)
- **Express.js** REST API server
- **JWT authentication** with bcrypt password hashing  
- **SQLite database** with better-sqlite3
- **Role-based authorization** middleware
- **Business logic enforcement** (state transitions, validations)

### MCP Server (Python)
- **Model Context Protocol** server for LLM interaction
- **HTTP client** to communicate with API server
- **Environment-aware** configuration (local vs production)

### Database
- **SQLite** with WAL mode enabled
- **Auto-migration** from seed.db on startup
- **Foreign key constraints** enforced
- **Sample data** included for testing

## API Endpoints

### Authentication
- `GET /api/v3/user/login` - User login
- `GET /api/v3/user/logout` - User logout
- `POST /api/v3/user` - Register new user

### Pets
- `POST /api/v3/pet` - Add new pet (store_owner/admin)
- `PUT /api/v3/pet` - Update pet (store_owner/admin)
- `GET /api/v3/pet/findByStatus` - Find pets by status
- `GET /api/v3/pet/findByTags` - Find pets by tags
- `GET /api/v3/pet/{id}` - Get pet by ID
- `DELETE /api/v3/pet/{id}` - Delete pet (store_owner/admin)

### Store
- `GET /api/v3/store/inventory` - Get inventory counts
- `POST /api/v3/store/order` - Place order
- `GET /api/v3/store/order/{id}` - Get order
- `DELETE /api/v3/store/order/{id}` - Cancel order

### Users
- `GET /api/v3/user/{username}` - Get user profile
- `PUT /api/v3/user/{username}` - Update user
- `DELETE /api/v3/user/{username}` - Delete user (admin)

## Roles and Permissions

### Guest (Unauthenticated)
- Browse pets and view details
- View inventory

### Customer
- Place and view own orders
- Cancel own placed orders
- Manage own profile

### Store Owner
- All customer permissions
- Manage pets (create, update, delete)
- View and approve all orders
- Deliver orders

### Admin
- All permissions
- Manage users and change roles
- Re-list sold pets as available
- Delete users

## Business Logic

### State Transitions
- **Order Placement**: Available pet → Pending
- **Order Delivery**: Pending pet → Sold  
- **Order Cancellation**: Pending pet → Available
- **Pet Re-listing**: Sold → Available (admin only)

### Validation Rules
- Orders require quantity = 1 for live animals
- Cannot order unavailable pets
- Cannot delete pets/users with active orders
- Role-based status transition restrictions

### Pre-conditions
- Pets with active orders cannot be deleted
- Users with active orders cannot be deleted
- Delivered orders cannot be modified

## Test Users

All test users have password: `password`

- **admin** - System administrator
- **storeowner** - Store management
- **customer1** - Regular customer
- **customer2** - Regular customer

## Environment Variables

- `PORT` - Server port (default: 3002)
- `JWT_SECRET` - JWT signing secret
- `DATABASE_PATH` - Custom database path
- `ENV_DB_DIR` - Database directory
- `NODE_ENV` - Environment (development/production)

## Development

### Project Structure
```
├── server/          # TypeScript API server
│   ├── src/
│   │   ├── routes/  # API route handlers
│   │   ├── lib/     # Database and utilities
│   │   └── index.ts # Server entry point
│   └── package.json
├── mcp/             # Python MCP server
│   ├── src/petstore_mcp/
│   │   ├── server.py   # MCP server
│   │   └── client.py   # API client
│   └── pyproject.toml
├── data/
│   ├── schema.sql   # Database schema
│   └── seed.db      # Seed database
├── mprocs.yaml      # Multi-process config
└── package.json     # Root package
```

### Scripts
- `pnpm dev` - Start all services
- `pnpm build` - Build TypeScript
- `pnpm start` - Start production server

### Database
- Seeds from `data/seed.db` automatically
- Runtime database: `data/current.sqlite`
- WAL mode enabled for better concurrency
- Foreign keys enforced

## API Documentation

See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for complete endpoint documentation.

## MCP Integration

The included MCP server provides LLM-friendly tools for:
- User authentication and profile management
- Pet browsing and inventory checking
- Order placement and tracking
- Store management (for authorized users)

See [mcp/README.md](./mcp/README.md) for MCP setup details.

## Production Deployment

### Docker
```bash
docker build -t petstore-api .
docker run -p 3002:3002 -e JWT_SECRET=your-secret petstore-api
```

### Environment
- Set `JWT_SECRET` to a secure random value
- Consider using PostgreSQL for production databases
- Set up proper logging and monitoring
- Configure CORS for your domains

## License

MIT