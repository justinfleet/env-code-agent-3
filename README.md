# env-code-agent-3

🤖 **Autonomous Fleet environment generation** from live APIs or formal specifications.

## Overview

env-code-agent-3 is an **agentic coding system** that generates Fleet-compliant environments through three approaches:

### Approach 1: Live API Exploration (3-Phase)
1. 🔍 **Autonomously explores** target APIs using Claude as the decision-maker
2. 📋 **Generates specifications** by synthesizing exploration findings
3. ⚡ **Writes production code** that implements the API as a Fleet environment

### Approach 2: Formal Specification (2-Phase)
1. 📋 **Parses formal specs** (OpenAPI, RealWorld, custom JSON)
2. ⚡ **Writes production code** directly from the specification

### Approach 3: Specification + Business Constraints (3-Phase)
1. 📋 **Parses formal specs** (OpenAPI, RealWorld, custom JSON)
2. 🔍 **Analyzes business constraints** in natural language → determines schema changes & application logic
3. ⚡ **Writes production code** with business rules enforced + generates validation workflows

All three approaches produce:
✅ **Fleet-compliant** output (seed.db, deterministic, backend-driven)

## Architecture

### Approach 1: Live API Exploration (3-Phase)
```
┌─────────────────────────────────────────────────┐
│         Exploration Agent (LLM-driven)          │
│  "I'll test /api/products... Found pagination"  │
│  "Now checking /api/products/1... Got it!"      │
└─────────────────┬───────────────────────────────┘
                  │ Observations & findings
                  ↓
┌─────────────────────────────────────────────────┐
│      Specification Builder (LLM synthesis)      │
│  Generates: OpenAPI spec + DB schema + logic    │
└─────────────────┬───────────────────────────────┘
                  │ Structured specification
                  ↓
┌─────────────────────────────────────────────────┐
│      Code Generator Agent (LLM coding)          │
│  Writes: Express server + SQLite + routes       │
└─────────────────┬───────────────────────────────┘
                  │ Generated environment
                  ↓
                Fleet-compliant environment ready! ✅
```

### Approach 2: Formal Specification (2-Phase)
```
┌─────────────────────────────────────────────────┐
│    Specification Ingestion Agent (Parser)       │
│  Reads: OpenAPI, RealWorld, custom specs        │
│  Parses: endpoints, schemas, relationships      │
└─────────────────┬───────────────────────────────┘
                  │ Structured specification
                  ↓
┌─────────────────────────────────────────────────┐
│      Code Generator Agent (LLM coding)          │
│  Writes: Express server + SQLite + routes       │
└─────────────────┬───────────────────────────────┘
                  │ Generated environment
                  ↓
                Fleet-compliant environment ready! ✅
```

### Approach 3: Specification + Business Constraints (3-Phase)
```
┌─────────────────────────────────────────────────┐
│    Specification Ingestion Agent (Parser)       │
│  Reads: OpenAPI, RealWorld, custom specs        │
│  Parses: endpoints, schemas, relationships      │
└─────────────────┬───────────────────────────────┘
                  │ Base specification
                  ↓
┌─────────────────────────────────────────────────┐
│    Business Requirement Agent (LLM analysis)    │
│  Input: Natural language constraints file       │
│  Analyzes: Auth, roles, state machines, rules   │
│  Outputs: Schema changes + Application logic    │
│  Generates: Validation test workflows           │
└─────────────────┬───────────────────────────────┘
                  │ Enriched specification + workflows
                  ↓
┌─────────────────────────────────────────────────┐
│      Code Generator Agent (LLM coding)          │
│  Writes: Express server + SQLite + routes       │
│  Implements: Business rules from requirements   │
│  Validates: Runs workflow tests to verify       │
└─────────────────┬───────────────────────────────┘
                  │ Generated environment
                  ↓
                Fleet-compliant environment ready! ✅
```

## Quick Start

### Prerequisites

