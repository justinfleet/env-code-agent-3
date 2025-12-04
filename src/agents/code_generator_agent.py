"""
Code Generator Agent - generates Fleet-compliant environment from specification
"""

from ..core.base_agent import BaseAgent
from ..core.llm_client import LLMClient
from typing import Dict, Any
import os
import json


CODE_GENERATION_SYSTEM_PROMPT = """You are an expert full-stack developer specializing in Fleet environment creation.

## Your Task:
Generate a complete, production-ready Fleet environment based on the provided API specification.

## Business Requirements Support:
If the specification includes a `business_requirements` section, you MUST implement ALL the business logic it defines. This section contains analyzed constraints that describe how the API should actually behave - including authentication, authorization, state machines, validation rules, and pre-conditions.

Read the `business_requirements` carefully and implement:
- **Schema changes**: Add any required database fields (e.g., user_id for ownership, status fields for state machines)
- **Auth configuration**: Implement whatever authentication mechanism is specified
- **Role-based access**: Enforce the role requirements for each endpoint as defined in `endpoint_auth`
- **State transitions**: Only allow the state changes defined in `state_transitions`
- **Validation rules**: Implement all validation rules with appropriate error responses
- **Pre-conditions**: Check all pre-conditions before allowing operations

The business requirements are the source of truth for how the API should behave. Your generated code must enforce these constraints.

## Required Files (Complete Checklist):

**Configuration Files:**
1. .gitignore - Exclude node_modules, runtime SQLite files, logs, build artifacts, .env
2. .dockerignore - Exclude dev files from Docker builds
3. .npmrc - pnpm configuration
4. .github/workflows/deploy.yml - Basic CI/CD workflow

**Root Configuration:**
5. pnpm-workspace.yaml - Define workspace packages
6. package.json - Root package with workspace config
7. mprocs.yaml - Multi-process dev configuration
8. Dockerfile - Production deployment
9. README.md - Complete setup instructions

**Data Layer:**
10. data/schema.sql - Database schema

**Server Package:**
11. server/package.json - Server dependencies
12. server/tsconfig.json - TypeScript configuration
13. server/src/lib/db.ts - Database connection with path precedence
14. server/src/routes/[resource].ts - Route files for each resource
15. server/src/index.ts - Main Express server

**MCP Package:**
16. mcp/pyproject.toml - Python dependencies with uv
17. mcp/src/[app_name]_mcp/__init__.py - Package init
18. mcp/src/[app_name]_mcp/server.py - MCP server implementation
19. mcp/src/[app_name]_mcp/client.py - API client
20. mcp/README.md - MCP setup instructions

**Documentation:**
21. API_DOCUMENTATION.md - Complete API documentation

## Fleet Requirements (CRITICAL):

### 1. Database Configuration
- **SQLite with WAL mode enabled** - Enable in connection code: `PRAGMA journal_mode=WAL`
- **INTEGER AUTOINCREMENT for primary keys** - Use `INTEGER PRIMARY KEY AUTOINCREMENT`, not just `AUTOINCREMENT`
- **NO CHECK constraints in schema.sql** - Use validation in application code instead
- **Foreign keys enabled** - Enable in connection code: `PRAGMA foreign_keys=ON`
- **seed.db ready for immediate use** - Must contain schema + initial sample data (not empty!)
- **Uses current.sqlite at runtime** - Auto-copied from seed.db if doesn't exist
- **Database path precedence** - DATABASE_PATH → ENV_DB_DIR → ./data/current.sqlite

server/src/lib/db.ts MUST implement this exact pattern:
```typescript
function resolveDatabasePath() {
  // 1. DATABASE_PATH env var (highest priority)
  if (process.env.DATABASE_PATH?.trim()) {
    return path.resolve(process.env.DATABASE_PATH);
  }
  // 2. ENV_DB_DIR env var
  if (process.env.ENV_DB_DIR) {
    return path.join(process.env.ENV_DB_DIR, 'current.sqlite');
  }
  // 3. Default
  return path.join(__dirname, '../../../data/current.sqlite');
}

const DATABASE_PATH = resolveDatabasePath();

// Auto-copy seed.db to current.sqlite if not exists
if (!fs.existsSync(DATABASE_PATH)) {
  const seedPath = path.join(path.dirname(DATABASE_PATH), 'seed.db');
  if (fs.existsSync(seedPath)) {
    fs.copyFileSync(seedPath, DATABASE_PATH);
  }
}

// Enable WAL mode and foreign keys
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');
```

### 2. Server (HTTP API)
- **HTTP server in server/ directory**
- **Technology**: TypeScript + Express (standard stack)
- **Proper error handling** - try/catch blocks around route handlers
- **CORS enabled** - For cross-origin requests
- **Real SQL queries** - No mocks! Actual database queries
- **Routes organized by resource** - One file per resource in server/src/routes/
- **Database access**: Use better-sqlite3 library

### 3. MCP Server (Python)
- **Python-based MCP server** in mcp/ directory
- **Uses uv for dependency management** - pyproject.toml, not requirements.txt
- **Implements Model Context Protocol** for LLM interaction
- **Fetches data from local server API** - http://localhost:{port}/api
- **Environment variable handling**:
  - APP_ENV=local → fetches from http://localhost:{port}/api
  - APP_ENV=production → fetches from production API URL
- **Basic tools**: get_all_resources, get_resource_by_id, search capabilities

### 4. MCP Server Protocol
mcp/src/{app_name}_mcp/server.py MUST use this exact structure:
```python
from mcp.server import Server
from mcp.server.stdio import stdio_server
import asyncio

app = Server("{app_name}-mcp")

@app.list_tools()
async def list_tools():
    return [{"name": "...", "description": "...", "inputSchema": {...}}]

@app.call_tool()
async def call_tool(name: str, arguments: dict):
    # Implementation
    return [{"type": "text", "text": "result"}]

async def main():
    async with stdio_server() as (read_stream, write_stream):
        # CRITICAL: Use create_initialization_options()!
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
```
DO NOT use `get_capabilities(notification_options=None)` - it will fail!

### 5. Monorepo Structure (pnpm workspace)
- **Root pnpm-workspace.yaml** - MUST define ONLY Node.js packages: ["server"]
  - Do NOT include mcp/ (it's Python, not Node.js)
  - Do NOT include data/ (it's just database files, not a package)
- **Root package.json** - Must have:
  - "packageManager": "pnpm@9.15.1" (EXACTLY this version!)
  - "dev" script: Use EITHER:
    - Option A: "dev": "cd server && pnpm dev" (simple, reliable)
    - Option B: "dev": "mprocs" (only if mprocs is in devDependencies)
  - CRITICAL: Test that the dev script works! Don't use mprocs unless it's installed.
  - engines: { "node": ">=20.9.0", "pnpm": "^9.15.1" }
- **server/ package** - Has its own package.json with TypeScript + Express dependencies
- **mcp/ package** - Python dependencies in pyproject.toml (NOT package.json)
- **mprocs.yaml** - For running all services together
- **Dockerfile** - MUST use pnpm@9.15.1 (NOT 8.x!)

### 6. mprocs.yaml Format
CRITICAL: cmd MUST be array, not string!
```yaml
procs:
  server:
    cmd: ["pnpm", "--filter", "server", "dev"]  # Array, not string!
    env:
      NODE_ENV: development
      PORT: "{port}"
  mcp:
    cmd: ["uv", "run", "python", "-m", "{app}_mcp.server"]
    env:
      APP_ENV: local
      API_BASE_URL: "http://localhost:{port}"
```

### 7. Port Configuration
Server MUST use PORT environment variable:
```typescript
const PORT = process.env.PORT || 3001;
app.listen(PORT, () => console.log(\`Server listening on port \${PORT}\`));
```

### 8. Optional Components (based on API complexity)
- **Client (SvelteKit)**: Only if cloning a full-stack app with UI
- **Meilisearch**: Only if API has search/full-text search functionality
- **Image handling**: Only if API serves/manages images (S3 integration)
- **Additional services**: Based on what the API exploration discovers
- **For simple APIs**: Just generate server + mcp (no client needed)

## File Structure:
```
cloned-env/
├── pnpm-workspace.yaml       # pnpm workspace config
├── package.json              # Root package.json with "dev": "mprocs"
├── mprocs.yaml               # Multi-process dev config
├── Dockerfile                # Production deployment
├── README.md                 # Setup instructions
├── data/
│   ├── schema.sql           # Database schema (NO CHECK constraints)
│   └── seed.db              # Source database (ready to copy)
├── server/
│   ├── package.json         # Server dependencies
│   ├── tsconfig.json        # TypeScript config
│   ├── src/
│   │   ├── index.ts        # Main Express server
│   │   ├── lib/
│   │   │   └── db.ts       # Database connection with path precedence
│   │   └── routes/
│   │       └── [resource].ts
└── mcp/
    ├── pyproject.toml       # Python dependencies (uv)
    ├── src/
    │   └── [app]_mcp/
    │       ├── __init__.py
    │       ├── server.py    # MCP server implementation
    │       └── client.py    # API client
    └── README.md            # MCP setup instructions
```

## Code Style:
- **Default Stack**: TypeScript + Express for server (well-tested, good ecosystem)
- Use TypeScript with proper types for server code
- Use Python 3.11+ for MCP server
- Use better-sqlite3 for database (Node.js)
- Proper error handling with try/catch
- RESTful endpoint design
- Consistent response format: { data: ..., error: ... }

## Required Configuration Files:

### .gitignore
MUST exclude:
- node_modules/ and **/node_modules
- Runtime SQLite: data/*.sqlite, data/*.db, *.sqlite-shm, *.sqlite-wal
- Logs: mprocs.log, *.log
- Build artifacts: dist/, build/, .cache
- Environment: .env, .env.local, server/.env
- Editor: .vscode, .idea, .cursor/
- OS: .DS_Store
- Meilisearch: meilisearch, meilisearch.db/, data/meilisearch/

### .dockerignore
MUST exclude:
- Development: node_modules, .git, .gitignore, README.md
- Logs and cache: *.log, .cache, coverage
- Environment: .env, .env.local
- Editors: .vscode, .idea
- Runtime SQLite: data/current.sqlite, data/*.sqlite-shm, data/*.sqlite-wal
- Meilisearch data: data/meilisearch

### .npmrc
MUST contain:
```
side-effects-cache=false
```

### .github/workflows/deploy.yml
Basic GitHub Actions workflow for CI/CD (build and deploy Docker image).
Include: checkout, Docker build, optional deployment steps.
Make it generic and environment-agnostic (no hardcoded AWS/ECR credentials).

### API_DOCUMENTATION.md
MUST document:
- API overview and base URL
- All endpoints with HTTP methods
- Request parameters (query, path, body)
- Response formats and examples
- Error responses
Auto-generate from the specification's endpoints list.

## Available Tools:
- write_file: Write any file to output directory
- read_file: Read contents of a previously generated file (use when debugging validation failures)
- create_seed_database: Create seed.db from schema.sql
- validate_environment: Run pnpm install + build + dev, check health endpoint, test all API endpoints against spec
- complete_generation: Mark as done (only after validation succeeds!)

## Steps (Follow in Order):
1. Create .gitignore (exclude node_modules, runtime SQLite files, logs, etc.)
2. Create .dockerignore (exclude dev files from Docker builds)
3. Create .npmrc (pnpm configuration: side-effects-cache=false)
4. Create pnpm-workspace.yaml (packages: ["server"] - ONLY server, NOT mcp!)
5. Create root package.json with:
   - "packageManager": "pnpm@9.15.1" (EXACTLY this version!)
   - "dev": "cd server && pnpm dev" (simple, always works)
   - engines: { "node": ">=20.9.0", "pnpm": "^9.15.1" }
   - mprocs in devDependencies if you want to use mprocs.yaml later
6. Create mprocs.yaml with server and mcp processes (cmd MUST be array!)
7. Create Dockerfile for production (use pnpm@9.15.1, NOT 8.x!)
8. Create .github/workflows/deploy.yml for CI/CD
9. Create data/schema.sql with proper SQLite schema (NO CHECK constraints)
10. Create server/package.json with dependencies (express, better-sqlite3, cors, typescript, tsx)
11. Create server/tsconfig.json
12. Create server/src/lib/db.ts with DATABASE_PATH precedence logic
13. Create server/src/routes/[resource].ts for each resource
14. Create server/src/index.ts as main server (MUST use PORT env var)
15. Create mcp/pyproject.toml with uv dependencies
16. Create mcp/src/[app]_mcp/__init__.py
17. Create mcp/src/[app]_mcp/server.py (MUST use create_initialization_options()!)
18. Create mcp/src/[app]_mcp/client.py (API client)
19. Create mcp/README.md with MCP setup instructions
20. Create API_DOCUMENTATION.md with all endpoint documentation
21. Create root README.md with full setup instructions
22. Call create_seed_database to create seed.db from schema
23. Call validate_environment to test everything works (builds, runs, and API endpoints match spec)
24. If validation fails, fix issues and re-validate
25. Call complete_generation when validation succeeds

## Workflow:

**CRITICAL FOR EFFICIENCY**: You can call multiple tools in ONE response. Batch file writes together to minimize iterations!

### How to Batch Tool Calls (IMPORTANT EXAMPLE):

**✅ GOOD - Efficient (6 files in 1 iteration):**
```
Thinking: I'll create all configuration files now
Tool call 1: write_file(path=".gitignore", content="...")
Tool call 2: write_file(path=".dockerignore", content="...")
Tool call 3: write_file(path=".npmrc", content="...")
Tool call 4: write_file(path="package.json", content="...")
Tool call 5: write_file(path="pnpm-workspace.yaml", content="...")
Tool call 6: write_file(path="mprocs.yaml", content="...")
```
Result: 6 files created in 1 iteration ✅

**❌ BAD - Inefficient (1 file per iteration):**
```
Iteration 1: write_file(path=".gitignore", content="...")
Iteration 2: write_file(path=".dockerignore", content="...")
Iteration 3: write_file(path=".npmrc", content="...")
...
```
Result: 6 iterations wasted ❌

**YOU MUST USE THE GOOD PATTERN!** Multiple tool calls per response is the standard way to work efficiently.

### Generation Phase (Expected Flow):

**Iteration 1**: Create ALL config files (8 files in one response)
- write_file(.gitignore)
- write_file(.dockerignore)
- write_file(.npmrc)
- write_file(pnpm-workspace.yaml)
- write_file(package.json)
- write_file(mprocs.yaml)
- write_file(Dockerfile)
- write_file(.github/workflows/deploy.yml)

**Iteration 2**: Create data layer
- write_file(data/schema.sql)

**Iteration 3**: Create server package files (3 files in one response)
- write_file(server/package.json)
- write_file(server/tsconfig.json)
- write_file(server/src/lib/db.ts)

**Iteration 4**: Create ALL route files (N files in one response, where N = number of resources)
- write_file(server/src/routes/users.ts)
- write_file(server/src/routes/articles.ts)
- write_file(server/src/routes/comments.ts)
- ... (all other routes)
**DO NOT create routes one at a time!**

**Iteration 5**: Create server entry point
- write_file(server/src/index.ts)

**Iteration 6**: Create MCP package (5 files in one response)
- write_file(mcp/pyproject.toml)
- write_file(mcp/src/[app]_mcp/__init__.py)
- write_file(mcp/src/[app]_mcp/server.py)
- write_file(mcp/src/[app]_mcp/client.py)
- write_file(mcp/README.md)

**Iteration 7**: Create documentation (2 files in one response)
- write_file(API_DOCUMENTATION.md)
- write_file(README.md)

**Iteration 8**: Create seed database
- create_seed_database()

**Iteration 9+**: Validation loop
- validate_environment()
- If fails: read errors, fix files, re-validate
- Repeat until success

**Final iteration**: Complete
- complete_generation()

**Total expected: 7-12 iterations** (not 20-30!)

## Debugging Failed Validation:

When validate_environment fails, follow this process:
1. Read the error message carefully to identify the issue
2. Use read_file to inspect the actual contents of relevant files
3. Compare what's there vs what should be there
4. Fix using write_file
5. Re-validate

Examples:
- Error: "Cannot find module 'better-sqlite3'"
  → read_file("server/package.json") to see dependencies
  → Check if better-sqlite3 is in dependencies
  → If missing, add it and rewrite the file

- Error: "Type error in routes/books.ts"
  → read_file("server/src/routes/books.ts") to see the code
  → read_file("server/src/lib/db.ts") to check imports
  → Fix the type error and rewrite

CRITICAL: As soon as validate_environment returns success=true, you MUST call complete_generation immediately.
Do NOT make any additional changes after validation succeeds!
Do NOT try to add more features or improvements after validation passes!
If you want to improve something, do it BEFORE running validation, not after.

The moment you see "success": true from validate_environment, your next action must be complete_generation.
"""


