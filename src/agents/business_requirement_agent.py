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


class BusinessRequirementAgent(BaseAgent):
    """Agent that analyzes business constraints and determines implementation requirements"""

    def __init__(self, llm: LLMClient):
        # Define tools for business requirement analysis
        tools = [
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

        super().__init__(
            llm=llm,
            tools=tools,
            tool_executor=self._execute_tool,
            system_prompt=BUSINESS_REQUIREMENT_SYSTEM_PROMPT,
            max_iterations=20
        )
        self.requirements = None
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

            # Create enriched specification
            enriched_spec = self._apply_requirements(specification, self.requirements)

            return {
                "success": True,
                "enriched_specification": enriched_spec,
                "requirements": self.requirements,
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
