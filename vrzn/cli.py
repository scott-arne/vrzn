"""vrzn CLI — version management across project files."""

from pathlib import Path

import rich_click as click
from rich import box
from rich.console import Console
from rich.table import Table

from vrzn.config import ConfigError, find_config, load_config, validate_config
from vrzn.locations import VersionFormat, VersionLocation, check_agreement, locations_from_config
from vrzn.version import Version, parse_version

# Rich click configuration
click.rich_click.TEXT_MARKUP = "rich"
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_COMMANDS_TABLE_COLUMN_WIDTH_RATIO = (1, 2)

console = Console()
err_console = Console(stderr=True)


class VrznContext:
    """Shared state passed through Click context."""

    def __init__(self, dry_run: bool, yes: bool, quiet: bool, config_path: Path | None):
        self.dry_run = dry_run
        self.yes = yes
        self.quiet = quiet
        self.config_path = config_path
        self._locations: list[VersionLocation] | None = None
        self._project_root: Path | None = None

    def load(self) -> list[VersionLocation]:
        """Load config and return locations.

        :returns: List of version locations.
        :raises ConfigError: If config is missing, invalid, or unreadable.
        """
        if self._locations is not None:
            return self._locations

        if self.config_path:
            config_file = self.config_path
            if not config_file.is_file():
                raise ConfigError(f"Config file not found: {config_file}")
        else:
            config_file = find_config()
            if config_file is None:
                raise ConfigError(
                    "No vrzn config found. Create vrzn.toml or add [tool.vrzn] to pyproject.toml."
                )

        self._project_root = config_file.parent
        config = load_config(config_file)
        validate_config(config)
        self._locations = locations_from_config(config, self._project_root)
        return self._locations

    @property
    def project_root(self) -> Path:
        if self._project_root is None:
            self.load()
            assert self._project_root is not None
        return self._project_root


@click.group()
@click.option("--dry-run", is_flag=True, help="Show what would change without writing files.")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompts.")
@click.option("--quiet", "-q", is_flag=True, help="Machine-readable output, no tables.")
@click.option("--config", "-c", "config_path", type=click.Path(path_type=Path), default=None,
              help="Path to config file (overrides discovery).")
@click.pass_context
def cli(ctx: click.Context, dry_run: bool, yes: bool, quiet: bool, config_path: Path | None):
    """Manage version numbers across project files."""
    ctx.ensure_object(dict)
    ctx.obj["vrzn"] = VrznContext(dry_run, yes, quiet, config_path)


def _common_options(f):
    """Add common CLI options to a subcommand.

    Mirrors the global group options so users can place flags like ``--yes``
    either before or after the subcommand name.
    """
    f = click.option("--config", "-c", "config_path", type=click.Path(path_type=Path),
                      default=None, help="Path to config file (overrides discovery).")(f)
    f = click.option("--quiet", "-q", is_flag=True, default=False,
                      help="Machine-readable output, no tables.")(f)
    f = click.option("--yes", "-y", is_flag=True, default=False,
                      help="Skip confirmation prompts.")(f)
    f = click.option("--dry-run", is_flag=True, default=False,
                      help="Show what would change without writing files.")(f)
    return f


def _merge_globals(
    ctx: click.Context,
    dry_run: bool,
    yes: bool,
    quiet: bool,
    config_path: Path | None,
) -> VrznContext:
    """Merge subcommand-level flags into the shared VrznContext.

    Boolean flags are OR-ed so that ``vrzn --yes bump`` and ``vrzn bump --yes``
    are equivalent.  A subcommand-level ``--config`` overrides the global one.

    :param ctx: Click context.
    :param dry_run: Subcommand-level ``--dry-run`` flag.
    :param yes: Subcommand-level ``--yes`` flag.
    :param quiet: Subcommand-level ``--quiet`` flag.
    :param config_path: Subcommand-level ``--config`` path.
    :returns: Updated VrznContext.
    """
    vctx: VrznContext = ctx.obj["vrzn"]
    if dry_run:
        vctx.dry_run = True
    if yes:
        vctx.yes = True
    if quiet:
        vctx.quiet = True
    if config_path is not None:
        vctx.config_path = config_path
    return vctx