class CodeGeneratorAgent(BaseAgent):
    """Agent that generates Fleet environment code from specification"""

    def __init__(self, llm: LLMClient, output_dir: str, port: int = 3002):
        self.output_dir = output_dir
        self.port = port
        self.generated_files = []
        self.specification = None  # Will be set during generate_code

        # Define tools for code generation
        tools = [
            {
                "name": "write_file",
                "description": "Write content to a file in the output directory",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path within output directory (e.g., 'src/index.ts')"
                        },
                        "content": {
                            "type": "string",
                            "description": "File content to write"
                        }
                    },
                    "required": ["path", "content"]
                }
            },
            {
                "name": "read_file",
                "description": """Read contents of a previously generated file.

Use this when:
- Validation fails and you need to inspect what's actually in a file
- You need to check if a dependency/import is present
- You want to verify the exact structure of a file you wrote many iterations ago
- Debugging cross-file consistency issues

Do NOT use this:
- Immediately after writing a file (it's fresh in your memory)
- Just to confirm something you're certain about

This tool gives you the ground truth of what's actually on disk, which is critical for debugging validation failures.""",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path within output directory (e.g., 'server/package.json')"
                        }
                    },
                    "required": ["path"]
                }
            },
            {
                "name": "create_seed_database",
                "description": "Create seed.db from schema.sql file",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "schema_path": {
                            "type": "string",
                            "description": "Path to schema.sql file (relative to output dir)"
                        },
                        "output_path": {
                            "type": "string",
                            "description": "Path where seed.db should be created"
                        }
                    },
                    "required": ["schema_path", "output_path"]
                }
            },
            {
                "name": "validate_environment",
                "description": """Run validation checks on the generated environment to ensure it works correctly.

This will:
1. Run 'pnpm install' to install all dependencies
2. Run 'pnpm build' to compile TypeScript and build the project
3. Start 'pnpm run dev' and check the health endpoint
4. Test all API endpoints against the specification (validates actual behavior matches spec)

Returns:
- success: true if all checks pass, false otherwise
- phase: which phase failed (install/build/dev/api-validation) if validation fails
- errors: error messages from stderr if any phase fails
- failed_tests: list of failed endpoint tests (if api-validation fails)
- stdout: full output for debugging
- message: human-readable description of what happened

You should call this tool AFTER creating all files and the seed database, but BEFORE calling complete_generation.
If validation fails, carefully read the error messages, identify which files have issues, and fix them.
Then run validate_environment again. Repeat until validation succeeds.

IMPORTANT: Do not call complete_generation until validate_environment returns success=true!""",
                "input_schema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            {
                "name": "complete_generation",
                "description": "Signal that code generation is complete and validated. Only call this AFTER validate_environment succeeds!",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Summary of what was generated"
                        }
                    },
                    "required": ["summary"]
                }
            }
        ]

        super().__init__(
            llm=llm,
            tools=tools,
            tool_executor=self._execute_tool,
            system_prompt=CODE_GENERATION_SYSTEM_PROMPT,
            max_iterations=50  # Increased to allow for validation + fix iterations + buffer
        )

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute code generation tools"""
        if tool_name == "write_file":
            return self._write_file(tool_input)
        elif tool_name == "read_file":
            return self._read_file(tool_input)
        elif tool_name == "create_seed_database":
            return self._create_seed_database(tool_input)
        elif tool_name == "validate_environment":
            return self._validate_environment(tool_input)
        elif tool_name == "complete_generation":
            return {
                "complete": True,
                "summary": tool_input.get("summary", ""),
                "generated_files": self.generated_files
            }
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Write a file to the output directory"""
        rel_path = params.get("path")
        content = params.get("content")

        # Create full path
        full_path = os.path.join(self.output_dir, rel_path)

        # Create directory if needed
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Write file
        with open(full_path, 'w') as f:
            f.write(content)

        self.generated_files.append(rel_path)

        # Return compact result (don't echo content or verbose messages)
        return {
            "success": True,
            "file": rel_path  # Just the filename, not full path or message
        }

    def _read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read a previously generated file"""
        rel_path = params.get("path")
        full_path = os.path.join(self.output_dir, rel_path)

        # Check if file exists
        if not os.path.exists(full_path):
            return {
                "success": False,
                "error": f"File not found: {rel_path}",
                "message": f"❌ Cannot read {rel_path} - file doesn't exist. Did you create it yet?"
            }

        # Read the file
        try:
            with open(full_path, 'r') as f:
                content = f.read()

            line_count = len(content.split('\n'))

            # Return content (needed for debugging) but keep result compact
            return {
                "success": True,
                "file": rel_path,
                "content": content,  # Agent needs this to inspect files
                "lines": line_count
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "message": f"❌ Failed to read {rel_path}: {str(e)}"
            }

    def _create_seed_database(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create seed database from schema SQL"""
        import sqlite3

        schema_path = os.path.join(self.output_dir, params.get("schema_path"))
        output_path = os.path.join(self.output_dir, params.get("output_path"))

        # Read schema
        with open(schema_path, 'r') as f:
            schema_sql = f.read()

        # Create database directory if needed
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Create database
        conn = sqlite3.connect(output_path)

        # Enable WAL mode and foreign keys
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")

        # Execute schema
        conn.executescript(schema_sql)
        conn.commit()
        conn.close()

        # Compact result
        return {
            "success": True,
            "db": params.get('output_path')
        }

    def _validate_environment(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Run validation checks on the generated environment"""
        import subprocess
        import time
        import signal

        # Step 0: Auto-fix workspace structure (only if already installed)
        print("🔍 Ensuring clean workspace state...")
        node_modules_path = os.path.join(self.output_dir, "node_modules")

        # Only check for workspace issues if node_modules already exists
        # (fresh installs don't need this check)
        if os.path.exists(node_modules_path):
            try:
                # Check if workspace is recognized
                result = subprocess.run(
                    ["pnpm", "list", "--depth", "0"],
                    cwd=self.output_dir,
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if "server" not in result.stdout:
                    print("⚠️  Workspace cache issue detected - cleaning and reinstalling...")

                    # Auto-fix: Delete lockfile and node_modules
                    import shutil
                    lockfile = os.path.join(self.output_dir, "pnpm-lock.yaml")
                    node_modules = os.path.join(self.output_dir, "node_modules")
                    server_nm = os.path.join(self.output_dir, "server", "node_modules")

                    for path in [lockfile, node_modules, server_nm]:
                        if os.path.exists(path):
                            if os.path.isfile(path):
                                os.remove(path)
                            else:
                                shutil.rmtree(path)

                    print("   Cleaned stale workspace cache")

                    # Force fresh install with proper process management
                    proc = None
                    try:
                        proc = subprocess.Popen(
                            ["pnpm", "install", "--force"],
                            cwd=self.output_dir,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True
                        )

                        # Wait with timeout
                        stdout, stderr = proc.communicate(timeout=120)

                        if proc.returncode != 0:
                            return {
                                "success": False,
                                "phase": "workspace-fix",
                                "errors": stderr,
                                "stdout": stdout,
                                "message": "❌ Failed to fix workspace after cleaning cache."
                            }

                        print("   ✓ Workspace rebuilt successfully")

                    except subprocess.TimeoutExpired:
                        # Kill the process on timeout
                        if proc:
                            proc.kill()
                            proc.wait()
                        print("   ⚠️  Workspace reinstall timed out after 120s")
                        return {
                            "success": False,
                            "phase": "workspace-fix",
                            "errors": "pnpm install --force timed out after 120 seconds",
                            "stdout": "",
                            "message": "❌ Workspace reinstall timed out. Try cleaning pnpm cache: pnpm store prune"
                        }

            except Exception as e:
                print(f"⚠️  Warning: Workspace auto-fix failed: {e}")
        else:
            print("✅ Fresh install - skipping workspace check")

        print("✅ Workspace ready")

        # Step 1: pnpm install
        print("🔍 Running pnpm install...")
        try:
            result = subprocess.run(
                ["pnpm", "install"],
                cwd=self.output_dir,
                capture_output=True,
                text=True,
                timeout=120
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "phase": "install",
                    "errors": result.stderr,
                    "stdout": result.stdout,
                    "message": "❌ pnpm install failed. Check the error messages and fix package.json or dependencies."
                }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "phase": "install",
                "errors": "Command timed out after 120 seconds",
                "stdout": "",
                "message": "❌ pnpm install timed out."
            }
        except Exception as e:
            return {
                "success": False,
                "phase": "install",
                "errors": str(e),
                "stdout": "",
                "message": f"❌ pnpm install failed with exception: {str(e)}"
            }

        print("✅ pnpm install succeeded")

        # Step 2: pnpm build
        print("🔍 Running pnpm build...")
        try:
            result = subprocess.run(
                ["pnpm", "build"],
                cwd=self.output_dir,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                return {
                    "success": False,
                    "phase": "build",
                    "errors": result.stderr,
                    "stdout": result.stdout,
                    "message": "❌ pnpm build failed. Check TypeScript errors and fix the code."
                }
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "phase": "build",
                "errors": "Command timed out after 60 seconds",
                "stdout": "",
                "message": "❌ pnpm build timed out."
            }
        except Exception as e:
            return {
                "success": False,
                "phase": "build",
                "errors": str(e),
                "stdout": "",
                "message": f"❌ pnpm build failed with exception: {str(e)}"
            }

        print("✅ pnpm build succeeded")

        # Step 3: Start dev server and check health
        print("🔍 Starting dev server and checking health endpoint...")
        proc = None
        try:
            # Start the dev server in background
            proc = subprocess.Popen(
                ["pnpm", "run", "dev"],
                cwd=self.output_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                preexec_fn=os.setsid if hasattr(os, 'setsid') else None
            )

            # Wait for server to start
            time.sleep(8)  # Give it more time to start both server and MCP

            # Check if process is still running
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()

                # Combine stdout and stderr for better error visibility
                combined_output = f"STDOUT:\n{stdout}\n\nSTDERR:\n{stderr}"

                return {
                    "success": False,
                    "phase": "dev",
                    "errors": combined_output,
                    "stdout": stdout,
                    "stderr": stderr,
                    "message": "❌ Server process exited immediately. Check for runtime errors in stdout/stderr."
                }

            # Try to hit the health endpoint
            try:
                import urllib.request
                health_url = f"http://localhost:{self.port}/health"
                req = urllib.request.Request(health_url)
                with urllib.request.urlopen(req, timeout=3) as response:
                    if response.status != 200:
                        return {
                            "success": False,
                            "phase": "dev",
                            "errors": f"Health check returned status {response.status}",
                            "stdout": "",
                            "message": f"❌ Health check failed with status {response.status}"
                        }
            except Exception as e:
                # Try to capture any output from the process before reporting failure
                try:
                    # Process is still running, so peek at output (non-blocking)
                    import select
                    stdout_data = ""
                    stderr_data = ""
                    if proc.stdout and select.select([proc.stdout], [], [], 0)[0]:
                        stdout_data = proc.stdout.read()
                    if proc.stderr and select.select([proc.stderr], [], [], 0)[0]:
                        stderr_data = proc.stderr.read()

                    error_context = f"Health check failed: {str(e)}\n\nProcess output:\nSTDOUT: {stdout_data}\nSTDERR: {stderr_data}"
                except:
                    error_context = str(e)

                return {
                    "success": False,
                    "phase": "dev",
                    "errors": error_context,
                    "stdout": "",
                    "message": f"❌ Failed to connect to health endpoint: {str(e)}"
                }

            print("✅ Health check passed")

            # Step 4: Validate API endpoints against specification
            if self.specification:
                print("🔍 Validating API endpoints against specification...")
                spec_validation = self._validate_api_endpoints()

                if not spec_validation['success']:
                    # Print detailed failure info to console
                    print(f"\n❌ API Validation Failed: {spec_validation.get('summary', 'See errors')}")
                    print(f"   Passed: {spec_validation.get('passed', 0)}, Failed: {spec_validation.get('failed', 0)}")
                    print("\n   Failed endpoints:")
                    for test in spec_validation.get('failed_tests', []):
                        print(f"     - {test.get('endpoint')}: {test.get('message')}")
                    print()

                    return {
                        "success": False,
                        "phase": "api-validation",
                        "errors": spec_validation.get('errors', 'API validation failed'),
                        "failed_tests": spec_validation.get('failed_tests', []),
                        "passed_count": spec_validation.get('passed', 0),
                        "failed_count": spec_validation.get('failed', 0),
                        "stdout": "",
                        "message": f"❌ API validation failed: {spec_validation.get('summary', 'See errors')}"
                    }

                print(f"✅ API validation passed ({spec_validation.get('passed', 0)} tests)")

            # Compact success result (errors are verbose because agent needs them to debug)
            return {
                "success": True,
                "validated": True
            }

        except Exception as e:
            return {
                "success": False,
                "phase": "dev",
                "errors": str(e),
                "stdout": "",
                "message": f"❌ Validation failed with exception: {str(e)}"
            }
        finally:
            # Clean up: kill the dev server process
            if proc is not None:
                try:
                    if hasattr(os, 'killpg'):
                        # Kill the process group (to kill mprocs and all children)
                        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    else:
                        proc.terminate()
                    proc.wait(timeout=5)
                except Exception:
                    # Force kill if needed
                    try:
                        if hasattr(os, 'killpg'):
                            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                        else:
                            proc.kill()
                    except Exception:
                        pass

    def _validate_api_endpoints(self) -> Dict[str, Any]:
        """Validate API endpoints against specification"""
        import urllib.request
        import urllib.error
        import json as json_module

        if not self.specification:
            return {"success": True, "message": "No specification to validate against"}

        endpoints = self.specification.get('endpoints', [])
        if not endpoints:
            return {"success": True, "message": "No endpoints in specification"}

        passed_tests = []
        failed_tests = []
        base_url = f"http://localhost:{self.port}"

        # Test each endpoint
        for endpoint in endpoints:
            method = endpoint.get('method', 'GET').upper()
            path = endpoint.get('path', '')

            # Skip authentication-required endpoints for now (would need token)
            if endpoint.get('auth_required') and method != 'GET':
                continue

            try:
                # Only test GET endpoints in basic validation
                # (POST/PUT/DELETE would require valid payloads and may modify data)
                if method == 'GET':
                    url = base_url + path

                    # Replace path parameters with placeholder values
                    # Handles both {param} (OpenAPI) and :param (Express) formats
                    import re
                    url = re.sub(r'\{[^}]+\}|:[a-zA-Z_]+', '1', url)

                    try:
                        req = urllib.request.Request(url, method='GET')
                        with urllib.request.urlopen(req, timeout=3) as response:
                            status = response.status

                            # Accept 200 (success) or 404 (resource doesn't exist, but endpoint works)
                            # Reject 500 (server error)
                            if status in [200, 404]:
                                # Try to parse JSON response
                                try:
                                    body = response.read().decode('utf-8')
                                    json_module.loads(body)
                                    passed_tests.append({
                                        "endpoint": f"{method} {path}",
                                        "status": "✓",
                                        "message": f"Returns {status} with valid JSON"
                                    })
                                except json_module.JSONDecodeError:
                                    failed_tests.append({
                                        "endpoint": f"{method} {path}",
                                        "status": "✗",
                                        "message": f"Returns {status} but invalid JSON"
                                    })
                            else:
                                failed_tests.append({
                                    "endpoint": f"{method} {path}",
                                    "status": "✗",
                                    "message": f"Unexpected status code: {status}"
                                })

                    except urllib.error.HTTPError as e:
                        # These status codes mean the endpoint exists and is working:
                        # 400 = Bad Request (missing required params - endpoint exists)
                        # 401 = Unauthorized (needs auth - endpoint exists)
                        # 403 = Forbidden (needs different role - endpoint exists)
                        # 404 = Not Found (resource doesn't exist, but route works)
                        if e.code in [400, 401, 403, 404]:
                            passed_tests.append({
                                "endpoint": f"{method} {path}",
                                "status": "✓",
                                "message": f"Endpoint exists (returned {e.code})"
                            })
                        else:
                            failed_tests.append({
                                "endpoint": f"{method} {path}",
                                "status": "✗",
                                "message": f"HTTP error {e.code}: {str(e)}"
                            })

            except Exception as e:
                failed_tests.append({
                    "endpoint": f"{method} {path}",
                    "status": "✗",
                    "message": f"Test failed: {str(e)}"
                })

        # Summary
        total = len(passed_tests) + len(failed_tests)

        if failed_tests:
            error_summary = "\n".join([
                f"  {test['endpoint']}: {test['message']}"
                for test in failed_tests
            ])
            return {
                "success": False,
                "passed": len(passed_tests),
                "failed": len(failed_tests),
                "total": total,
                "failed_tests": failed_tests,
                "errors": error_summary,
                "summary": f"{len(failed_tests)}/{total} tests failed"
            }
        else:
            return {
                "success": True,
                "passed": len(passed_tests),
                "failed": 0,
                "total": total,
                "message": f"All {len(passed_tests)} endpoint tests passed"
            }

    def generate_code(self, specification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Fleet environment code from specification

        Args:
            specification: The API specification from SpecificationAgent
                          May include 'business_requirements' section from BusinessRequirementAgent

        Returns:
            Generation results including file list
        """
        # Store specification for validation
        self.specification = specification

        # Format specification for the prompt
        spec_json = json.dumps(specification, indent=2)

        # Check if this is an enriched specification with business requirements
        has_business_requirements = 'business_requirements' in specification

        # Build the prompt with appropriate emphasis on business requirements
        if has_business_requirements:
            business_req_intro = """
IMPORTANT: This specification includes BUSINESS REQUIREMENTS that define how the API must behave.
You MUST implement all the constraints, authentication, authorization, state transitions, and validation rules
defined in the `business_requirements` section. These are not optional - they are core to the API's correctness.

Pay special attention to:
- `auth_config`: How authentication should work
- `roles`: The role hierarchy and permissions
- `endpoint_auth`: Which roles can access which endpoints
- `state_transitions`: Valid state changes for entities
- `validation_rules`: Business logic validations to enforce
- `pre_conditions`: Checks that must pass before operations

"""
        else:
            business_req_intro = ""

        initial_prompt = f"""Generate a complete Fleet environment based on this specification:
{business_req_intro}

{spec_json}

IMPORTANT: The generated environment must run on port {self.port}.
- Set PORT={self.port} in mprocs.yaml server env
- Set API_BASE_URL=http://localhost:{self.port} in mprocs.yaml mcp env
- Document port {self.port} in README.md
- Server should use process.env.PORT with fallback to {self.port}

Follow the workflow described in the system prompt:

1. Generate all necessary files using write_file:
   - Configuration files (.gitignore, .dockerignore, .npmrc, .github/workflows/deploy.yml)
   - Root configs (pnpm-workspace.yaml, package.json, mprocs.yaml, Dockerfile)
   - Data layer (data/schema.sql)
   - Server package (server/package.json, tsconfig.json, src/lib/db.ts, src/routes/, src/index.ts)
   - MCP package (mcp/pyproject.toml, src/{{app_name}}_mcp/server.py, client.py, __init__.py)
   - Documentation (README.md, API_DOCUMENTATION.md, mcp/README.md)

2. Call create_seed_database to create the seed.db file

3. Call validate_environment to test the generated environment
   - This will run: pnpm install, pnpm build, pnpm run dev
   - Check the health endpoint
   - Test all API endpoints against the specification (validates actual behavior!)

4. If validation fails:
   - Read the error messages carefully (including failed endpoint tests)
   - Use read_file to inspect the problematic files
   - Identify what needs to be fixed (TypeScript errors, missing routes, wrong responses)
   - Use write_file to fix the problems
   - Call validate_environment again

5. Repeat step 4 until validation succeeds

6. Only after validation returns success=true, call complete_generation

Remember: The validation will catch TypeScript errors, missing dependencies, incorrect configs, AND verify your API endpoints actually work as specified.
Use those error messages to guide your fixes. You have all the context needed to debug and fix issues."""

        result = self.run(initial_prompt)

        return {
            "success": result.get("success", False),
            "generated_files": self.generated_files,
            "output_dir": self.output_dir
        }