- Node.js 20+
- Anthropic API key ([get one here](https://console.anthropic.com/))
- Target API running locally or remotely

### Installation

```bash
# Clone the repo
git clone https://github.com/justinfleet/env-code-agent-3.git
cd env-code-agent-3

# Install dependencies
pnpm install

# Set up environment
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### Usage

#### Option 1: Clone from Live API (3-Phase)

```bash
# Clone a running API
python3 -m src.cli clone http://localhost:3001

# With custom options
python3 -m src.cli clone http://localhost:3001 \
  --output ./my-output \
  --port 3002 \
  --max-iterations 50 \
  --endpoints /api/products /api/users

# Just explore (don't generate code)
python3 -m src.cli explore http://localhost:3001
```

#### Option 2: Clone from Formal Specification (2-Phase)

```bash
# From local spec file
python3 -m src.cli from-spec ./examples/realworld-conduit-spec.json

# From documentation URL (auto-extracts and parses)
python3 -m src.cli from-spec https://realworld-docs.netlify.app/specifications/backend/endpoints \
    --output ./output-realworld \
    --port 3003

# From OpenAPI spec URL
python3 -m src.cli from-spec https://example.com/api-spec.json

# With custom options
python3 -m src.cli from-spec ./spec.json \
  --output ./my-output \
  --port 3002
```

#### Option 3: Clone from Specification + Business Constraints (3-Phase)

```bash
# From OpenAPI spec with business constraints
python3 -m src.cli from-spec-with-constraints https://petstore3.swagger.io/api/v3/openapi.json \
    -c examples/petstore-constraints.txt \
    -o ./output-petstore

# Validate and fix an existing environment
python3 -m src.cli validate ./output-petstore/cloned-env
```

**Example constraints file (petstore-constraints.txt):**
```text
## Authentication & Roles
- All API operations require authentication
- Three roles exist: customer, store_owner, admin
- Role hierarchy: admin > store_owner > customer

## Pet Management
- Only store_owner or admin can add, edit, or delete pets
- Cannot delete a pet that has active orders

## Order Management
- Customers can only view their own orders
- Only store_owner or admin can approve/deliver orders
- Placing an order changes pet status to "pending"
- Delivering an order changes pet status to "sold"

## Validation Rules
- Order quantity must be exactly 1
- Cannot order a pet that is not "available"
```

**Supported spec formats:**
- Documentation URLs (HTML - auto-extracts API info)
- OpenAPI 3.x (JSON/YAML)
- RealWorld Conduit format
- Custom JSON specifications
- Any structured API documentation

### Run the Generated Environment

```bash
cd output/cloned-env
pnpm install
pnpm run dev  # Starts server + MCP via mprocs
```

The `pnpm run dev` command uses mprocs to start both:
- **Server**: Express API on http://localhost:3001
- **MCP**: Python MCP server for LLM interaction

## How It Works

### Phase 1: Autonomous Exploration

The **Exploration Agent** uses Claude to intelligently explore the API:

```
Agent: "I'll start by checking /health and /api"
Agent: "Found /api/products returning an array"
Agent: "Let me test /api/products/1 for single item"
Agent: "Testing pagination with ?page=2"
Agent: "Looking for related endpoints like /api/categories"
```

The LLM **decides what to test next** based on what it discovers.

### Phase 2: Specification Generation

The **Specification Agent** synthesizes findings into structured format:

```json
{
  "endpoints": [
    {
      "path": "/api/products/search",
      "method": "GET",
      "logic": "Full-text search with pagination"
    }
  ],
  "database": {
    "tables": [
      {
        "name": "products",
        "fields": [...]
      }
    ]
  }
}
```

### Phase 2b: Business Requirement Analysis (for `from-spec-with-constraints`)

The **Business Requirement Agent** analyzes natural language constraints and determines implementation requirements at two layers:

#### Schema Layer (Database)
Determines additional database fields needed to enforce business rules:
- `role` field on users table (for role-based access control)
- `user_id` field on orders table (for ownership tracking)
- Status fields for state machines
- Foreign keys to establish relationships

#### Application Layer (Code Logic)
Determines runtime enforcement rules:
- **Authentication**: JWT-based auth with configurable endpoints
- **Authorization**: Role-based access control per endpoint
- **Ownership checks**: Users can only access their own resources
- **State transitions**: Automatic status changes (e.g., order placed → pet pending)
- **Pre-conditions**: Checks before operations (e.g., can't delete pet with active orders)
- **Validation rules**: Field-level validation (e.g., quantity must be 1)

#### Output: Enriched Specification
The agent produces a specification enriched with:
```json
{
  "schema_changes": { "users": { "add_fields": [{"name": "role", ...}] } },
  "auth_config": { "method": "jwt", "token_payload": ["user_id", "username", "role"] },
  "roles": { "customer": {...}, "store_owner": {...}, "admin": {...} },
  "endpoint_auth": [{ "path": "/pet", "allowed_roles": ["store_owner", "admin"] }],
  "state_transitions": [{ "trigger": "create order", "effect": "pet.status = pending" }],
  "validation_rules": [{ "field": "quantity", "check": "value == 1" }],
  "pre_conditions": [{ "endpoint": "DELETE /pet", "check": "no active orders" }]
}
```

#### Output: Validation Workflows
The agent also generates executable test workflows (YAML) that verify the implementation:
- **Happy path tests**: Normal successful operations
- **Authorization tests**: Role-based access control enforcement
- **Validation tests**: Business rule enforcement
- **State transition tests**: Automatic state changes
- **Error handling tests**: Pre-condition checks

These workflows run against the generated API to verify correctness.

### Phase 3: Code Generation

The **Code Generator Agent** writes production-ready code:

- ✅ Express + TypeScript server
- ✅ SQLite database with seed data
- ✅ Actual SQL queries (not mocks!)
- ✅ Fleet-compliant structure
- ✅ Proper error handling

## Examples

### Example 1: From Live API (Famazon)

```bash
# Assuming famazon is running on :3000
python3 -m src.cli clone http://localhost:3000

# Output:
🔍 PHASE 1: AUTONOMOUS API EXPLORATION
💭 Agent: I'll start by checking common patterns...
🔧 Tool: make_http_request { path: "/health" }
💭 Agent: Found API at /api, exploring endpoints...
✅ Exploration complete!

📋 PHASE 2: SPECIFICATION GENERATION
🏗️ Building API specification...
✅ Specification generated: 15 endpoints, 8 tables

⚡ PHASE 3: FLEET ENVIRONMENT GENERATION
🔧 Tool: write_file { path: "data/schema.sql" }
🔧 Tool: write_file { path: "src/index.ts" }
✅ Code generation complete!

🎉 CLONING COMPLETE!
```

### Example 2: From Formal Specification (RealWorld Conduit)

```bash
# From documentation URL
python3 -m src.cli from-spec https://realworld-docs.netlify.app/specifications/backend/endpoints \
    --output ./output-realworld \
    --port 3003

# Output:
📋 PHASE 1: SPECIFICATION INGESTION
📥 Fetching spec from https://realworld-docs.netlify.app/specifications/backend/endpoints...
✅ Fetched 44606 characters (HTML format)
🔍 Extracting API information from HTML...
✅ Reduced to 8234 chars (relevant content only)
💭 Agent: Parsing endpoint definitions...
💭 Agent: Building database schema from data structures...
✅ Specification parsed successfully!
   API: RealWorld Conduit API
   Endpoints: 19
   Tables: 7

⚡ PHASE 2: FLEET ENVIRONMENT GENERATION
📁 Output directory: ./output-realworld/cloned-env
🔧 Generating files...
✅ Code generation complete in 11 iterations!
   Generated 26 files

🎉 CLONING COMPLETE!
```

Alternatively, use the included local spec file:

```bash
python3 -m src.cli from-spec ./examples/realworld-conduit-spec.json
```

The RealWorld Conduit API demonstrates:
- Complete RealWorld (Medium clone) API specification
- 19 endpoints (articles, comments, users, profiles, favorites, follows, tags)
- 7 database tables with relationships
- Authentication with JWT
- Many-to-many relationships (article_tags, favorites, follows)

## Configuration

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=your_key_here

# Optional
ANTHROPIC_MODEL=claude-sonnet-4-20250514  # Model to use
OUTPUT_DIR=./output/cloned-env             # Output directory
MAX_ITERATIONS=50                          # Max agent iterations
```

### Supported Models

- `claude-sonnet-4-20250514` (default, recommended)
- `claude-3-5-sonnet-20241022`
- `claude-opus-4-20250514` (slower but more thorough)

## Fleet Compliance

Generated environments follow all Fleet standards:

- ✅ `seed.db` ready for immediate use (contains schema + initial data)
- ✅ `current.sqlite` used at runtime (auto-copied from seed.db)
- ✅ `schema.sql` without CHECK constraints
- ✅ INTEGER AUTOINCREMENT primary keys
- ✅ WAL mode + foreign keys enabled
- ✅ DATABASE_PATH → ENV_DB_DIR → default precedence
- ✅ MCP server for LLM interaction (Python-based)
- ✅ pnpm workspace monorepo structure
- ✅ mprocs.yaml for multi-process development
- ✅ Dockerfile for production deployment
- ✅ Backend-driven (no localStorage dependencies)
- ✅ Deterministic behavior support

## Project Structure

```
env-code-agent-3/
├── src/
│   ├── core/
│   │   ├── llm_client.py         # Anthropic API wrapper
│   │   ├── base_agent.py         # Agentic loop framework
│   │   └── workflow_runner.py    # Test workflow executor
│   ├── agents/
│   │   ├── exploration_agent.py       # LLM-driven API explorer
│   │   ├── specification_agent.py     # Spec generator from exploration
│   │   ├── spec_ingestion_agent.py    # OpenAPI/formal spec parser
│   │   ├── business_requirement_agent.py  # Constraint analyzer
│   │   └── code_generator_agent.py    # Code writer with validation
│   └── cli.py                    # CLI entry point
├── scripts/
│   └── run_workflows.py          # Manual workflow test runner
├── examples/
│   └── petstore-constraints.txt  # Example business constraints
├── output/                       # Generated environments
└── DESIGN_AGENTIC.md            # Architecture docs
```

## Development

```bash
# Run in development mode
pnpm dev clone http://localhost:3000

# Build for production
pnpm build

# Run built version
pnpm start clone http://localhost:3000
```

## Observations & Lessons Learned (Business Constraints Mode)

The `from-spec-with-constraints` mode is significantly more complex than simple spec-to-code generation. Key observations:

### Multi-step Workflows are Harder
Workflows involving multiple API calls are significantly more difficult to fully pass than single API call validations. Each step depends on previous steps, state accumulates, and any mismatch compounds into failures.

### Authentication Adds Complexity
Adding authentication makes it harder to get generated workflow tests to pass:
- **Endpoint mismatches**: The LLM sometimes generates slightly different auth API endpoints in workflows vs. the generated code (e.g., `/user/login` vs `/api/v3/user/login`)
- **Token field names**: Code may return `sessionToken` while workflows expect `token`
- **Password hashing**: The coding agent sometimes generates invalid bcrypt hashes in seed data that don't match the test password

These issues required adding explicit guidance to the prompts (e.g., "always use `token` field name", "use this exact bcrypt hash").

### Prompt Size vs. Determinism Tradeoff
As prompts grow larger with more guidance, non-determinism increases:
- Despite explicit instructions to call multiple `write_file` tools in parallel, the agent sometimes only calls one at a time
- This behavior becomes more frequent as the prompt becomes larger
- Larger prompts may cause the LLM to "forget" or deprioritize certain instructions

### Database State Pollution
Workflows that modify state (e.g., placing orders) affect subsequent workflows. Solutions:
- Reset database between workflows via `/reset` endpoint
- Use different resources (pet IDs) for different tests
- Design workflows to be independent/idempotent

## Roadmap

- [x] Agentic exploration with LLM decision-making
- [x] Specification generation from observations
- [x] Code generation with Fleet compliance
- [x] MCP server generation (Python-based with uv)
- [x] pnpm monorepo structure
- [x] mprocs.yaml for multi-process development
- [x] Dockerfile for production deployment
- [x] Business requirement analysis from natural language constraints
- [x] Validation workflows with test runner
- [x] Schema + application layer separation
- [ ] Database reset endpoint for workflow isolation
- [ ] SvelteKit client generation
- [ ] CLI tool cloning (non-HTTP)

## Contributing

This is an internal Fleet tool. For questions or contributions, contact the Fleet team.

## License

MIT

## Credits

Built by the Fleet team for automated environment generation.
