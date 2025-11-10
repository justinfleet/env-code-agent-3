"""
Exploration Agent - autonomously explores an API
"""

from ..core.base_agent import BaseAgent
from ..core.llm_client import LLMClient
from ..tools.tool_executor import ToolExecutor
from ..tools.tool_definitions import EXPLORATION_TOOLS


EXPLORATION_SYSTEM_PROMPT = """You are an expert API explorer. Your job is to autonomously explore an API to understand its complete structure and behavior.

## Your Goals:
1. Discover all available endpoints (GET, POST, PUT, DELETE, etc.)
2. Understand the data models and relationships
3. Identify CRUD patterns and business logic
4. Map state-changing operations
5. Understand validation rules and error handling
6. Identify authentication/authorization requirements

## Your Approach:
- Start with common patterns: /health, /api, /api/v1, etc.
- When you find a collection endpoint (e.g., /api/products), look for single-item endpoints (e.g., /api/products/{id})
- Test pagination, filtering, sorting on list endpoints
- For POST endpoints, try valid and invalid data to understand validation
- Look for relationships (e.g., products → categories, orders → items)
- Pay attention to response structures and infer database schema
- Note any authentication headers or tokens required

## Available Tools:
- make_http_request: Make HTTP requests to explore endpoints
- record_observation: Document your findings
- complete_exploration: Signal when you've gathered enough information

## Strategy:
1. Start broad: Find main resource endpoints
2. Go deep: Explore each resource thoroughly
3. Find relationships: Look for foreign keys and nested resources
4. Test edge cases: Try invalid inputs, missing params, etc.
5. Document everything: Record observations as you go

Remember: Be systematic and thorough. The quality of your exploration determines how well we can clone this API."""


class ExplorationAgent(BaseAgent):
    """Agent that explores an API to understand its structure"""

    def __init__(self, llm: LLMClient, target_url: str, max_iterations: int = 100):
        self.executor = ToolExecutor(target_url)

        super().__init__(
            llm=llm,
            tools=EXPLORATION_TOOLS,
            tool_executor=self.executor.execute,
            system_prompt=EXPLORATION_SYSTEM_PROMPT,
            max_iterations=max_iterations
        )

    def explore(self, starting_endpoints: list[str] = None) -> dict:
        """
        Explore the target API

        Args:
            starting_endpoints: Optional list of endpoints to start exploration with

        Returns exploration results including endpoints, observations, etc.
        """
        if starting_endpoints:
            # User provided specific endpoints to start with
            endpoints_list = "\n".join([f"- {ep}" for ep in starting_endpoints])
            initial_prompt = f"""Explore the API at {self.executor.target_url}.

Start by exploring these specific endpoints:
{endpoints_list}

For each endpoint:
1. Test it to understand what data it returns
2. Look for related endpoints (e.g., if /api/products exists, try /api/products/{{id}})
3. Test query parameters, pagination, filtering
4. For POST/PUT endpoints, try different request bodies
5. Document all findings using record_observation

After exploring these endpoints, look for additional related endpoints and patterns.

When you've thoroughly explored the API and feel you have a complete understanding, use the complete_exploration tool."""
        else:
            # Default exploration strategy
            initial_prompt = f"""Explore the API at {self.executor.target_url}.

Start by testing common endpoints like:
- /health or /api/health
- /api
- /api/v1
- Common resource patterns like /api/products, /api/users, /api/orders, /api/books

Be systematic:
1. First, discover what endpoints exist
2. Then, explore each endpoint in depth
3. Look for patterns and relationships
4. Document everything you learn

When you've thoroughly explored the API and feel you have a complete understanding, use the complete_exploration tool."""

        result = self.run(initial_prompt)

        # Extract exploration data from final result
        # Handle case where agent hits max iterations without calling complete_exploration
        exploration_data = result.get("data")

        if exploration_data is None:
            # Agent didn't call complete_exploration, so grab observations from executor
            exploration_data = {
                "summary": "Exploration incomplete - reached max iterations",
                "observations": self.executor.observations
            }

        return {
            "success": result["success"],
            "iterations": result["iterations"],
            "summary": exploration_data.get("summary", "No summary available"),
            "observations": exploration_data.get("observations", [])
        }
