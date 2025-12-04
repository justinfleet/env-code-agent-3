"""
Business Requirement Agent - analyzes natural language business constraints
and determines what changes are needed at both schema and application layers.
"""

from ..core.base_agent import BaseAgent
from ..core.llm_client import LLMClient
from typing import Dict, Any
import json


BUSINESS_REQUIREMENT_SYSTEM_PROMPT = """You are an expert at analyzing business requirements and determining how to implement them in a web API.

## Your Task:
Given an API specification and business constraints in natural language, analyze each constraint and determine:
1. **Schema-layer changes** - New fields, tables, relationships in the database
2. **Application-layer logic** - Validation, authorization, state management in code

## Understanding the Two Layers:

### Schema Layer (Database)
Things that require database changes:
- Adding `role` field to users table
- Adding `user_id` foreign key to orders table
- Creating new junction tables for relationships
- Adding status fields for state machines

### Application Layer (Code)
Things that require code logic:
- Authentication middleware (JWT verification)
- Authorization checks (role-based access control)
- Ownership validation (user can only see their own orders)
- State transition logic (order placed → pet becomes pending)
- Pre-condition checks (cannot delete pet with active orders)
- Data validation (quantity must be 1)

## Example Analysis:

**Constraint:** "Customers can only view their own orders"

**Schema Layer:**
- Orders table needs `user_id` field (foreign key to users)

**Application Layer:**
- GET /store/order/{id} must verify: token.user_id == order.user_id
- Exception: store_owner and admin can view any order
- Return 403 if ownership check fails

---

**Constraint:** "Only store_owner or admin can add pets"

**Schema Layer:**
- Users table needs `role` field (TEXT: customer, store_owner, admin)

**Application Layer:**
- Auth middleware extracts role from JWT
- POST /pet checks: if role not in ['store_owner', 'admin'] → 403
- Same for PUT /pet and DELETE /pet

---

**Constraint:** "Placing an order changes pet status to pending"

**Schema Layer:**
- (Assuming pet.status already exists) No schema change needed

**Application Layer:**
- POST /store/order handler must:
  1. Validate pet status == 'available'
  2. Create order record
  3. Update pet.status = 'pending'
  4. Use transaction for atomicity

---

**Constraint:** "Cannot delete a pet with active orders"

**Schema Layer:**
- No schema change (relationship already exists via order.pet_id)

**Application Layer:**
- DELETE /pet/{id} must first query:
  SELECT COUNT(*) FROM orders WHERE pet_id = ? AND status IN ('placed', 'approved')
- If count > 0, return 400 "Cannot delete pet with active orders"

## Output Format:

Use the output_requirements tool to provide the complete analysis with these sections:

### 1. schema_changes
Database-level changes needed:
```json
{
  "schema_changes": {
    "users": {
      "add_fields": [
        {"name": "role", "type": "TEXT", "default": "customer", "reason": "Role-based access control"}
      ]
    },
    "orders": {
      "add_fields": [
        {"name": "user_id", "type": "INTEGER", "foreign_key": "users.id", "reason": "Track order ownership"}
      ]
    }
  }
}
```

### 2. auth_config
Authentication setup:
```json
{
  "auth_config": {
    "enabled": true,
    "method": "jwt",
    "secret_env_var": "JWT_SECRET",
    "token_expiry": "24h",
    "token_payload": ["user_id", "username", "role"],
    "password_hashing": "bcrypt",
    "login_endpoint": "POST /user/login",
    "register_endpoint": "POST /user"
  }
}
```

### 3. roles
Role definitions:
```json
{
  "roles": {
    "guest": {
      "description": "Unauthenticated user",
      "permissions": ["browse_pets", "view_inventory"]
    },
    "customer": {
      "description": "Registered user",
      "permissions": ["place_orders", "view_own_orders", "cancel_own_placed_orders", "manage_own_profile"]
    },
    "store_owner": {
      "description": "Store employee",
      "permissions": ["manage_pets", "view_all_orders", "approve_orders", "deliver_orders"]
    },
    "admin": {
      "description": "System administrator",
      "permissions": ["all", "manage_users", "relist_sold_pets"]
    }
  }
}
```

### 4. endpoint_auth
Authorization rules per endpoint:
```json
{
  "endpoint_auth": [
    {
      "method": "POST",
      "path": "/pet",
      "auth_required": true,
      "allowed_roles": ["store_owner", "admin"],
      "reason": "Only store_owner or admin can add pets"
    },
    {
      "method": "GET",
      "path": "/store/order/:orderId",
      "auth_required": true,
      "ownership_check": {
        "resource": "order",
        "owner_field": "user_id",
        "bypass_roles": ["store_owner", "admin"]
      },
      "reason": "Customers can only view their own orders"
    }
  ]
}
```

### 5. state_transitions
Automatic state changes (application logic):
```json
{
  "state_transitions": [
    {
      "trigger": {"action": "create", "resource": "order"},
      "effect": {"resource": "pet", "field": "status", "value": "pending"},
      "condition": "pet.status == 'available'",
      "reason": "Placing an order changes pet status to pending"
    },
    {
      "trigger": {"action": "delete", "resource": "order", "when": "status == 'placed'"},
      "effect": {"resource": "pet", "field": "status", "value": "available"},
      "reason": "Cancelling order returns pet to available"
    },
    {
      "trigger": {"action": "update", "resource": "order", "when": "status becomes 'delivered'"},
      "effect": {"resource": "pet", "field": "status", "value": "sold"},
      "reason": "Delivering order marks pet as sold"
    }
  ]
}
```

### 6. validation_rules
Data validation (application logic):
```json
{
  "validation_rules": [
    {
      "endpoint": "POST /store/order",
      "validations": [
        {
          "field": "petId",
          "check": "pet.status == 'available'",
          "error": "Pet is not available for purchase",
          "status_code": 400
        },
        {
          "field": "quantity",
          "check": "value == 1",
          "error": "Quantity must be 1 for live animals",
          "status_code": 400
        }
      ]
    }
  ]
}
```

### 7. pre_conditions
Checks before allowing operations:
```json
{
  "pre_conditions": [
    {
      "endpoint": "DELETE /pet/:petId",
      "checks": [
        {
          "query": "SELECT COUNT(*) FROM orders WHERE pet_id = ? AND status IN ('placed', 'approved')",
          "condition": "count == 0",
          "error": "Cannot delete pet with active orders",
          "status_code": 400
        }
      ]
    },
    {
      "endpoint": "DELETE /user/:username",
      "checks": [
        {
          "query": "SELECT COUNT(*) FROM orders WHERE user_id = ? AND status IN ('placed', 'approved')",
          "condition": "count == 0",
          "error": "Cannot delete user with active orders",
          "status_code": 400
        }
      ]
    }
  ]
}
```

## Important Guidelines:
1. **Separate concerns** - Clearly distinguish schema vs application layer
2. **Be specific** - Include exact field names, error messages, status codes
3. **Think about transactions** - State transitions often need atomicity
4. **Consider edge cases** - What happens on failure? Rollback?
5. **Role hierarchy** - Admin typically inherits all permissions
6. **Ownership patterns** - Common pattern: user owns resource, admins bypass
"""