def _load_or_exit(vctx: VrznContext, ctx: click.Context) -> list[VersionLocation]:
    """Load locations from config, printing errors and exiting on failure."""
    try:
        return vctx.load()
    except ConfigError as e:
        err_console.print(f"[red]{e}[/red]")
        ctx.exit(2)
        return []  # unreachable, satisfies type checker


@cli.command()
@_common_options
@click.pass_context
def get(ctx: click.Context, dry_run: bool, yes: bool, quiet: bool, config_path: Path | None):
    """Display the current version in all configured files."""
    vctx = _merge_globals(ctx, dry_run, yes, quiet, config_path)
    locations = _load_or_exit(vctx, ctx)
    if not locations:
        return
    consensus, mismatches = check_agreement(locations)

    if vctx.quiet:
        if consensus:
            click.echo(consensus.normalized)
        ctx.exit(1 if mismatches else 0)
        return

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

        if loc.format == VersionFormat.COMPONENT:
            raw = loc.read_version()
            if raw is None:
                table.add_row(rel_path, loc.label, "-", "[yellow]not found[/yellow]")
            else:
                table.add_row(rel_path, loc.label, raw, "[green]ok[/green]")
            continue

        parsed = loc.read_version_parsed()

        if parsed is None:
            table.add_row(rel_path, loc.label, "-", "[yellow]not found[/yellow]")
        elif id(loc) in mismatch_locs:
            ver_display = parsed.base if loc.format == VersionFormat.BASE else parsed.normalized
            table.add_row(rel_path, loc.label, f"[red]{ver_display}[/red]", "[red]mismatch[/red]")
        else:
            ver_display = parsed.base if loc.format == VersionFormat.BASE else parsed.normalized
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

    ctx.exit(1 if mismatches else 0)


@cli.command("set")
@click.argument("version")
@_common_options
@click.pass_context
def set_version(ctx: click.Context, version: str, dry_run: bool, yes: bool, quiet: bool,
                config_path: Path | None):
    """Set all version numbers to VERSION across all configured files.

    VERSION supports full PEP 440 specification (e.g., 1.0.0, 1.0.0rc1, 1.0.0.post1).
    Non-normalized forms are accepted and automatically normalized.
    """
    vctx = _merge_globals(ctx, dry_run, yes, quiet, config_path)

    try:
        ver = parse_version(version)
    except ValueError:
        err_console.print(f"[red]Invalid version format: {version}[/red]")
        err_console.print("  Expected PEP 440 version (e.g., 1.0.0, 1.0.0rc1, 1.0.0.post1)")
        ctx.exit(1)
        return

    locations = _load_or_exit(vctx, ctx)
    if not locations:
        return

    if not vctx.quiet:
        console.print()
        console.print(f"  Setting version to [bold green]{ver.normalized}[/bold green]")
        console.print()

    if not vctx.dry_run and not vctx.yes:
        if not click.confirm("  Proceed?"):
            console.print("\n  [dim]Aborted.[/dim]\n")
            return
        console.print()

    table = _update_all(locations, ver, vctx)
    if not vctx.quiet:
        console.print(table)
        console.print()
        if vctx.dry_run:
            console.print("  [yellow]Dry run — no files were modified.[/yellow]")
        else:
            console.print(f"  [green]All versions set to {ver.normalized}.[/green]")
        console.print()


