"""Orchestrator - State machine that coordinates agent execution."""

import asyncio
from pathlib import Path
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .base import AgentStatus
from .context import MigrationContext, MigrationPhase, StatePersistence
from .analyzer import AnalyzerAgent
from .builder import BuilderAgent
from .executor import ExecutorAgent
from .validator import ValidatorAgent
from .diagnoser import DiagnoserAgent
from .llm.openai_client import OpenAIClient, LLMConfig
from ..cli.approval import CLIApprovalHandler
from ..connections.sql_server import SQLServerConfig

console = Console()


class MigrationOrchestrator:
    """
    State machine that coordinates the multi-agent migration pipeline.

    Flow:
    1. ANALYZING: Parse and understand SSIS packages
    2. BUILDING: Generate dbt models
    3. AWAITING_APPROVAL: Wait for human approval
    4. EXECUTING: Write files and run dbt
    5. VALIDATING: Compare data
    6. DIAGNOSING: (if validation fails) Analyze and suggest fixes
    7. COMPLETE or FAILED
    """

    def __init__(
        self,
        context: MigrationContext,
        llm_config: Optional[LLMConfig] = None,
        source_db_config: Optional[SQLServerConfig] = None,
        target_db_config: Optional[SQLServerConfig] = None,
        auto_approve: bool = False,
        verbose: bool = True,
    ):
        self.context = context
        self.verbose = verbose
        self.state_dir = Path(context.output_dir) / "state"
        self.persistence = StatePersistence(self.state_dir)

        # Initialize approval handler
        self.approval_handler = CLIApprovalHandler(auto_approve=auto_approve)

        # Initialize LLM client (optional)
        self.llm_client: Optional[OpenAIClient] = None
        if llm_config:
            try:
                self.llm_client = OpenAIClient(llm_config)
            except Exception as e:
                self.log(f"LLM client initialization failed: {e}", "warning")

        # Initialize agents
        self.analyzer = AnalyzerAgent(context, self.llm_client)
        self.builder = BuilderAgent(context, self.llm_client)
        self.executor = ExecutorAgent(context, self.approval_handler)
        self.validator = ValidatorAgent(context, source_db_config, target_db_config)
        self.diagnoser = DiagnoserAgent(context, self.llm_client)

    def log(self, message: str, level: str = "info") -> None:
        """Log a message with appropriate formatting."""
        if not self.verbose:
            return

        level_styles = {
            "info": "blue",
            "success": "green",
            "warning": "yellow",
            "error": "red",
        }
        style = level_styles.get(level, "white")
        console.print(f"[{style}][Orchestrator][/{style}] {message}")

    async def run(self) -> MigrationContext:
        """
        Execute the full migration pipeline.

        Returns:
            Final MigrationContext with all results
        """
        console.print(
            Panel(
                f"[bold]SSIS-to-dbt Migration Pipeline[/bold]\n"
                f"Run ID: {self.context.run_id}",
                border_style="blue",
            )
        )

        try:
            while self.context.current_phase not in [
                MigrationPhase.COMPLETE,
                MigrationPhase.FAILED,
            ]:
                await self._execute_current_phase()
                self.persistence.save_state(self.context)

        except KeyboardInterrupt:
            self.log("Pipeline interrupted by user", "warning")
            self.context.errors.append("Pipeline interrupted by user")
            self.context.transition_to(MigrationPhase.FAILED)

        except Exception as e:
            self.log(f"Pipeline failed: {e}", "error")
            self.context.errors.append(str(e))
            self.context.transition_to(MigrationPhase.FAILED)

        # Final save
        self.persistence.save_state(self.context)

        # Display summary
        self._display_summary()

        return self.context

    async def _execute_current_phase(self) -> None:
        """Execute logic for the current phase."""
        phase = self.context.current_phase

        if phase == MigrationPhase.INITIALIZED:
            self.log("Initializing pipeline")
            self.context.transition_to(MigrationPhase.ANALYZING)

        elif phase == MigrationPhase.ANALYZING:
            await self._run_analysis()

        elif phase == MigrationPhase.ANALYSIS_COMPLETE:
            self.context.transition_to(MigrationPhase.BUILDING)

        elif phase == MigrationPhase.BUILDING:
            await self._run_building()

        elif phase == MigrationPhase.BUILD_COMPLETE:
            self.context.transition_to(MigrationPhase.AWAITING_APPROVAL)

        elif phase == MigrationPhase.AWAITING_APPROVAL:
            # Approval is handled during execution
            self.context.transition_to(MigrationPhase.EXECUTING)

        elif phase == MigrationPhase.EXECUTING:
            await self._run_execution()

        elif phase == MigrationPhase.EXECUTION_COMPLETE:
            self.context.transition_to(MigrationPhase.VALIDATING)

        elif phase == MigrationPhase.VALIDATING:
            await self._run_validation()

        elif phase == MigrationPhase.VALIDATION_COMPLETE:
            self.context.transition_to(MigrationPhase.COMPLETE)

        elif phase == MigrationPhase.VALIDATION_FAILED:
            await self._handle_validation_failure()

        elif phase == MigrationPhase.DIAGNOSING:
            await self._run_diagnosis()

    async def _run_analysis(self) -> None:
        """Run the Analyzer Agent."""
        self.log("Starting analysis phase")
        self.approval_handler.display_progress("Analysis", "Parsing SSIS packages")

        result = await self.analyzer.execute({
            "package_paths": [self.context.input_dir]
        })

        if result.success:
            self.context.analysis_result = result.data
            self.approval_handler.display_progress(
                "Analysis",
                f"Completed - {len(result.data.get('packages', []))} packages analyzed",
                "completed",
            )
            self.context.transition_to(MigrationPhase.ANALYSIS_COMPLETE)
        else:
            self.context.errors.extend(result.errors)
            self.approval_handler.display_progress(
                "Analysis", "Failed", "failed"
            )
            self.context.transition_to(MigrationPhase.FAILED)

    async def _run_building(self) -> None:
        """Run the Builder Agent."""
        self.log("Starting build phase")
        self.approval_handler.display_progress("Build", "Generating dbt models")

        result = await self.builder.execute({
            "analysis": self.context.analysis_result,
            "output_dir": self.context.output_dir,
        })

        if result.success:
            self.context.build_result = result.data
            file_count = result.data.get("file_count", 0)
            self.approval_handler.display_progress(
                "Build",
                f"Completed - {file_count} files generated",
                "completed",
            )
            self.context.transition_to(MigrationPhase.BUILD_COMPLETE)
        else:
            self.context.errors.extend(result.errors)
            self.approval_handler.display_progress(
                "Build", "Failed", "failed"
            )
            self.context.transition_to(MigrationPhase.FAILED)

    async def _run_execution(self) -> None:
        """Run the Executor Agent."""
        self.log("Starting execution phase")
        self.approval_handler.display_progress(
            "Execution", "Awaiting approval", "waiting"
        )

        result = await self.executor.execute({
            "build_result": self.context.build_result,
        })

        if result.success:
            self.context.execution_result = result.data
            summary = result.data.get("summary", {})
            self.approval_handler.display_progress(
                "Execution",
                f"Completed - {summary.get('models_success', 0)} models run",
                "completed",
            )
            self.context.transition_to(MigrationPhase.EXECUTION_COMPLETE)
        else:
            self.context.errors.extend(result.errors)
            self.approval_handler.display_progress(
                "Execution", "Failed or denied", "failed"
            )
            self.context.transition_to(MigrationPhase.FAILED)

    async def _run_validation(self) -> None:
        """Run the Validator Agent."""
        self.log("Starting validation phase")
        self.approval_handler.display_progress("Validation", "Comparing data")

        model_mappings = self.context.build_result.get("model_mappings", {})

        result = await self.validator.execute({
            "model_mappings": model_mappings,
        })

        self.context.validation_result = result.data

        if result.success:
            report = result.data.get("validation_report", {})
            self.approval_handler.display_progress(
                "Validation",
                f"Passed - {report.get('passed', 0)} models validated",
                "completed",
            )
            self.context.transition_to(MigrationPhase.VALIDATION_COMPLETE)
        else:
            report = result.data.get("validation_report", {})
            self.approval_handler.display_progress(
                "Validation",
                f"Failed - {report.get('failed', 0)} models failed",
                "failed",
            )
            self.context.transition_to(MigrationPhase.VALIDATION_FAILED)

    async def _handle_validation_failure(self) -> None:
        """Handle validation failure - retry or fail."""
        if self.context.can_retry():
            self.log(
                f"Validation failed, attempting retry "
                f"({self.context.iteration_count + 1}/{self.context.max_iterations})"
            )
            self.context.increment_iteration()
            self.context.transition_to(MigrationPhase.DIAGNOSING)
        else:
            self.log("Max retries exceeded", "error")
            self.context.errors.append(
                f"Validation failed after {self.context.max_iterations} attempts"
            )
            self.context.transition_to(MigrationPhase.FAILED)

    async def _run_diagnosis(self) -> None:
        """Run the Diagnoser Agent."""
        self.log("Starting diagnosis phase")
        self.approval_handler.display_progress("Diagnosis", "Analyzing failures")

        result = await self.diagnoser.execute({
            "validation_report": self.context.validation_result.get(
                "validation_report", {}
            ),
            "model_mappings": self.context.build_result.get("model_mappings", {}),
        })

        self.context.diagnosis_result = result.data

        if result.data.get("can_retry"):
            # Request approval to retry
            approved = self.approval_handler.request_approval(
                "retry_migration",
                {
                    "iteration": self.context.iteration_count,
                    "diagnosis": result.data,
                },
            )

            if approved:
                self.approval_handler.display_progress(
                    "Diagnosis",
                    "Retry approved, restarting analysis",
                    "completed",
                )
                self.context.record_feedback("retry_approved", result.data)
                self.context.transition_to(MigrationPhase.ANALYZING)
            else:
                self.approval_handler.display_progress(
                    "Diagnosis", "Retry denied", "failed"
                )
                self._save_diagnosis_report(result.data)
                self.context.transition_to(MigrationPhase.FAILED)
        else:
            self.approval_handler.display_progress(
                "Diagnosis",
                "Manual review required",
                "failed",
            )
            self._save_diagnosis_report(result.data)
            self.context.transition_to(MigrationPhase.FAILED)

    def _save_diagnosis_report(self, diagnosis_data: dict[str, Any]) -> None:
        """Save diagnosis report to file."""
        report = diagnosis_data.get("report", "")
        if report:
            report_path = Path(self.context.output_dir) / "diagnosis_report.md"
            with open(report_path, "w") as f:
                f.write(report)
            self.log(f"Diagnosis report saved to: {report_path}")

    def _display_summary(self) -> None:
        """Display final migration summary."""
        summary = self.context.to_summary()

        status_style = (
            "green"
            if self.context.current_phase == MigrationPhase.COMPLETE
            else "red"
        )

        console.print()
        console.print(
            Panel(
                f"[bold]Migration {'Complete' if status_style == 'green' else 'Failed'}[/bold]",
                border_style=status_style,
            )
        )

        self.approval_handler.display_summary({
            "Run ID": summary["run_id"],
            "Duration": f"{summary['duration_seconds']:.1f} seconds",
            "Final Phase": summary["current_phase"],
            "Iterations": summary["iteration_count"],
            "Errors": summary["errors_count"],
            "Warnings": summary["warnings_count"],
        })

        # Show output location
        console.print(f"\n[dim]State saved to: {self.state_dir}[/dim]")