WORKFLOW_GENERATION_SYSTEM_PROMPT = """You are an expert at creating executable API test workflows.

## Your Task:
Given business requirements (auth, roles, state transitions, validation rules, pre-conditions),
generate comprehensive test workflows that verify the API implementation is correct.

## What are Workflows?
Workflows are executable test scenarios that verify both API functionality AND business rule enforcement.
They serve as:
1. **Validation tests** - Run against generated code to verify correctness
2. **Living documentation** - Show how the API should be used
3. **Business rule coverage** - Ensure constraints are actually enforced

## Workflow Structure:
Each workflow has:
- `name`: Unique identifier (snake_case)
- `description`: What this workflow tests
- `category`: "happy_path", "authorization", "validation", "state_transition", or "error_handling"
- `steps`: Ordered list of API calls with expectations

## Step Structure:
```yaml
- action: "POST /user/login"           # HTTP method + path
  as_role: "customer"                   # Which test user role to use (optional)
  description: "Login as customer"      # What this step does
  body:                                 # Request body (for POST/PUT)
    username: "{{customer_username}}"
    password: "{{customer_password}}"
  expect:
    status: 200                         # Expected HTTP status
    body_contains:                      # Partial body matching
      token: "{{save:auth_token}}"      # Save value for later use

- action: "GET /pet/{{pet_id}}"        # Use saved variables
  headers:
    Authorization: "Bearer {{auth_token}}"
  expect:
    status: 200
    body_contains:
      status: "available"
```

## Variable Syntax:
- `{{variable}}` - Use a previously saved variable
- `{{save:variable_name}}` - Save this value from response
- `{{customer_username}}` - Built-in test user credentials
- `{{store_owner_username}}` - Built-in test user credentials
- `{{admin_username}}` - Built-in test user credentials
- `{{test_password}}` - Built-in password for all test users
- `{{available_pet_id}}` - Built-in: ID of an available pet from seed data
- `{{pending_pet_id}}` - Built-in: ID of a pending pet from seed data
- `{{sold_pet_id}}` - Built-in: ID of a sold pet from seed data

## Required Workflow Categories:

### 1. Happy Path Workflows
Normal successful operations:
- Customer login and browse pets
- Customer places order successfully
- Store owner approves and delivers order
- Full purchase lifecycle

### 2. Authorization Workflows
Role-based access control tests:
- Customer cannot create/edit/delete pets (403)
- Customer cannot approve orders (403)
- Customer cannot view others' orders (403)
- Guest cannot place orders (401)

### 3. Validation Workflows
Business rule enforcement:
- Cannot order unavailable pet (400)
- Cannot order pet with active order (400)
- Quantity must be 1 (400)

### 4. State Transition Workflows
Verify state machines work correctly:
- Order creation changes pet to pending
- Order delivery changes pet to sold
- Order cancellation returns pet to available
- Only admin can relist sold pets

### 5. Pre-condition Workflows
Pre-condition check enforcement:
- Cannot delete pet with active orders (400)
- Cannot delete user with active orders (400)
- Cannot modify delivered orders (400)

## Output Format:
Use the `output_workflows` tool with a YAML structure containing all workflows.
Generate at least 8-12 workflows covering all categories.
"""


