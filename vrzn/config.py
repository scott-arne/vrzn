"""Configuration file discovery, loading, and validation."""

import json
import sys
from pathlib import Path
from typing import Any, Optional

from vrzn.presets import PRESET_REGISTRY

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib
    except ImportError as e:
        raise ImportError("Install 'tomli' for Python < 3.11: pip install tomli") from e


class ConfigError(Exception):
    """Raised when the vrzn configuration is invalid."""


_CONFIG_FILENAMES = ("vrzn.toml", "vrzn.yaml", "vrzn.json", "pyproject.toml")


def find_config(start_dir: Optional[Path] = None) -> Optional[Path]:
    """Walk up from start_dir looking for a vrzn config file.

    :param start_dir: Directory to start searching from. Defaults to CWD.
    :returns: Path to config file, or None if not found.
    """
    from rich.console import Console
    err_console = Console(stderr=True)

    current = (start_dir or Path.cwd()).resolve()
    while True:
        found: list[Path] = []
        for name in _CONFIG_FILENAMES:
            candidate = current / name
            if candidate.is_file():
                if name == "pyproject.toml":
                    if _pyproject_has_vrzn(candidate):
                        found.append(candidate)
                else:
                    found.append(candidate)

        if found:
            if len(found) > 1:
                others = ", ".join(f.name for f in found[1:])
                err_console.print(
                    f"[yellow]Warning: multiple config files found in {current}. "
                    f"Using {found[0].name}, ignoring {others}.[/yellow]"
                )
            return found[0]

        parent = current.parent
        if parent == current:
            break
        current = parent
    return None


def _pyproject_has_vrzn(path: Path) -> bool:
    """Check if a pyproject.toml contains [tool.vrzn]."""
    with open(path, "rb") as f:
        data = tomllib.load(f)
    return "vrzn" in data.get("tool", {})


def load_config(config_path: Path) -> dict[str, Any]:
    """Load and return the vrzn configuration from a config file.

    :param config_path: Path to the config file.
    :returns: Parsed configuration dict with a "locations" key.
    :raises ConfigError: If the file cannot be parsed.
    """
    name = config_path.name
    try:
        if name.endswith(".toml"):
            with open(config_path, "rb") as f:
                data = tomllib.load(f)
            if name == "pyproject.toml":
                data = data.get("tool", {}).get("vrzn", {})
            return data
        elif name.endswith(".json"):
            with open(config_path, encoding="utf-8") as f:
                return json.load(f)
        elif name.endswith((".yaml", ".yml")):
            try:
                import yaml
            except ImportError:
                raise ConfigError(
                    "YAML config requires PyYAML. Install it with: pip install 'vrzn[yaml]'"
                )
            with open(config_path, encoding="utf-8") as f:
                return yaml.safe_load(f)
        else:
            raise ConfigError(f"Unsupported config file format: {name}")
    except (json.JSONDecodeError, Exception) as e:
        if isinstance(e, ConfigError):
            raise
        raise ConfigError(f"Failed to parse {config_path}: {e}") from e


def validate_config(config: dict[str, Any]) -> None:
    """Validate a parsed vrzn configuration.

    :param config: Parsed configuration dict.
    :raises ConfigError: If the configuration is invalid.
    """
    if "locations" not in config:
        raise ConfigError("Config missing required 'locations' key")

    locations = config["locations"]
    if not locations:
        raise ConfigError("No locations defined in config")

    for i, loc in enumerate(locations):
        prefix = f"locations[{i}]"

        if "file" not in loc:
            raise ConfigError(f"{prefix}: missing required 'file' key")
        if "type" not in loc:
            raise ConfigError(f"{prefix}: missing required 'type' key")

        loc_type = loc["type"]

        if loc_type == "custom":
            for field in ("pattern", "replacement", "extract"):
                if field not in loc:
                    raise ConfigError(f"{prefix}: custom type requires '{field}' key")
        elif loc_type == "c-define":
            if "prefix" not in loc:
                raise ConfigError(f"{prefix}: c-define type requires 'prefix' key")
        elif loc_type not in PRESET_REGISTRY:
            raise ConfigError(f"{prefix}: Unknown preset type '{loc_type}'")
