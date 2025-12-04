#!/usr/bin/env python3
"""
CLI for env-code-agent - API exploration and Fleet environment generation
"""

import os
import sys
import argparse
import shutil
from dotenv import load_dotenv

from .core.llm_client import LLMClient
from .agents.exploration_agent import ExplorationAgent
from .agents.specification_agent import SpecificationAgent
from .agents.spec_ingestion_agent import SpecificationIngestionAgent
from .agents.business_requirement_agent import BusinessRequirementAgent
from .agents.code_generator_agent import CodeGeneratorAgent


def main():
    """Main CLI entry point"""
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Explore APIs and generate Fleet environments"
    )
    parser.add_argument(
        "command",
        choices=["clone", "explore", "from-spec", "from-spec-with-constraints", "validate"],
        help="Command to run: 'clone' = explore live API and clone, 'explore' = only explore API, 'from-spec' = clone from formal specification, 'from-spec-with-constraints' = clone with business constraints, 'validate' = validate and fix existing environment"
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="Target API URL (for clone/explore), spec file/URL (for from-spec), or directory path (for validate)"
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
        help="Maximum number of exploration iterations (default: 30, recommended: 30-50 for thorough exploration)",
        default=30
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        help="Port for the generated environment to run on (default: 3002)",
        default=3002
    )
    parser.add_argument(
        "--constraints",
        "-c",
        help="Path to file containing business constraints (for from-spec-with-constraints command)",
        default=None
    )

    args = parser.parse_args()

    # Validate target argument for commands that require it
    if args.command != "validate" and not args.target:
        print(f"❌ Error: 'target' argument is required for '{args.command}' command")
        sys.exit(1)

    # Get API key
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY environment variable not set")
        sys.exit(1)

    # Initialize LLM client
    # Use higher max_tokens for spec ingestion (needs to generate large JSON)
    llm = LLMClient(api_key=api_key, max_tokens=8192)

    # ========================================
    # BRANCH: validate vs from-spec-with-constraints vs from-spec vs clone/explore
    # ========================================
    if args.command == "validate":
        # ========================================
        # VALIDATE EXISTING ENVIRONMENT
        # ========================================
        print(f"\n{'='*70}")
        print(f"🔍 VALIDATING EXISTING ENVIRONMENT")
        print(f"{'='*70}\n")

        # Determine the directory to validate
        if args.target:
            env_dir = args.target
        else:
            env_dir = os.path.join(args.output, "cloned-env")

        if not os.path.exists(env_dir):
            print(f"❌ Directory not found: {env_dir}")
            sys.exit(1)

        print(f"📁 Environment directory: {env_dir}")
        print(f"🔌 Testing on port: {args.port}\n")

        # Create a CodeGeneratorAgent just for validation/fixing
        code_agent = CodeGeneratorAgent(llm, env_dir, port=args.port)

        # Try to load existing specification if available
        spec_file = os.path.join(env_dir, ".spec.json")
        if os.path.exists(spec_file):
            import json
            with open(spec_file, 'r') as f:
                code_agent.specification = json.load(f)
            print(f"📋 Loaded specification from .spec.json")

            # Also load workflows if available
            workflows_file = os.path.join(env_dir, "workflows.yaml")
            if os.path.exists(workflows_file):
                import yaml
                with open(workflows_file, 'r') as f:
                    workflows_data = yaml.safe_load(f)
                    if workflows_data and 'workflows' in workflows_data:
                        code_agent.specification['workflows'] = workflows_data['workflows']
                        print(f"📋 Loaded {len(workflows_data['workflows'])} workflows from workflows.yaml")
            print()

        # Run validation and let the agent fix issues
        validate_prompt = f"""You are validating an existing Fleet environment at: {env_dir}

The environment already has generated code. Your task is to:
1. Run validate_environment to test if everything works
2. If validation fails, use read_file to inspect the problematic files
3. Use write_file to fix any issues you find
4. Re-run validate_environment until it passes
5. Call complete_generation when validation succeeds

Start by running validate_environment to see the current state."""

        result = code_agent.run(validate_prompt)

        if result.get('success'):
            print(f"\n{'='*70}")
            print(f"✅ VALIDATION COMPLETE!")
            print(f"{'='*70}\n")
            print(f"📂 Environment at: {env_dir}")
            print(f"✅ All checks passed!")
        else:
            print(f"\n❌ Validation failed after maximum iterations")
            sys.exit(1)

        return

    elif args.command == "from-spec-with-constraints":
        # ========================================
        # PHASE 1: SPECIFICATION INGESTION
        # ========================================
        print(f"\n{'='*70}")
        print(f"📋 PHASE 1: SPECIFICATION INGESTION")
        print(f"{'='*70}\n")

        ingestion_agent = SpecificationIngestionAgent(llm)
        spec_result = ingestion_agent.ingest_spec(
            spec_source=args.target,
            source_type="auto"
        )

        if not spec_result['success']:
            print("❌ Failed to parse specification")
            sys.exit(1)

        base_spec = spec_result['specification']

        # ========================================
        # PHASE 2: BUSINESS REQUIREMENTS ANALYSIS
        # ========================================
        print(f"\n{'='*70}")
        print(f"🔍 PHASE 2: BUSINESS REQUIREMENTS ANALYSIS")
        print(f"{'='*70}\n")

        # Load constraints from file or prompt user
        if args.constraints:
            print(f"📂 Loading constraints from: {args.constraints}")
            try:
                with open(args.constraints, 'r') as f:
                    constraints = f.read()
                print(f"✅ Loaded {len(constraints)} characters of constraints\n")
            except Exception as e:
                print(f"❌ Failed to load constraints file: {e}")
                sys.exit(1)
        else:
            print("📝 No constraints file provided. Enter constraints below.")
            print("   (Type your constraints, then press Ctrl+D or Ctrl+Z when done)\n")
            try:
                constraints = sys.stdin.read()
            except KeyboardInterrupt:
                print("\n\n❌ Cancelled by user")
                sys.exit(1)

        if not constraints.strip():
            print("❌ No constraints provided")
            sys.exit(1)

        # Analyze business requirements
        requirement_agent = BusinessRequirementAgent(llm)
        requirement_result = requirement_agent.analyze_constraints(
            specification=base_spec,
            constraints=constraints
        )

        if not requirement_result['success']:
            print("❌ Failed to analyze business requirements")
            sys.exit(1)

        # Use enriched specification for code generation
        spec = requirement_result['enriched_specification']

    elif args.command == "from-spec":
        # ========================================
        # PHASE 1: SPECIFICATION INGESTION
        # ========================================
        print(f"\n{'='*70}")
        print(f"📋 PHASE 1: SPECIFICATION INGESTION")
        print(f"{'='*70}\n")

        ingestion_agent = SpecificationIngestionAgent(llm)
        spec_result = ingestion_agent.ingest_spec(
            spec_source=args.target,
            source_type="auto"
        )

        if not spec_result['success']:
            print("❌ Failed to parse specification")
            sys.exit(1)

        spec = spec_result['specification']

    else:
        # ========================================
        # PHASE 1: EXPLORATION (for clone/explore)
        # ========================================
        print(f"\n{'='*70}")
        print(f"🔍 PHASE 1: AUTONOMOUS API EXPLORATION")
        print(f"{'='*70}\n")

        if args.endpoints:
            print(f"📍 Starting endpoints: {', '.join(args.endpoints)}")
        print(f"🔄 Max iterations: {args.max_iterations}\n")

        exploration_agent = ExplorationAgent(
            llm,
            args.target,
            max_iterations=args.max_iterations
        )
        exploration_result = exploration_agent.explore(starting_endpoints=args.endpoints)

        print(f"\n{'='*70}")
        print(f"📊 EXPLORATION RESULTS")
        print(f"{'='*70}\n")

        print(f"✅ Success: {exploration_result['success']}")
        print(f"🔄 Iterations: {exploration_result['iterations']}")
        print(f"\n📝 Summary:\n{exploration_result['summary']}\n")

        if exploration_result['observations']:
            print(f"📋 Observations ({len(exploration_result['observations'])}):")
            for i, obs in enumerate(exploration_result['observations'], 1):
                print(f"  {i}. [{obs['category']}] {obs['observation']}")

        # If just exploring, stop here
        if args.command == "explore":
            print()
            return

        # ========================================
        # PHASE 2: SPECIFICATION GENERATION
        # ========================================
        print(f"\n{'='*70}")
        print(f"📋 PHASE 2: SPECIFICATION GENERATION")
        print(f"{'='*70}\n")

        spec_agent = SpecificationAgent(llm)
        spec_result = spec_agent.generate_spec(
            observations=exploration_result['observations'],
            target_url=args.target
        )

        if not spec_result['success']:
            print("❌ Failed to generate specification")
            sys.exit(1)

        print("✅ Specification generated successfully!")
        spec = spec_result['specification']
        print(f"   Endpoints: {len(spec.get('endpoints', []))}")
        print(f"   Tables: {len(spec.get('database', {}).get('tables', []))}")

    # ========================================
    # CODE GENERATION (Phase 2 for from-spec, Phase 3 for clone/from-spec-with-constraints)
    # ========================================
    if args.command == "from-spec":
        phase_num = "2"
    elif args.command == "from-spec-with-constraints":
        phase_num = "3"
    else:
        phase_num = "3"
    print(f"\n{'='*70}")
    print(f"⚡ PHASE {phase_num}: FLEET ENVIRONMENT GENERATION")
    print(f"{'='*70}\n")

    # Clean and create output directory
    output_dir = os.path.join(args.output, "cloned-env")

    # Remove existing directory if it exists
    if os.path.exists(output_dir):
        print(f"🧹 Cleaning existing output directory: {output_dir}")
        try:
            shutil.rmtree(output_dir)
            print(f"   ✓ Old files removed\n")
        except Exception as e:
            print(f"   ⚠️  Warning: Could not fully clean directory: {e}\n")

    # Create fresh output directory
    os.makedirs(output_dir, exist_ok=True)
    print(f"📁 Output directory: {output_dir}")
    print(f"🔌 Generated environment will run on port: {args.port}\n")

    # Save specification and workflows BEFORE code generation
    # (so they're available for debugging even if generation fails)
    import json
    spec_file = os.path.join(output_dir, ".spec.json")
    with open(spec_file, 'w') as f:
        json.dump(spec, f, indent=2)
    print(f"📋 Saved specification to .spec.json")

    if spec.get('workflows'):
        import yaml
        workflows_file = os.path.join(output_dir, "workflows.yaml")
        with open(workflows_file, 'w') as f:
            yaml.dump({"workflows": spec['workflows']}, f, default_flow_style=False, sort_keys=False)
        print(f"📋 Saved {len(spec['workflows'])} workflows to workflows.yaml")
    print()

    code_agent = CodeGeneratorAgent(llm, output_dir, port=args.port)
    code_result = code_agent.generate_code(specification=spec)

    if not code_result['success']:
        print("❌ Failed to generate code")
        print(f"\n💡 Spec and workflows saved to {output_dir} for debugging")
        print(f"   You can manually run: python3 scripts/run_workflows.py {workflows_file}")
        sys.exit(1)

    print(f"\n✅ Code generation complete!")
    print(f"   Generated {len(code_result['generated_files'])} files:")
    for file in code_result['generated_files']:
        print(f"   - {file}")

    # ========================================
    # COMPLETE
    # ========================================
    print(f"\n{'='*70}")
    print(f"🎉 CLONING COMPLETE!")
    print(f"{'='*70}\n")
    print(f"📂 Fleet environment created at: {output_dir}")
    print(f"✅ Environment validated and working!")
    print(f"\n📝 To run the generated environment:")
    print(f"   cd {output_dir}")
    print(f"   pnpm run dev")
    print(f"\n🔌 The API will be available at: http://localhost:{args.port}")
    print(f"\n💡 The environment follows Fleet standards:")
    print(f"   - Uses current.sqlite (auto-copied from seed.db)")
    print(f"   - Supports DATABASE_PATH/ENV_DB_DIR environment variables")
    print(f"   - Includes MCP server for LLM interaction")
    print(f"   - Runs with mprocs for multi-process development")
    print()


if __name__ == "__main__":
    main()
