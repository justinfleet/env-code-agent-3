"""
Workflow Test Runner - executes validation workflows against a running API
"""

import re
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional


class WorkflowRunner:
    """Executes validation workflows against a running API server"""

    # Built-in test variables (these should match seed data)
    BUILTIN_VARIABLES = {
        "customer_username": "customer1",
        "store_owner_username": "storeowner",
        "admin_username": "admin",
        "test_password": "password",
        "available_pet_id": "1",
        "pending_pet_id": "5",
        "sold_pet_id": "6",
    }

    def __init__(self, base_url: str = "http://localhost:3002"):
        self.base_url = base_url.rstrip('/')
        self.variables: Dict[str, str] = dict(self.BUILTIN_VARIABLES)
        self.results: List[Dict[str, Any]] = []

    def run_workflows(self, workflows: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Run all workflows and return results.

        Args:
            workflows: List of workflow definitions

        Returns:
            Summary with passed/failed counts and details
        """
        self.results = []
        passed = 0
        failed = 0

        for workflow in workflows:
            result = self.run_workflow(workflow)
            self.results.append(result)

            if result['success']:
                passed += 1
            else:
                failed += 1

        return {
            "success": failed == 0,
            "total": len(workflows),
            "passed": passed,
            "failed": failed,
            "results": self.results
        }

    def run_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single workflow.

        Args:
            workflow: Workflow definition with name, steps, etc.

        Returns:
            Result with success status and step details
        """
        name = workflow.get('name', 'unnamed')
        description = workflow.get('description', '')
        category = workflow.get('category', 'unknown')
        steps = workflow.get('steps', [])

        # Reset variables for this workflow (keep builtins)
        self.variables = dict(self.BUILTIN_VARIABLES)

        step_results = []
        workflow_success = True

        print(f"\n   📋 {name} ({category})")

        for i, step in enumerate(steps):
            step_result = self._execute_step(step, i + 1)
            step_results.append(step_result)

            if not step_result['success']:
                workflow_success = False
                error_msg = step_result.get('error', 'Failed')
                response_preview = step_result.get('response', '')
                if response_preview and len(str(response_preview)) > 100:
                    response_preview = str(response_preview)[:100] + '...'
                print(f"      ❌ Step {i+1} [{step.get('action', '')}]: {error_msg}")
                if response_preview:
                    print(f"         Response: {response_preview}")
                break  # Stop workflow on first failure
            else:
                print(f"      ✓ Step {i+1}: {step.get('description', step.get('action', ''))}")

        return {
            "name": name,
            "description": description,
            "category": category,
            "success": workflow_success,
            "steps": step_results
        }

    def _execute_step(self, step: Dict[str, Any], step_num: int) -> Dict[str, Any]:
        """Execute a single workflow step"""
        action = step.get('action', '')
        expect = step.get('expect', {})

        # Parse action into method and path
        parts = action.split(' ', 1)
        if len(parts) != 2:
            return {
                "success": False,
                "error": f"Invalid action format: {action}"
            }

        method = parts[0].upper()
        path = self._substitute_variables(parts[1])

        # Handle query parameters in step (separate from URL query string)
        query_params = step.get('query', {})
        if query_params:
            query_params = self._substitute_variables_in_obj(query_params)
            query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])
            if '?' in path:
                path = f"{path}&{query_string}"
            else:
                path = f"{path}?{query_string}"

        # Build URL
        url = self.base_url + path

        # Build headers
        headers = {}
        for key, value in step.get('headers', {}).items():
            headers[key] = self._substitute_variables(str(value))

        # Build body
        body = None
        if step.get('body'):
            body_data = self._substitute_variables_in_obj(step['body'])
            body = json.dumps(body_data).encode('utf-8')
            headers['Content-Type'] = 'application/json'

        # Make request
        try:
            req = urllib.request.Request(url, data=body, headers=headers, method=method)

            try:
                with urllib.request.urlopen(req, timeout=10) as response:
                    status = response.status
                    response_body = response.read().decode('utf-8')
                    try:
                        response_json = json.loads(response_body)
                    except json.JSONDecodeError:
                        response_json = None
            except urllib.error.HTTPError as e:
                status = e.code
                response_body = e.read().decode('utf-8') if e.fp else ''
                try:
                    response_json = json.loads(response_body)
                except json.JSONDecodeError:
                    response_json = None

            # Check expectations
            expected_status = expect.get('status')
            if expected_status and status != expected_status:
                return {
                    "success": False,
                    "error": f"Expected status {expected_status}, got {status}",
                    "actual_status": status,
                    "response": response_body[:500]
                }

            # Check body_contains
            body_contains = expect.get('body_contains', {})
            if body_contains and response_json:
                for key, expected_value in body_contains.items():
                    # Handle {{save:variable_name}} syntax
                    if isinstance(expected_value, str) and expected_value.startswith('{{save:'):
                        var_name = expected_value[7:-2]  # Extract variable name
                        if key in response_json:
                            self.variables[var_name] = str(response_json[key])
                    else:
                        # Check actual value matches
                        actual_value = response_json.get(key)
                        expected_substituted = self._substitute_variables(str(expected_value))

                        if str(actual_value) != expected_substituted:
                            return {
                                "success": False,
                                "error": f"Expected {key}={expected_substituted}, got {actual_value}",
                                "response": response_body[:500]
                            }

            return {
                "success": True,
                "status": status,
                "response": response_json
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Request failed: {str(e)}"
            }

    def _substitute_variables(self, text: str) -> str:
        """Replace {{variable}} with actual values"""
        def replace_var(match):
            var_name = match.group(1)
            return self.variables.get(var_name, match.group(0))

        return re.sub(r'\{\{([^}]+)\}\}', replace_var, text)

    def _substitute_variables_in_obj(self, obj: Any) -> Any:
        """Recursively substitute variables in an object"""
        if isinstance(obj, str):
            return self._substitute_variables(obj)
        elif isinstance(obj, dict):
            return {k: self._substitute_variables_in_obj(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._substitute_variables_in_obj(item) for item in obj]
        else:
            return obj

    def print_summary(self):
        """Print a summary of workflow results"""
        if not self.results:
            print("No workflows executed")
            return

        passed = sum(1 for r in self.results if r['success'])
        failed = len(self.results) - passed

        print(f"\n{'='*50}")
        print(f"WORKFLOW TEST RESULTS")
        print(f"{'='*50}")
        print(f"Total: {len(self.results)}, Passed: {passed}, Failed: {failed}")

        if failed > 0:
            print(f"\nFailed workflows:")
            for r in self.results:
                if not r['success']:
                    print(f"  ❌ {r['name']}: {r.get('steps', [{}])[-1].get('error', 'Unknown error')}")

        print()
