"""Main CLI entry point for Codex Lifecycle Agent."""

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..core.config import Config
from ..core.models import LifecycleState

app = typer.Typer(
    name="codex",
    help="Codex Lifecycle Agent - AI-powered software development lifecycle automation",
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True, style="red")

# Global options
verbose_option = typer.Option(False, "--verbose", "-v", help="Enable verbose output")
quiet_option = typer.Option(False, "--quiet", "-q", help="Suppress non-essential output")
dry_run_option = typer.Option(False, "--dry-run", help="Show what would happen without executing")
config_option = typer.Option(None, "--config", help="Path to config file")
no_color_option = typer.Option(False, "--no-color", help="Disable colored output")
json_output_option = typer.Option(False, "--json", help="Output in JSON format")


@app.command()
def init(
    project_name: str = typer.Argument(..., help="Project name"),
    stack: str = typer.Option("python-postgres", help="Technology stack"),
    verbose: bool = verbose_option,
    dry_run: bool = dry_run_option,
) -> None:
    """Initialize Codex agent in the current directory."""
    console.print(Panel.fit(f"🚀 Initializing Codex agent for [bold]{project_name}[/bold]"))

    if dry_run:
        console.print("[yellow]DRY RUN - No changes will be made[/yellow]")

    codex_dir = Path(".codex")

    if codex_dir.exists() and not dry_run:
        if not typer.confirm("Codex directory already exists. Reinitialize?"):
            raise typer.Exit(0)

    if not dry_run:
        # Create directory structure
        codex_dir.mkdir(exist_ok=True)
        (codex_dir / "tasks").mkdir(exist_ok=True)
        (codex_dir / "checkpoints").mkdir(exist_ok=True)
        (codex_dir / "logs").mkdir(exist_ok=True)
        (codex_dir / "cache").mkdir(exist_ok=True)
        (codex_dir / "artifacts").mkdir(exist_ok=True)

        # Create initial config
        from ..core.config import ProjectConfig

        project_config = ProjectConfig(name=project_name, stack=stack)
        config = Config(project=project_config)
        config.save_to_file(codex_dir / "config.yaml")

        console.print("[green]✓[/green] Codex agent initialized successfully")
        console.print(f"  Config saved to: {codex_dir / 'config.yaml'}")
    else:
        console.print("[yellow]Would create:[/yellow]")
        console.print(f"  - {codex_dir}/")
        console.print(f"  - {codex_dir}/config.yaml")