def _update_all(locations: list[VersionLocation], ver: Version, vctx: "VrznContext") -> Table:
    """Update all version locations and return a results table.

    :param locations: List of version locations to update.
    :param ver: Target version to write.
    :param vctx: VrznContext with dry_run and project_root.
    :returns: Rich Table with update results.
    """
    table = Table(
        title="dry run" if vctx.dry_run else "updated files",
        box=box.ROUNDED,
        show_lines=False,
        title_style="bold yellow" if vctx.dry_run else "bold green",
        header_style="bold",
    )
    table.add_column("File", style="blue", max_width=45)
    table.add_column("Location", style="dim")
    table.add_column("Current", justify="center")
    table.add_column("New", justify="center")
    table.add_column("Result", justify="center")

    for loc in locations:
        rel_path = _relative_path(loc.file, vctx.project_root)
        target_str = ver.normalized if loc.format == VersionFormat.FULL else ver.base
        current = loc.read_version() or "-"

        if not loc.file.exists():
            table.add_row(rel_path, loc.label, "-", target_str, "[yellow]skipped (not found)[/yellow]")
            continue

        if vctx.dry_run:
            table.add_row(rel_path, loc.label, current, target_str, "[cyan]would update[/cyan]")
        else:
            ok = loc.write_version(ver)
            if ok:
                table.add_row(rel_path, loc.label, current, target_str, "[green]updated[/green]")
            else:
                table.add_row(rel_path, loc.label, current, target_str, "[red]pattern not matched[/red]")

    return table


# Valid pre-release labels for the --pre option
_PRE_LABELS = {"alpha": "a", "a": "a", "beta": "b", "b": "b", "rc": "rc"}


@cli.command()
@click.argument("part", type=click.Choice(["major", "minor", "patch", "pre", "release"]))
@click.option("--pre", "pre_label", type=click.Choice(["alpha", "a", "beta", "b", "rc"]),
              default=None, help="Start or promote a pre-release with this label.")
@_common_options
@click.pass_context
def bump(ctx: click.Context, part: str, pre_label: str | None, dry_run: bool, yes: bool,
         quiet: bool, config_path: Path | None):
    """Bump the version number across all configured files.

    PART must be one of: major, minor, patch, pre, release.
    Use --pre to enter or promote a pre-release state.
    """
    vctx = _merge_globals(ctx, dry_run, yes, quiet, config_path)
    locations = _load_or_exit(vctx, ctx)
    if not locations:
        return
    consensus, mismatches = check_agreement(locations)

    if consensus is None:
        err_console.print("[red]Could not read any version from configured locations.[/red]")
        ctx.exit(1)
        return

    if mismatches and not vctx.yes and not vctx.dry_run:
        err_console.print(f"[yellow]Warning: {len(mismatches)} location(s) out of sync.[/yellow]")
        if not click.confirm("  Continue with bump from consensus version?"):
            console.print("\n  [dim]Aborted.[/dim]\n")
            return

    # Normalize the pre-release label
    normalized_label = _PRE_LABELS[pre_label] if pre_label else None

    try:
        if part == "major":
            new = consensus.bump_major(pre_label=normalized_label)
        elif part == "minor":
            new = consensus.bump_minor(pre_label=normalized_label)
        elif part == "patch":
            new = consensus.bump_patch(pre_label=normalized_label)
        elif part == "pre":
            new = consensus.bump_pre(label=normalized_label)
        elif part == "release":
            new = consensus.bump_release()
        else:
            err_console.print(f"[red]Unknown part: {part}[/red]")
            ctx.exit(1)
            return
    except ValueError as e:
        err_console.print(f"[red]{e}[/red]")
        ctx.exit(1)
        return

    if not vctx.quiet:
        console.print()
        console.print(
            f"  Version bump: [bold red]{consensus.normalized}[/bold red] "
            f"\u2192 [bold green]{new.normalized}[/bold green]"
        )
        console.print()

    if not vctx.dry_run and not vctx.yes:
        if not click.confirm("  Proceed?"):
            console.print("\n  [dim]Aborted.[/dim]\n")
            return
        console.print()

    table = _update_all(locations, new, vctx)
    if not vctx.quiet:
        console.print(table)
        console.print()
        if vctx.dry_run:
            console.print("  [yellow]Dry run \u2014 no files were modified.[/yellow]")
        else:
            console.print(f"  [green]Version bumped to {new.normalized}.[/green]")
        console.print()


def _relative_path(path: Path, root: Path) -> str:
    """Return path relative to root, or absolute if not under root."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def main():
    """Entry point for the vrzn CLI."""
    cli()
