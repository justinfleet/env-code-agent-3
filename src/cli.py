#!/usr/bin/env python3
"""
CLI for env-code-agent - API exploration and Fleet environment generation
"""

import os
import sys
import argparse
from dotenv import load_dotenv

from .core.llm_client import LLMClient
from .agents.exploration_agent import ExplorationAgent


def main():
    """Main CLI entry point"""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Explore APIs and generate Fleet environments"
    )
    parser.add_argument(
        "command",
        choices=["clone", "explore"],
        help="Command to run"
    )
    parser.add_argument(
        "target_url",
        help="Target API URL (e.g., http://localhost:3001)"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output directory for generated code",
        default="./output"
    )
    parser.add_argument(
        "--endpoints",
        "-e",
        nargs="+",
        help="List of endpoints to explore (e.g., /api/products /api/users)",
        default=None
    )
    parser.add_argument(
        "--max-iterations",
        "-m",
        type=int,
        help="Maximum number of exploration iterations (default: 100)",
        default=100
    )

    args = parser.parse_args()

    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    # Initialize LLM client
    llm = LLMClient(api_key=api_key)

    # Run command
    if args.command in ["clone", "explore"]:
        print(f"\n{'='*70}")
        print(f"🔍 PHASE 1: AUTONOMOUS API EXPLORATION")
        print(f"{'='*70}\n")

        if args.endpoints:
            print(f"📍 Starting endpoints: {', '.join(args.endpoints)}")
        print(f"🔄 Max iterations: {args.max_iterations}\n")

        agent = ExplorationAgent(
            llm,
            args.target_url,
            max_iterations=args.max_iterations
        )
        result = agent.explore(starting_endpoints=args.endpoints)

        print(f"\n{'='*70}")
        print(f"📊 EXPLORATION RESULTS")
        print(f"{'='*70}\n")

        print(f"✅ Success: {result['success']}")
        print(f"🔄 Iterations: {result['iterations']}")
        print(f"\n📝 Summary:\n{result['summary']}\n")

        if result['observations']:
            print(f"📋 Observations ({len(result['observations'])}):")
            for i, obs in enumerate(result['observations'], 1):
                print(f"  {i}. [{obs['category']}] {obs['observation']}")

        print()


if __name__ == "__main__":
    main()