async def run_migration(
    input_dir: str,
    output_dir: str,
    dbt_project_path: str,
    auto_approve: bool = False,
    use_llm: bool = True,
    verbose: bool = True,
    resume_run_id: Optional[str] = None,
) -> MigrationContext:
    """
    Main entry point to run the migration pipeline.

    Args:
        input_dir: Directory containing SSIS packages
        output_dir: Output directory for generated files
        dbt_project_path: Path to dbt project
        auto_approve: If True, skip approval prompts
        use_llm: If True, use OpenAI for enhanced analysis
        verbose: If True, show detailed progress
        resume_run_id: If provided, resume a previous run

    Returns:
        Final MigrationContext
    """
    # Create or load context
    if resume_run_id:
        persistence = StatePersistence(Path(output_dir) / "state")
        context = persistence.load_state(resume_run_id)
    else:
        context = MigrationContext(
            input_dir=input_dir,
            output_dir=output_dir,
            dbt_project_path=dbt_project_path,
        )

    # Configure LLM if requested
    llm_config = None
    if use_llm:
        import os

        if os.getenv("OPENAI_API_KEY"):
            llm_config = LLMConfig()
        else:
            console.print(
                "[yellow]OPENAI_API_KEY not set, running without LLM[/yellow]"
            )

    # Configure database connections
    source_config = SQLServerConfig.from_env("SOURCE")
    target_config = SQLServerConfig.from_env("TARGET")

    # Create and run orchestrator
    orchestrator = MigrationOrchestrator(
        context=context,
        llm_config=llm_config,
        source_db_config=source_config,
        target_db_config=target_config,
        auto_approve=auto_approve,
        verbose=verbose,
    )

    return await orchestrator.run()