class BusinessRequirementAgent(BaseAgent):
    """Agent that analyzes business constraints and determines implementation requirements"""

    # Tools for requirements analysis phase
    REQUIREMENTS_TOOLS = [
        {
            "name": "analyze_constraint",
            "description": "Analyze a single business constraint to understand what it requires",
            "input_schema": {
                "type": "object",
                "properties": {
                    "constraint": {
                        "type": "string",
                        "description": "The constraint text being analyzed"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["ordering", "pet_management", "user_management", "order_management", "inventory", "other"],
                        "description": "Category of this constraint"
                    },
                    "schema_impact": {
                        "type": "string",
                        "description": "What database schema changes are needed, if any"
                    },
                    "application_impact": {
                        "type": "string",
                        "description": "What application code logic is needed"
                    },
                    "affected_endpoints": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Which endpoints are affected (e.g., 'POST /pet', 'GET /store/order/:id')"
                    }
                },
                "required": ["constraint", "category", "application_impact"]
            }
        },
        {
            "name": "output_requirements",
            "description": "Output the complete business requirements specification with both schema and application layer requirements",
            "input_schema": {
                "type": "object",
                "properties": {
                    "requirements": {
                        "type": "object",
                        "description": "Complete requirements specification",
                        "properties": {
                            "schema_changes": {
                                "type": "object",
                                "description": "Database schema changes needed"
                            },
                            "auth_config": {
                                "type": "object",
                                "description": "Authentication configuration"
                            },
                            "roles": {
                                "type": "object",
                                "description": "Role definitions and permissions"
                            },
                            "endpoint_auth": {
                                "type": "array",
                                "description": "Authorization rules per endpoint"
                            },
                            "state_transitions": {
                                "type": "array",
                                "description": "Automatic state changes"
                            },
                            "validation_rules": {
                                "type": "array",
                                "description": "Data validation rules"
                            },
                            "pre_conditions": {
                                "type": "array",
                                "description": "Pre-condition checks before operations"
                            }
                        },
                        "required": ["schema_changes", "auth_config", "roles", "endpoint_auth"]
                    }
                },
                "required": ["requirements"]
            }
        }
    ]

    # Tools for workflow generation phase
    WORKFLOW_TOOLS = [
        {
            "name": "output_workflows",
            "description": "Output the complete set of validation workflows in YAML format",
            "input_schema": {
                "type": "object",
                "properties": {
                    "workflows": {
                        "type": "array",
                        "description": "List of workflow definitions",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {
                                    "type": "string",
                                    "description": "Unique workflow name (snake_case)"
                                },
                                "description": {
                                    "type": "string",
                                    "description": "What this workflow tests"
                                },
                                "category": {
                                    "type": "string",
                                    "enum": ["happy_path", "authorization", "validation", "state_transition", "error_handling"],
                                    "description": "Workflow category"
                                },
                                "steps": {
                                    "type": "array",
                                    "description": "Ordered list of test steps",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "action": {
                                                "type": "string",
                                                "description": "HTTP method + path (e.g., 'POST /user/login')"
                                            },
                                            "description": {
                                                "type": "string",
                                                "description": "What this step does"
                                            },
                                            "headers": {
                                                "type": "object",
                                                "description": "Request headers"
                                            },
                                            "body": {
                                                "type": "object",
                                                "description": "Request body for POST/PUT"
                                            },
                                            "expect": {
                                                "type": "object",
                                                "description": "Expected response",
                                                "properties": {
                                                    "status": {
                                                        "type": "integer",
                                                        "description": "Expected HTTP status code"
                                                    },
                                                    "body_contains": {
                                                        "type": "object",
                                                        "description": "Expected fields in response body"
                                                    }
                                                }
                                            }
                                        },
                                        "required": ["action", "expect"]
                                    }
                                }
                            },
                            "required": ["name", "description", "category", "steps"]
                        }
                    }
                },
                "required": ["workflows"]
            }
        }
    ]

    def __init__(self, llm: LLMClient):
        super().__init__(
            llm=llm,
            tools=self.REQUIREMENTS_TOOLS,
            tool_executor=self._execute_tool,
            system_prompt=BUSINESS_REQUIREMENT_SYSTEM_PROMPT,
            max_iterations=20
        )
        self.requirements = None
        self.workflows = None
        self.constraint_analyses = []

    def _execute_tool(self, tool_name: str, tool_input: Dict[str, Any]) -> Any:
        """Execute business requirement analysis tools"""
        if tool_name == "analyze_constraint":
            analysis = {
                "constraint": tool_input.get("constraint"),
                "category": tool_input.get("category"),
                "schema_impact": tool_input.get("schema_impact", "None"),
                "application_impact": tool_input.get("application_impact"),
                "affected_endpoints": tool_input.get("affected_endpoints", [])
            }
            self.constraint_analyses.append(analysis)

            # Format output for console
            constraint_preview = tool_input.get('constraint', '')[:60]
            if len(tool_input.get('constraint', '')) > 60:
                constraint_preview += '...'
            print(f"   📋 [{tool_input.get('category', 'other')}] {constraint_preview}")

            return {
                "success": True,
                "message": "Constraint analysis recorded"
            }

        elif tool_name == "output_requirements":
            requirements = tool_input.get("requirements")

            if not requirements:
                return {
                    "complete": False,
                    "success": False,
                    "error": "requirements parameter is required"
                }

            # Validate required sections
            required_sections = ["schema_changes", "auth_config", "roles", "endpoint_auth"]
            missing = [s for s in required_sections if s not in requirements]
            if missing:
                return {
                    "complete": False,
                    "success": False,
                    "error": f"Missing required sections: {missing}"
                }

            self.requirements = requirements
            return {
                "complete": True,
                "message": "✅ Business requirements specification created successfully"
            }

        elif tool_name == "output_workflows":
            workflows = tool_input.get("workflows")

            if not workflows:
                return {
                    "complete": False,
                    "success": False,
                    "error": "workflows parameter is required"
                }

            if not isinstance(workflows, list) or len(workflows) == 0:
                return {
                    "complete": False,
                    "success": False,
                    "error": "workflows must be a non-empty list"
                }

            # Validate each workflow has required fields
            for i, workflow in enumerate(workflows):
                required = ["name", "description", "category", "steps"]
                missing = [f for f in required if f not in workflow]
                if missing:
                    return {
                        "complete": False,
                        "success": False,
                        "error": f"Workflow {i+1} missing required fields: {missing}"
                    }

            self.workflows = workflows

            # Print summary
            categories = {}
            for w in workflows:
                cat = w.get('category', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1

            print(f"\n   ✅ Generated {len(workflows)} workflows:")
            for cat, count in sorted(categories.items()):
                print(f"      - {cat}: {count}")

            return {
                "complete": True,
                "message": f"✅ Generated {len(workflows)} validation workflows"
            }

        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def analyze_constraints(
        self,
        specification: Dict[str, Any],
        constraints: str
    ) -> Dict[str, Any]:
        """
        Analyze business constraints and create requirements specification.

        Args:
            specification: The base API specification (from SpecificationIngestionAgent)
            constraints: Natural language business constraints

        Returns:
            Requirements specification with schema and application layer changes
        """
        # Format the specification summary for the prompt
        spec_summary = self._summarize_spec(specification)

        initial_prompt = f"""Please analyze these business constraints and determine what changes are needed at both the schema layer (database) and application layer (code).

## Current API Specification Summary:
{spec_summary}

## Business Constraints (Natural Language):
{constraints}

## Your Task:

**Step 1: Analyze each constraint individually**
Use the analyze_constraint tool for each business rule to understand:
- What category it belongs to (ordering, pet_management, user_management, etc.)
- What schema changes it requires (new fields, tables)
- What application logic it requires (auth, validation, state transitions)
- Which endpoints it affects

**Step 2: Synthesize into requirements specification**
After analyzing all constraints, use output_requirements to provide:

1. **schema_changes** - What database changes are needed?
   - New fields on existing tables (e.g., role on users, user_id on orders)
   - New tables if needed
   - Foreign key relationships

2. **auth_config** - How should authentication work?
   - JWT configuration
   - Token payload (what claims to include)
   - Password hashing

3. **roles** - What roles exist and what can each do?
   - guest, customer, store_owner, admin
   - Permissions for each role

4. **endpoint_auth** - What authorization does each endpoint need?
   - Which endpoints require auth?
   - Which roles can access?
   - Ownership checks?

5. **state_transitions** - What automatic state changes occur?
   - Order created → pet.status becomes 'pending'
   - Order delivered → pet.status becomes 'sold'
   - Order cancelled → pet.status returns to 'available'

6. **validation_rules** - What data validations are needed?
   - Pet must be available to order
   - Quantity must be 1

7. **pre_conditions** - What checks before operations?
   - Cannot delete pet with active orders
   - Cannot delete user with active orders

Be thorough and specific - this specification will be used to generate actual working code.
"""

        print(f"\n{'='*70}")
        print(f"🔍 ANALYZING BUSINESS REQUIREMENTS")
        print(f"{'='*70}\n")

        # Show constraint preview
        constraint_lines = constraints.strip().split('\n')
        preview_lines = constraint_lines[:10]
        print("Constraints to analyze:")
        for line in preview_lines:
            if line.strip():
                print(f"  {line}")
        if len(constraint_lines) > 10:
            print(f"  ... and {len(constraint_lines) - 10} more lines")
        print()

        result = self.run(initial_prompt)

        if self.requirements:
            # Print summary
            print(f"\n✅ Business requirements analysis complete!")
            print(f"\n📊 Summary:")
            print(f"   Schema changes: {self._count_schema_changes()} field(s) to add")
            print(f"   Endpoint rules: {len(self.requirements.get('endpoint_auth', []))} endpoint(s) with auth")
            print(f"   State transitions: {len(self.requirements.get('state_transitions', []))} transition(s)")
            print(f"   Validation rules: {len(self.requirements.get('validation_rules', []))} rule(s)")
            print(f"   Pre-conditions: {len(self.requirements.get('pre_conditions', []))} check(s)")

            # Phase 2: Generate validation workflows
            print(f"\n{'='*70}")
            print(f"📋 GENERATING VALIDATION WORKFLOWS")
            print(f"{'='*70}\n")

            workflows = self._generate_workflows(specification)

            # Create enriched specification
            enriched_spec = self._apply_requirements(specification, self.requirements)

            # Add workflows to enriched spec
            if workflows:
                enriched_spec['workflows'] = workflows

            return {
                "success": True,
                "enriched_specification": enriched_spec,
                "requirements": self.requirements,
                "workflows": workflows,
                "constraint_analyses": self.constraint_analyses
            }
        else:
            return {
                "success": False,
                "error": "Failed to create requirements specification"
            }

    def _count_schema_changes(self) -> int:
        """Count total schema field changes"""
        count = 0
        for table_changes in self.requirements.get('schema_changes', {}).values():
            count += len(table_changes.get('add_fields', []))
        return count

    def _summarize_spec(self, spec: Dict[str, Any]) -> str:
        """Create a summary of the specification for the prompt"""
        lines = []

        lines.append(f"API Name: {spec.get('api_name', 'Unknown')}")
        lines.append(f"Base Path: {spec.get('base_path', '/')}")

        lines.append("\nEndpoints:")
        for endpoint in spec.get('endpoints', [])[:20]:  # Limit to first 20
            method = endpoint.get('method', 'GET')
            path = endpoint.get('path', '')
            desc = endpoint.get('description', '')[:50]
            lines.append(f"  - {method} {path}: {desc}")

        if len(spec.get('endpoints', [])) > 20:
            lines.append(f"  ... and {len(spec.get('endpoints', [])) - 20} more endpoints")

        lines.append("\nDatabase Tables:")
        for table in spec.get('database', {}).get('tables', []):
            table_name = table.get('name', '')
            fields = [f.get('name', '') for f in table.get('fields', [])]
            lines.append(f"  - {table_name}: {', '.join(fields[:8])}")
            if len(fields) > 8:
                lines.append(f"    ... and {len(fields) - 8} more fields")

        return '\n'.join(lines)

    def _apply_requirements(
        self,
        spec: Dict[str, Any],
        requirements: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply requirements to create enriched specification"""
        import copy
        enriched = copy.deepcopy(spec)

        # Store the full requirements
        enriched['business_requirements'] = requirements

        # Apply schema changes to database tables
        schema_changes = requirements.get('schema_changes', {})
        tables = enriched.get('database', {}).get('tables', [])

        for table_name, changes in schema_changes.items():
            # Find the table
            table = next((t for t in tables if t.get('name') == table_name), None)

            if table:
                # Add new fields
                for field in changes.get('add_fields', []):
                    # Check if field already exists
                    existing = [f for f in table.get('fields', []) if f.get('name') == field.get('name')]
                    if not existing:
                        new_field = {
                            'name': field.get('name'),
                            'type': field.get('type', 'TEXT'),
                            'constraints': ''
                        }
                        if field.get('default'):
                            new_field['default'] = field.get('default')
                        if field.get('foreign_key'):
                            new_field['foreign_key'] = field.get('foreign_key')
                        table['fields'].append(new_field)
                        print(f"   + Added field '{field.get('name')}' to '{table_name}'")
            else:
                # Table doesn't exist, might need to create it
                print(f"   ⚠️  Table '{table_name}' not found in schema")

        # Copy over application-layer requirements (used by code generator)
        enriched['auth_config'] = requirements.get('auth_config', {})
        enriched['roles'] = requirements.get('roles', {})
        enriched['endpoint_auth'] = requirements.get('endpoint_auth', [])
        enriched['state_transitions'] = requirements.get('state_transitions', [])
        enriched['validation_rules'] = requirements.get('validation_rules', [])
        enriched['pre_conditions'] = requirements.get('pre_conditions', [])

        return enriched

    def _generate_workflows(self, specification: Dict[str, Any]) -> list:
        """
        Generate validation workflows based on the analyzed requirements.
        This runs as a separate phase with different tools and system prompt.
        """
        if not self.requirements:
            print("   ⚠️  No requirements to generate workflows from")
            return []

        # Switch to workflow generation mode
        self.tools = self.WORKFLOW_TOOLS
        self.system_prompt = WORKFLOW_GENERATION_SYSTEM_PROMPT

        # Create enriched spec first, then summarize it (so schema includes business requirement fields)
        enriched_spec = self._apply_requirements(specification, self.requirements)
        spec_summary = self._summarize_spec(enriched_spec)

        # Only include the application-layer requirements (not schema_changes since they're already merged)
        app_requirements = {
            "auth_config": self.requirements.get("auth_config", {}),
            "roles": self.requirements.get("roles", {}),
            "endpoint_auth": self.requirements.get("endpoint_auth", []),
            "state_transitions": self.requirements.get("state_transitions", []),
            "validation_rules": self.requirements.get("validation_rules", []),
            "pre_conditions": self.requirements.get("pre_conditions", [])
        }
        requirements_json = json.dumps(app_requirements, indent=2)

        workflow_prompt = f"""Based on the following API specification and business requirements, generate comprehensive validation workflows.

## API Specification (with business requirement fields already included):
{spec_summary}

## Business Rules to Enforce:
{requirements_json}

## Your Task:
Generate validation workflows that test:

1. **Happy Path** - Normal successful operations
   - Login flows for different roles
   - Successful purchase flow
   - Order approval and delivery

2. **Authorization** - Role-based access control
   - Test that customers cannot access store_owner endpoints
   - Test that guests cannot access authenticated endpoints
   - Test ownership checks (user can only see own orders)

3. **Validation** - Business rule enforcement
   - Cannot order unavailable pets
   - Quantity must be 1
   - Cannot order pet with existing active order

4. **State Transitions** - Verify state machines
   - Order creation → pet becomes pending
   - Order delivery → pet becomes sold
   - Order cancellation → pet returns to available

5. **Pre-conditions** - Pre-condition checks
   - Cannot delete pet with active orders
   - Cannot modify delivered orders

Generate at least 8-12 workflows covering all these categories.
Use the output_workflows tool to submit the complete workflow list.
"""

        # Run the workflow generation
        result = self.run(workflow_prompt)

        # Switch back to requirements tools (in case agent is reused)
        self.tools = self.REQUIREMENTS_TOOLS
        self.system_prompt = BUSINESS_REQUIREMENT_SYSTEM_PROMPT

        return self.workflows if self.workflows else []
