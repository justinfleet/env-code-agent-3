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

## Fleet Requirements (CRITICAL):
1. **Database Configuration**:
   - SQLite with WAL mode enabled
   - INTEGER AUTOINCREMENT for primary keys
   - NO CHECK constraints in schema.sql (use validation in code)
   - Foreign keys enabled
   - seed.db ready for immediate use (contains schema + initial data)
   - Uses current.sqlite at runtime (auto-copied from seed.db if not exists)
   - Database path precedence: DATABASE_PATH → ENV_DB_DIR → ./data/current.sqlite

2. **Server (HTTP API)**:
   - HTTP server in server/ directory
   - Technology: TypeScript + Express (default), but other stacks acceptable:
     - Alternative: Python + FastAPI, Go + stdlib, Bun + Elysia, etc.
   - Proper error handling (try/catch or equivalent)
   - CORS enabled for cross-origin requests
   - Real SQL queries (no mocks!)
   - Routes/endpoints organized by resource
   - SQLite database access via:
     - Node.js: better-sqlite3 (with or without Drizzle ORM)
     - Python: sqlite3 module
     - Go: database/sql
     - Other: any SQLite driver

3. **MCP Server (Python)**:
   - Python-based MCP server in mcp/ directory
   - Uses uv for dependency management (pyproject.toml)
   - Implements Model Context Protocol for LLM interaction
   - Fetches data from local server API (http://localhost:3001/api)
   - Environment variable: APP_ENV=local (for local dev) or production
     - APP_ENV=local → fetches from http://localhost:3001/api
     - APP_ENV=production → fetches from production API URL
   - Basic tools: process_data, execute_query, load_* functions

4. **Monorepo Structure (pnpm workspace)**:
   - Root pnpm-workspace.yaml defining ONLY Node.js packages (server)
   - Do NOT include mcp/ in pnpm-workspace.yaml (it's Python, not Node.js)
   - Do NOT include data/ in pnpm-workspace.yaml (it's just database files)
   - Root package.json with workspace scripts and "packageManager": "pnpm@9.15.1"
   - server/ package with its own package.json
   - mcp/ package with Python dependencies (pyproject.toml, NOT package.json)
   - mprocs.yaml for running all services together

5. **Optional Components (based on API complexity)**:
   - Client (SvelteKit): Only if cloning a full-stack app with UI
   - Meilisearch: Only if API has search/full-text search functionality
   - Image handling: Only if API serves/manages images (S3 integration)
   - Additional services: Based on what the API exploration discovers
   - For simple APIs: Just generate server + mcp (no client needed)

6. **File Structure**:
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

7. **Database Path Handling (CRITICAL)**:
   In server/src/lib/db.ts, implement this precedence:
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
     // 3. Default: ./data/current.sqlite
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
   ```

## Available Tools:
- write_file: Write content to a file in the output directory
- create_seed_database: Create seed.db from schema.sql
- complete_generation: Signal when all files are generated

## Code Style:
- **Default Stack**: TypeScript + Express for server (well-tested, good ecosystem)
  - Note: Other stacks (Python, Go, Rust) are valid but not currently supported by this generator
- Use TypeScript with proper types for server code
- Use Python 3.11+ for MCP server
- Use better-sqlite3 for database (Node.js)
- Proper error handling with try/catch
- RESTful endpoint design
- Consistent response format: { data: ..., error: ... }

## Steps (Follow in Order):
1. Create pnpm-workspace.yaml
2. Create root package.json with workspace config
3. Create mprocs.yaml with server and mcp processes
4. Create Dockerfile for production
5. Create server/package.json with dependencies
6. Create server/tsconfig.json
7. Create data/schema.sql with proper SQLite schema (NO CHECK constraints)
8. Create server/src/lib/db.ts with DATABASE_PATH precedence logic
9. Create server/src/routes/[resource].ts for each resource
10. Create server/src/index.ts as main server
11. Create mcp/pyproject.toml with uv dependencies
12. Create mcp/src/[app]_mcp/server.py (basic MCP server)
13. Create mcp/src/[app]_mcp/client.py (API client)
14. Create mcp/README.md with MCP setup instructions
15. Create root README.md with full setup instructions
16. Create seed database from schema
17. Call complete_generation when done

Be thorough and ensure all files are production-ready and Fleet-compliant!
"""


class CodeGeneratorAgent(BaseAgent):
    """Agent that generates Fleet environment code from specification"""

    def __init__(self, llm: LLMClient, output_dir: str):
        self.output_dir = output_dir
        self.generated_files = []

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
                "name": "complete_generation",
                "description": "Signal that code generation is complete",
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
            max_iterations=25  # Reduced from 50 - typically completes in 10-15 iterations
        )

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute code generation tools"""
        if tool_name == "write_file":
            return self._write_file(tool_input)
        elif tool_name == "create_seed_database":
            return self._create_seed_database(tool_input)
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

        return {
            "success": True,
            "message": f"File written: {rel_path}",
            "path": full_path
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

        return {
            "success": True,
            "message": f"Database created: {params.get('output_path')}"
        }

    def generate_code(self, specification: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate Fleet environment code from specification

        Args:
            specification: The API specification from SpecificationAgent

        Returns:
            Generation results including file list
        """
        # Format specification for the prompt
        spec_json = json.dumps(specification, indent=2)

        initial_prompt = f"""Generate a complete Fleet environment based on this specification:

{spec_json}

Create all necessary files following Fleet standards. You MUST generate ALL of these files:

**Root Configuration:**
1. pnpm-workspace.yaml - Define packages: ["server"] (ONLY server, NOT mcp!)
2. package.json - Root package with:
   - "packageManager": "pnpm@9.15.1"
   - "dev": "mprocs" script
   - engines: node "^20.19.4", pnpm "^9.15.1"
3. mprocs.yaml - Multi-process config for server + mcp
4. Dockerfile - Production deployment configuration
5. README.md - Complete setup instructions with pnpm run dev

**Data Layer:**
6. data/schema.sql - Database schema (NO CHECK constraints!)
7. Create seed.db from schema (use create_seed_database tool)

**Server Package (server/):**
8. server/package.json - Dependencies: express, better-sqlite3, cors, typescript, tsx
9. server/tsconfig.json - TypeScript configuration
10. server/src/lib/db.ts - Database connection with DATABASE_PATH→ENV_DB_DIR→default precedence
11. server/src/routes/[resource].ts - One file per resource
12. server/src/index.ts - Main Express server

**MCP Package (mcp/):**
13. mcp/pyproject.toml - Python dependencies with uv (mcp, httpx, etc.)
14. mcp/src/[app_name]_mcp/__init__.py - Package init
15. mcp/src/[app_name]_mcp/server.py - MCP server with basic tools
16. mcp/src/[app_name]_mcp/client.py - API client for local server
17. mcp/README.md - MCP setup and usage instructions

CRITICAL Requirements:
- pnpm-workspace.yaml MUST ONLY include ["server"], NOT ["server", "mcp"] or ["server", "data"]
- mcp/ is a Python package (pyproject.toml), NOT a Node.js package
- data/ is NOT a workspace package (no package.json)
- Root package.json MUST have "packageManager": "pnpm@9.15.1"
- Root package.json MUST have engines: node "^20.19.4", pnpm "^9.15.1"
- server/src/lib/db.ts MUST use current.sqlite (not seed.db directly)
- MUST implement DATABASE_PATH → ENV_DB_DIR → default precedence
- MUST auto-copy seed.db to current.sqlite if not exists
- mprocs.yaml MUST run both server and mcp processes
- mprocs.yaml MUST set APP_ENV=local for MCP process (not RAMP_ENV)
- Root package.json MUST have "dev": "mprocs" script

Use write_file for each file, then create_seed_database, then complete_generation.

Generate production-ready code with proper error handling!"""

        result = self.run(initial_prompt)

        return {
            "success": result.get("success", False),
            "generated_files": self.generated_files,
            "output_dir": self.output_dir
        }
