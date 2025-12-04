#!/usr/bin/env python3
"""
Run workflow tests against a running API server.

Usage:
    python scripts/run_workflows.py [workflows.yaml] [--base-url URL] [--verbose]

Examples:
    # Test against default localhost:3002
    python scripts/run_workflows.py output/cloned-env/workflows.yaml

    # Test against custom URL
    python scripts/run_workflows.py workflows.yaml --base-url http://localhost:3000

    # Verbose output (show all step details)
    python scripts/run_workflows.py workflows.yaml --verbose

    # Reset database to seed state before running (ensures clean state)
    python scripts/run_workflows.py workflows.yaml --reset-db
"""

import sys
import os
import argparse
import shutil

# Add parent directory to path so we can import from src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml
from src.core.workflow_runner import WorkflowRunner


def reset_database(workflows_file: str) -> bool:
    """
    Reset the database to seed state by copying seed.db to current.sqlite.

    Looks for data/ directory relative to workflows.yaml file location.
    Returns True if reset was successful, False otherwise.
    """
    # Find the environment directory (parent of workflows.yaml)
    env_dir = os.path.dirname(os.path.abspath(workflows_file))
    data_dir = os.path.join(env_dir, 'data')

    seed_db = os.path.join(data_dir, 'seed.db')
    current_db = os.path.join(data_dir, 'current.sqlite')

    if not os.path.exists(seed_db):
        print(f"⚠️  Warning: seed.db not found at {seed_db}")
        return False

    try:
        # Remove WAL and SHM files if they exist (SQLite journal files)
        for ext in ['-wal', '-shm']:
            wal_file = current_db + ext
            if os.path.exists(wal_file):
                os.remove(wal_file)

        # Copy seed.db to current.sqlite
        shutil.copy2(seed_db, current_db)
        print(f"🔄 Database reset to seed state")
        return True
    except Exception as e:
        print(f"⚠️  Warning: Failed to reset database: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run workflow tests against API")
    parser.add_argument("workflows_file", help="Path to workflows.yaml file")
    parser.add_argument("--base-url", "-u", default="http://localhost:3002",
                        help="Base URL of the API server (default: http://localhost:3002)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show verbose output including response bodies")
    parser.add_argument("--workflow", "-w",
                        help="Run only a specific workflow by name")
    parser.add_argument("--category", "-c",
                        help="Run only workflows in a specific category")
    parser.add_argument("--reset-db", "-r", action="store_true",
                        help="Reset database to seed state before running tests")

    args = parser.parse_args()

    # Load workflows
    if not os.path.exists(args.workflows_file):
        print(f"❌ File not found: {args.workflows_file}")
        sys.exit(1)

    with open(args.workflows_file, 'r') as f:
        data = yaml.safe_load(f)

    workflows = data.get('workflows', [])
    if not workflows:
        print("❌ No workflows found in file")
        sys.exit(1)

    # Filter workflows if requested
    if args.workflow:
        workflows = [w for w in workflows if w.get('name') == args.workflow]
        if not workflows:
            print(f"❌ Workflow '{args.workflow}' not found")
            sys.exit(1)

    if args.category:
        workflows = [w for w in workflows if w.get('category') == args.category]
        if not workflows:
            print(f"❌ No workflows found in category '{args.category}'")
            sys.exit(1)

    # Reset database if requested
    if args.reset_db:
        reset_database(args.workflows_file)

    print(f"🔍 Running {len(workflows)} workflow(s) against {args.base_url}")
    print(f"{'='*60}\n")

    # Run workflows
    runner = WorkflowRunner(base_url=args.base_url)

    if args.verbose:
        # Override the runner to show more details
        original_execute = runner._execute_step
        def verbose_execute(step, step_num):
            result = original_execute(step, step_num)
            if result.get('response'):
                print(f"         Response: {result.get('response')}")
            return result
        runner._execute_step = verbose_execute

    result = runner.run_workflows(workflows)

    # Print summary
    print(f"\n{'='*60}")
    print(f"RESULTS: {result['passed']}/{result['total']} passed")
    print(f"{'='*60}")

    if result['failed'] > 0:
        print(f"\n❌ Failed workflows:")
        for r in result['results']:
            if not r['success']:
                failed_step = r.get('steps', [{}])[-1]
                print(f"   - {r['name']}: {failed_step.get('error', 'Unknown')}")
        sys.exit(1)
    else:
        print(f"\n✅ All workflows passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
