"""vrzn CLI — version management across project files."""

import sys
from pathlib import Path
from typing import Optional

import rich_click as click
from rich import box
from rich.console import Console
from rich.table import Table

from vrzn.config import ConfigError, find_config, load_config, validate_config
from vrzn.locations import VersionLocation, check_agreement, locations_from_config
from vrzn.version import Version, parse_version

# Rich click configuration
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_COMMANDS_TABLE_COLUMN_WIDTH_RATIO = (1, 2)

console = Console()
err_console = Console(stderr=True)


class VrznContext:
    """Shared state passed through Click context."""

    def __init__(self, dry_run: bool, yes: bool, quiet: bool, config_path: Optional[Path]):
        self.dry_run = dry_run
        self.yes = yes
        self.quiet = quiet
        self.config_path = config_path
        self._locations: Optional[list[VersionLocation]] = None
        self._project_root: Optional[Path] = None

    def load(self) -> list[VersionLocation]:
        """Load config and return locations. Exits on error."""
        if self._locations is not None:
            return self._locations

        if self.config_path:
            config_file = self.config_path
            if not config_file.is_file():
                err_console.print(f"[red]Config file not found: {config_file}[/red]")
                sys.exit(2)
        else:
            config_file = find_config()
            if config_file is None:
                err_console.print("[red]No vrzn config found. Create vrzn.toml or add [tool.vrzn] to pyproject.toml.[/red]")
                sys.exit(2)

        self._project_root = config_file.parent

        try:
            config = load_config(config_file)
            validate_config(config)
        except ConfigError as e:
            err_console.print(f"[red]Configuration error: {e}[/red]")
            sys.exit(2)

        self._locations = locations_from_config(config, self._project_root)
        return self._locations

    @property
    def project_root(self) -> Path:
        if self._project_root is None:
            self.load()
        return self._project_root


@click.group()
@click.option("--dry-run", is_flag=True, help="Show what would change without writing files.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts.")
@click.option("--quiet", "-q", is_flag=True, help="Machine-readable output, no tables.")
@click.option("--config", "-c", "config_path", type=click.Path(path_type=Path), default=None,
              help="Path to config file (overrides discovery).")
@click.pass_context
def cli(ctx: click.Context, dry_run: bool, yes: bool, quiet: bool, config_path: Optional[Path]):
    """Manage version numbers across project files."""
    ctx.ensure_object(dict)
    ctx.obj["vrzn"] = VrznContext(dry_run, yes, quiet, config_path)


@cli.command()
@click.pass_context
def get(ctx: click.Context):
    """Display the current version in all configured files."""
    vctx: VrznContext = ctx.obj["vrzn"]
    locations = vctx.load()
    consensus, mismatches = check_agreement(locations)

    if vctx.quiet:
        if consensus:
            click.echo(consensus.normalized)
        sys.exit(1 if mismatches else 0)

    table = Table(
        title="vrzn \u2014 version report",
        box=box.ROUNDED,
        show_lines=True,
        title_style="bold cyan",
        header_style="bold",
    )
    table.add_column("File", style="blue", max_width=45)
    table.add_column("Location", style="dim")
    table.add_column("Version", justify="center")
    table.add_column("Status", justify="center")

    mismatch_locs = {id(m.location) for m in mismatches}

    for loc in locations:
        rel_path = _relative_path(loc.file, vctx.project_root)
        parsed = loc.read_version_parsed()

        if parsed is None:
            table.add_row(rel_path, loc.label, "-", "[yellow]not found[/yellow]")
        elif id(loc) in mismatch_locs:
            ver_display = parsed.base if loc.base_only else parsed.normalized
            table.add_row(rel_path, loc.label, f"[red]{ver_display}[/red]", "[red]mismatch[/red]")
        else:
            ver_display = parsed.base if loc.base_only else parsed.normalized
            table.add_row(rel_path, loc.label, ver_display, "[green]ok[/green]")

    console.print()
    console.print(table)
    console.print()

    if consensus:
        console.print(f"  Consensus version: [bold]{consensus.normalized}[/bold]")
    if mismatches:
        console.print(f"  [red]{len(mismatches)} location(s) out of sync[/red]")
    else:
        console.print("  [green]All version numbers are consistent.[/green]")
    console.print()

    sys.exit(1 if mismatches else 0)


def _relative_path(path: Path, root: Path) -> str:
    """Return path relative to root, or absolute if not under root."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main():
    """Entry point for the vrzn CLI."""
    cli()