@app.command()
def status(
    config_path: Optional[Path] = config_option,
    json_output: bool = json_output_option,
) -> None:
    """Show current agent status and progress."""
    try:
        config = _load_config(config_path)

        if json_output:
            import json

            status_data = {
                "state": "IDLE",  # TODO: Load from persistence
                "project": config.project.name,
                "stack": config.project.stack,
            }
            console.print(json.dumps(status_data, indent=2))
        else:
            table = Table(title="Codex Agent Status")
            table.add_column("Property", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Project", config.project.name)
            table.add_row("Stack", config.project.stack)
            table.add_row("State", "IDLE")  # TODO: Load from persistence
            table.add_row("Config", str(config.codex_dir / "config.yaml"))

            console.print(table)

    except Exception as e:
        err_console.print(f"Error: {e}")
        raise typer.Exit(1)


@app.command()
def plan(
    subcommand: str = typer.Argument("generate", help="Subcommand: generate, show, approve, revise"),
    prd_file: Optional[Path] = typer.Option(None, "--prd", help="Path to PRD file"),
    verbose: bool = verbose_option,
) -> None:
    """PRD ingestion and planning."""
    console.print(f"[yellow]Plan command not yet implemented: {subcommand}[/yellow]")
    # TODO: Implement planning logic
    raise typer.Exit(1)


@app.command()
def scaffold(
    verbose: bool = verbose_option,
    dry_run: bool = dry_run_option,
) -> None:
    """Create project structure and scaffolding."""
    console.print("[yellow]Scaffold command not yet implemented[/yellow]")
    # TODO: Implement scaffolding logic
    raise typer.Exit(1)


@app.command()
def build(
    subcommand: str = typer.Argument("next", help="Subcommand: next, task <id>, all"),
    task_id: Optional[str] = typer.Option(None, "--task", help="Specific task ID"),
    verbose: bool = verbose_option,
) -> None:
    """Execute implementation tasks."""
    console.print(f"[yellow]Build command not yet implemented: {subcommand}[/yellow]")
    # TODO: Implement build logic
    raise typer.Exit(1)


@app.command()
def verify(
    subcommand: str = typer.Argument("run", help="Subcommand: run, fix, report"),
    verbose: bool = verbose_option,
) -> None:
    """Run tests and validation."""
    console.print(f"[yellow]Verify command not yet implemented: {subcommand}[/yellow]")
    # TODO: Implement verification logic
    raise typer.Exit(1)


@app.command()
def deploy(
    environment: str = typer.Argument(..., help="Environment: staging or prod"),
    verbose: bool = verbose_option,
    dry_run: bool = dry_run_option,
) -> None:
    """Deploy to environments."""
    if environment not in ["staging", "prod"]:
        err_console.print("Error: Environment must be 'staging' or 'prod'")
        raise typer.Exit(2)

    console.print(f"[yellow]Deploy command not yet implemented: {environment}[/yellow]")
    # TODO: Implement deployment logic
    raise typer.Exit(1)


@app.command()
def observe(
    subcommand: str = typer.Argument("status", help="Subcommand: status, logs, metrics"),
    verbose: bool = verbose_option,
) -> None:
    """Monitor running application."""
    console.print(f"[yellow]Observe command not yet implemented: {subcommand}[/yellow]")
    # TODO: Implement observability logic
    raise typer.Exit(1)


@app.command()
def maintain(
    subcommand: str = typer.Argument("upgrade", help="Subcommand: upgrade, patch, refactor"),
    verbose: bool = verbose_option,
) -> None:
    """Maintenance operations."""
    console.print(f"[yellow]Maintain command not yet implemented: {subcommand}[/yellow]")
    # TODO: Implement maintenance logic
    raise typer.Exit(1)


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="Number of events to show"),
    json_output: bool = json_output_option,
) -> None:
    """Show audit log."""
    console.print("[yellow]History command not yet implemented[/yellow]")
    # TODO: Implement history logic
    raise typer.Exit(1)


config_app = typer.Typer(help="Manage configuration")
app.add_typer(config_app, name="config")


@config_app.command("show")
def config_show(
    config_path: Optional[Path] = config_option,
) -> None:
    """Show current configuration."""
    try:
        config = _load_config(config_path)
        console.print(config.model_dump_json(indent=2, exclude_none=True))
    except Exception as e:
        err_console.print(f"Error: {e}")
        raise typer.Exit(1)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key (e.g., llm.model)"),
    value: str = typer.Argument(..., help="Config value"),
    config_path: Optional[Path] = config_option,
) -> None:
    """Set configuration value."""
    console.print("[yellow]Config set not yet implemented[/yellow]")
    # TODO: Implement config set
    raise typer.Exit(1)


@config_app.command("validate")
def config_validate(
    config_path: Optional[Path] = config_option,
) -> None:
    """Validate configuration."""
    try:
        config = _load_config(config_path)
        console.print("[green]✓[/green] Configuration is valid")
    except Exception as e:
        err_console.print(f"[red]✗[/red] Configuration is invalid: {e}")
        raise typer.Exit(1)


def _load_config(config_path: Optional[Path] = None) -> Config:
    """Load configuration from file or defaults."""
    if config_path is None:
        config_path = Path(".codex/config.yaml")

    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. Run 'codex init' to initialize."
        )

    return Config.load_from_file(config_path)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        from .. import __version__

        console.print(f"Codex Lifecycle Agent v{__version__}")
        raise typer.Exit(0)


@app.callback()
def main(
    version: Optional[bool] = typer.Option(
        None,
        "--version",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
) -> None:
    """Codex Lifecycle Agent CLI."""
    pass


if __name__ == "__main__":
    app()
