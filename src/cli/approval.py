"""CLI approval handler for human-in-the-loop decisions."""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from rich.table import Table
from rich.syntax import Syntax

console = Console()


class CLIApprovalHandler:
    """Handle approval requests via CLI prompts."""

    def __init__(self, auto_approve: bool = False, timeout: int = 300):
        """
        Initialize the approval handler.

        Args:
            auto_approve: If True, automatically approve all requests
            timeout: Timeout in seconds for approval prompts
        """
        self.auto_approve = auto_approve
        self.timeout = timeout

    def request_approval(
        self,
        action: str,
        details: dict[str, Any],
    ) -> bool:
        """
        Display approval request and get user response.

        Args:
            action: Name of the action requiring approval
            details: Context to show the user

        Returns:
            True if approved, False otherwise
        """
        if self.auto_approve:
            console.print(
                f"[yellow]Auto-approving action: {action}[/yellow]"
            )
            return True

        console.print()
        console.print(
            Panel(
                f"[bold yellow]Approval Required: {action}[/bold yellow]",
                title="Human-in-the-Loop",
                border_style="yellow",
            )
        )

        # Display action-specific details
        if action == "write_files":
            self._display_file_approval(details)
        elif action == "execute_dbt":
            self._display_dbt_approval(details)
        elif action == "retry_migration":
            self._display_retry_approval(details)
        else:
            self._display_generic_approval(details)

        console.print()
        try:
            approved = Confirm.ask(
                "[bold]Do you approve this action?[/bold]",
                default=False,
            )
        except KeyboardInterrupt:
            console.print("\n[red]Approval cancelled by user[/red]")
            return False

        if approved:
            console.print("[green]✓ Approved[/green]")
        else:
            console.print("[red]✗ Denied[/red]")

        return approved

    def _display_file_approval(self, details: dict[str, Any]) -> None:
        """Display file writing approval details."""
        files = details.get("files", [])

        console.print("\n[bold]Files to be written:[/bold]")

        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("File Path", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Model", style="yellow")

        for f in files[:15]:  # Show first 15
            table.add_row(
                f.get("path", "unknown"),
                f.get("file_type", ""),
                f.get("model_name", "-"),
            )

        console.print(table)

        if len(files) > 15:
            console.print(f"  ... and {len(files) - 15} more files")

        # Show preview of first file if available
        if files and details.get("show_preview", True):
            first_file = files[0]
            content = first_file.get("content", "")
            if content:
                console.print("\n[bold]Preview of first file:[/bold]")
                syntax = Syntax(
                    content[:500] + ("..." if len(content) > 500 else ""),
                    "sql",
                    theme="monokai",
                    line_numbers=True,
                )
                console.print(syntax)

    def _display_dbt_approval(self, details: dict[str, Any]) -> None:
        """Display dbt execution approval details."""
        files = details.get("files", [])
        commands = details.get("commands", ["deps", "run", "test"])

        console.print("\n[bold]Files to be written:[/bold]")
        for f in files[:10]:
            path = f.get("path", f) if isinstance(f, dict) else f
            console.print(f"  • {path}")
        if len(files) > 10:
            console.print(f"  ... and {len(files) - 10} more files")

        console.print("\n[bold]dbt commands to execute:[/bold]")
        for cmd in commands:
            console.print(f"  • [cyan]dbt {cmd}[/cyan]")

        console.print("\n[dim]This will modify the dbt project and run models.[/dim]")

    def _display_retry_approval(self, details: dict[str, Any]) -> None:
        """Display retry approval details after failure."""
        iteration = details.get("iteration", 1)
        diagnosis = details.get("diagnosis", {})

        console.print(f"\n[bold]Retry Attempt:[/bold] {iteration}")

        if diagnosis:
            console.print("\n[bold]Diagnosis:[/bold]")
            root_cause = diagnosis.get("root_cause", "Unknown")
            console.print(f"  Root cause: {root_cause}")

            fixes = diagnosis.get("suggested_fixes", [])
            if fixes:
                console.print("\n[bold]Suggested Fixes:[/bold]")
                for fix in fixes:
                    if isinstance(fix, dict):
                        desc = fix.get("description", str(fix))
                        priority = fix.get("priority", "medium")
                        console.print(f"  • [{priority}] {desc}")
                    else:
                        console.print(f"  • {fix}")

        console.print(
            "\n[dim]Approving will restart the pipeline with fixes applied.[/dim]"
        )

    def _display_generic_approval(self, details: dict[str, Any]) -> None:
        """Display generic approval details."""
        console.print("\n[bold]Action Details:[/bold]")
        for key, value in details.items():
            if isinstance(value, (list, dict)):
                console.print(f"  {key}:")
                if isinstance(value, list):
                    for item in value[:5]:
                        console.print(f"    • {item}")
                    if len(value) > 5:
                        console.print(f"    ... and {len(value) - 5} more")
                else:
                    for k, v in list(value.items())[:5]:
                        console.print(f"    {k}: {v}")
            else:
                console.print(f"  {key}: {value}")

    def display_progress(
        self,
        phase: str,
        message: str,
        status: str = "running",
    ) -> None:
        """Display progress update."""
        status_icons = {
            "running": "[blue]⟳[/blue]",
            "completed": "[green]✓[/green]",
            "failed": "[red]✗[/red]",
            "waiting": "[yellow]⏳[/yellow]",
        }
        icon = status_icons.get(status, "•")
        console.print(f"{icon} [bold]{phase}:[/bold] {message}")

    def display_summary(
        self,
        results: dict[str, Any],
    ) -> None:
        """Display final summary of the migration run."""
        console.print()
        console.print(
            Panel(
                "[bold]Migration Summary[/bold]",
                border_style="blue",
            )
        )

        table = Table(show_header=True, header_style="bold")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        for key, value in results.items():
            table.add_row(str(key), str(value))

        console.print(table)
