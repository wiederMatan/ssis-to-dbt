#!/usr/bin/env python3
"""
SSIS-to-dbt Multi-Agent Migration Pipeline

CLI entry point for running the intelligent agent-based migration system.

Usage:
    python run_agents.py ./samples/ssis_packages --output ./output
    python run_agents.py ./samples/ssis_packages --auto-approve
    python run_agents.py --resume <run_id>
"""

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from rich.console import Console

from src.logging_config import setup_logging, get_logger

console = Console()
logger = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="SSIS-to-dbt Multi-Agent Migration Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_agents.py ./samples/ssis_packages
  python run_agents.py ./samples/ssis_packages --output ./output --auto-approve
  python run_agents.py --resume 20240115_143022
  python run_agents.py ./samples --no-llm --verbose

Environment Variables:
  OPENAI_API_KEY        - OpenAI API key for LLM-enhanced analysis
  SOURCE_SQL_SERVER_HOST - Source SQL Server hostname
  SOURCE_SQL_SERVER_DB   - Source database name
  TARGET_SQL_SERVER_HOST - Target SQL Server hostname
  TARGET_SQL_SERVER_DB   - Target database name
        """,
    )

    parser.add_argument(
        "input_dir",
        nargs="?",
        help="Directory containing SSIS packages (.dtsx files)",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="./output",
        help="Output directory for generated files (default: ./output)",
    )

    parser.add_argument(
        "--dbt-project",
        default="./dbt_project",
        help="Path to dbt project (default: ./dbt_project)",
    )

    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Automatically approve all actions (skip confirmation prompts)",
    )

    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Disable LLM-enhanced analysis (run without OpenAI)",
    )

    parser.add_argument(
        "--resume",
        metavar="RUN_ID",
        help="Resume a previous migration run by its ID",
    )

    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="List all previous migration runs",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        default=True,
        help="Show detailed progress (default: True)",
    )

    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="Suppress detailed output",
    )

    parser.add_argument(
        "--max-retries",
        type=int,
        default=3,
        help="Maximum retry attempts on validation failure (default: 3)",
    )

    return parser.parse_args()


def list_previous_runs(output_dir: str) -> None:
    """List all previous migration runs."""
    from src.agents.context import StatePersistence

    state_dir = Path(output_dir) / "state"
    if not state_dir.exists():
        console.print("[yellow]No previous runs found[/yellow]")
        return

    persistence = StatePersistence(state_dir)
    runs = persistence.list_runs()

    if not runs:
        console.print("[yellow]No previous runs found[/yellow]")
        return

    console.print("[bold]Previous Migration Runs:[/bold]\n")
    for run_id in sorted(runs, reverse=True):
        try:
            context = persistence.load_state(run_id)
            status_color = (
                "green" if context.current_phase == "complete" else "red"
            )
            console.print(
                f"  [{status_color}]{run_id}[/{status_color}] - "
                f"{context.current_phase} - "
                f"{context.iteration_count} iterations"
            )
        except Exception:
            console.print(f"  [dim]{run_id}[/dim] - (unable to load)")


async def main() -> int:
    """Main entry point."""
    args = parse_args()

    # Setup logging based on verbosity
    log_level = "DEBUG" if args.verbose and not args.quiet else "INFO"
    if args.quiet:
        log_level = "WARNING"
    setup_logging(level=log_level, log_dir=str(Path(args.output) / "logs"))
    logger.info("SSIS-to-dbt Migration Pipeline starting")

    # Handle list runs
    if args.list_runs:
        list_previous_runs(args.output)
        return 0

    # Validate arguments
    if not args.resume and not args.input_dir:
        console.print(
            "[red]Error: input_dir is required unless using --resume[/red]"
        )
        console.print("Use --help for usage information")
        return 1

    # Check input directory exists
    if args.input_dir:
        input_path = Path(args.input_dir)
        if not input_path.exists():
            console.print(f"[red]Error: Input directory not found: {args.input_dir}[/red]")
            return 1

        # Check for .dtsx files
        dtsx_files = list(input_path.glob("**/*.dtsx"))
        if not dtsx_files:
            console.print(
                f"[yellow]Warning: No .dtsx files found in {args.input_dir}[/yellow]"
            )

    # Create output directory
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    # Import here to avoid circular imports and show nicer errors
    try:
        from src.agents.orchestrator import run_migration
    except ImportError as e:
        console.print(f"[red]Error importing agents: {e}[/red]")
        console.print("Make sure all dependencies are installed:")
        console.print("  pip install -r requirements.txt")
        return 1

    # Run the migration
    try:
        context = await run_migration(
            input_dir=args.input_dir or "",
            output_dir=args.output,
            dbt_project_path=args.dbt_project,
            auto_approve=args.auto_approve,
            use_llm=not args.no_llm,
            verbose=not args.quiet,
            resume_run_id=args.resume,
        )

        # Return appropriate exit code
        if context.current_phase == "complete":
            return 0
        else:
            return 1

    except KeyboardInterrupt:
        logger.warning("Migration cancelled by user")
        console.print("\n[yellow]Migration cancelled by user[/yellow]")
        return 130

    except Exception as e:
        logger.exception("Migration failed with error")
        console.print(f"\n[red]Migration failed: {e}[/red]")
        if args.verbose:
            import traceback

            console.print(traceback.format_exc())
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
