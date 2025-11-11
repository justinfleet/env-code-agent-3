"""
Base Agent class with simple agentic loop
"""

from typing import List, Dict, Any, Optional, Callable
from .llm_client import LLMClient


class BaseAgent:
    """
    Simple agentic loop implementation

    This handles the core pattern:
    1. Send messages to LLM
    2. If LLM wants to use tools, execute them
    3. Send tool results back to LLM
    4. Repeat until done or max iterations
    """

    def __init__(
        self,
        llm: LLMClient,
        tools: List[Dict[str, Any]],
        tool_executor: Callable,
        system_prompt: str,
        max_iterations: int = 100
    ):
        self.llm = llm
        self.tools = tools
        self.tool_executor = tool_executor
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.messages: List[Dict[str, Any]] = []

    def run(self, initial_prompt: str) -> Dict[str, Any]:
        """
        Run the agentic loop

        Returns:
            {
                "success": bool,
                "iterations": int,
                "final_message": str,
                "data": Any
            }
        """
        print(f"\n🤖 Starting agent: {self.__class__.__name__}")
        print(f"📋 Initial task: {initial_prompt}\n")

        # Start with user message
        self.messages.append({
            "role": "user",
            "content": initial_prompt
        })

        iteration = 0
        is_complete = False
        final_data = None

        while iteration < self.max_iterations and not is_complete:
            iteration += 1
            print(f"\n━━━ Iteration {iteration}/{self.max_iterations} ━━━")

            # Get LLM response
            response = self.llm.create_message(
                messages=self.messages,
                tools=self.tools,
                system=self.system_prompt
            )

            # Log thinking
            text_content = self._extract_text(response.content)
            if text_content:
                preview = text_content[:200] + ("..." if len(text_content) > 200 else "")
                print(f"💭 Agent: {preview}")

            # Check for tool use
            tool_uses = [block for block in response.content if block.type == "tool_use"]

            if tool_uses:
                # Build assistant message with tool uses
                self.messages.append({
                    "role": "assistant",
                    "content": response.content
                })

                # Execute tools and build tool results
                tool_results = []
                for tool_use in tool_uses:
                    print(f"🔧 Tool: {tool_use.name}")
                    print(f"   Input: {str(tool_use.input)[:100]}...")

                    try:
                        result = self.tool_executor(tool_use.name, tool_use.input)

                        # Convert result to compact string representation
                        result_str = str(result) if len(str(result)) < 200 else str(result)[:200] + "..."

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": result_str  # Compact string, not full result
                        })

                        # Check if tool signals completion
                        if isinstance(result, dict) and result.get("complete"):
                            is_complete = True
                            final_data = result

                        # Compact console output
                        if isinstance(result, dict):
                            # Show just success status and key field
                            status = "✓" if result.get("success") else "✗"
                            key_field = result.get("file") or result.get("db") or ("OK" if result.get("validated") else "")
                            print(f"   {status} {key_field if key_field else str(result)[:80]}")
                    except Exception as e:
                        print(f"   ✗ Error: {str(e)}")
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": f"Error: {str(e)}",
                            "is_error": True
                        })

                # Add tool results as user message
                self.messages.append({
                    "role": "user",
                    "content": tool_results
                })

                # If complete, break
                if is_complete:
                    break

            else:
                # No tool use, agent is done
                self.messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                break

            # Check stop reason
            if response.stop_reason == "end_turn":
                break

        print(f"\n✅ Agent completed after {iteration} iterations\n")

        final_message = self._extract_text(self.messages[-1]["content"]) if self.messages else ""

        return {
            "success": is_complete or iteration < self.max_iterations,
            "iterations": iteration,
            "final_message": final_message,
            "data": final_data
        }

    def _extract_text(self, content) -> str:
        """Extract text from content blocks"""
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            text_blocks = [block.text for block in content if hasattr(block, "text")]
            return " ".join(text_blocks)
        return ""

    def reset(self):
        """Reset conversation history"""
        self.messages = []
