# vrzn

**Author:** Scott Arne Johnson ([scott.arne.johnson@gmail.com](mailto:scott.arne.johnson@gmail.com))

Language-agnostic version management across project files.

## Overview

Projects often store version numbers in multiple files: `pyproject.toml`, `__init__.py`, `CMakeLists.txt`, `package.json`, and others. When these fall out of sync, builds break and releases ship incorrect metadata.

vrzn solves this by letting you declare every file that contains a version number in a single configuration file. It can then read, set, and bump versions across all of them at once, with full [PEP 440](https://peps.python.org/pep-0440/) support.

## Installation

Requires Python 3.10 or later.

```bash
pip install vrzn
```

For YAML config file support:

```bash
pip install 'vrzn[yaml]'
```

## Quick Start

Create a `vrzn.toml` in your project root:

```toml
[[locations]]
file = "pyproject.toml"
type = "pyproject-version"

[[locations]]
file = "src/mypackage/__init__.py"
type = "python-dunder"
```

Check that all version locations are in sync:

```
$ vrzn get

                       vrzn — version report
╭───────────────────────────┬───────────────────┬─────────┬────────╮
│ File                      │ Location          │ Version │ Status │
├───────────────────────────┼───────────────────┼─────────┼────────┤
│ pyproject.toml            │ pyproject-version │  1.0.0  │   ok   │
├───────────────────────────┼───────────────────┼─────────┼────────┤
│ src/mypackage/__init__.py │ python-dunder     │  1.0.0  │   ok   │
╰───────────────────────────┴───────────────────┴─────────┴────────╯

  Consensus version: 1.0.0
  All version numbers are consistent.
```

Set a specific version everywhere:

```
$ vrzn -y set 1.2.0

  Setting version to 1.2.0

                                updated files
╭───────────────────────────┬───────────────────┬─────────┬───────┬─────────╮
│ File                      │ Location          │ Current │  New  │ Result  │
├───────────────────────────┼───────────────────┼─────────┼───────┼─────────┤
│ pyproject.toml            │ pyproject-version │  1.0.0  │ 1.2.0 │ updated │
│ src/mypackage/__init__.py │ python-dunder     │  1.0.0  │ 1.2.0 │ updated │
╰───────────────────────────┴───────────────────┴─────────┴───────┴─────────╯

  All versions set to 1.2.0.
```

Bump the version:

```
$ vrzn -y bump patch

  Version bump: 1.2.0 → 1.2.1

                                updated files
╭───────────────────────────┬───────────────────┬─────────┬───────┬─────────╮
│ File                      │ Location          │ Current │  New  │ Result  │
├───────────────────────────┼───────────────────┼─────────┼───────┼─────────┤
│ pyproject.toml            │ pyproject-version │  1.2.0  │ 1.2.1 │ updated │
│ src/mypackage/__init__.py │ python-dunder     │  1.2.0  │ 1.2.1 │ updated │
╰───────────────────────────┴───────────────────┴─────────┴───────┴─────────╯

  Version bumped to 1.2.1.
```

Preview changes without writing files:

```
$ vrzn --dry-run bump minor

  Version bump: 1.2.1 → 1.3.0

                                    dry run
╭───────────────────────────┬───────────────────┬─────────┬───────┬──────────────╮
│ File                      │ Location          │ Current │  New  │    Result     │
├───────────────────────────┼───────────────────┼─────────┼───────┼──────────────┤
│ pyproject.toml            │ pyproject-version │  1.2.1  │ 1.3.0 │ would update │
│ src/mypackage/__init__.py │ python-dunder     │  1.2.1  │ 1.3.0 │ would update │
╰───────────────────────────┴───────────────────┴─────────┴───────┴──────────────╯

  Dry run — no files were modified.
```

Pre-release workflows:

```bash
vrzn -y bump patch --pre rc  # 1.0.0 -> 1.0.1rc1
vrzn -y bump pre             # 1.0.1rc1 -> 1.0.1rc2
vrzn -y bump release         # 1.0.1rc2 -> 1.0.1
```

## CLI Reference

### Global Options

Global options must be placed before the subcommand (e.g., `vrzn --dry-run bump patch`).

| Option | Description |
|--------|-------------|
| `--dry-run` | Show what would change without writing files. |
| `--yes`, `-y` | Skip confirmation prompts. |
| `--quiet`, `-q` | Machine-readable output, no tables. |
| `--config`, `-c PATH` | Path to config file (overrides discovery). |

### Commands

#### `vrzn get`

Display the current version in all configured files. Prints a table showing each location, its version, and whether it matches the consensus.

With `--quiet`, prints only the consensus version string.

**Exit codes:** `0` if all versions agree, `1` if mismatches exist, `2` if no config found.

#### `vrzn set VERSION`

Set all version numbers to VERSION. Accepts any PEP 440 version string (e.g., `1.0.0`, `1.0.0rc1`, `1.0.0.post1`). Non-normalized forms are accepted and automatically normalized.

Prompts for confirmation unless `--yes` or `--dry-run` is set.

**Exit codes:** `1` for invalid version format, `2` if no config found.

#### `vrzn bump PART [--pre LABEL]`

Bump the version number. PART must be one of: `major`, `minor`, `patch`, `pre`, `release`.

Use `--pre` with a label (`alpha`, `a`, `beta`, `b`, `rc`) to enter a pre-release state. Use `bump pre` to increment an existing pre-release. Use `bump release` to finalize a pre-release to its stable version.

If versions are out of sync, vrzn warns and uses a consensus version (most common across locations). Prompts for confirmation unless `--yes` or `--dry-run` is set.

**Exit codes:** `1` for errors (no readable version, invalid bump operation), `2` if no config found.

## Configuration

vrzn searches up the directory tree for config in this order:

1. `vrzn.toml`
2. `vrzn.yaml`
3. `vrzn.json`
4. `pyproject.toml` (under `[tool.vrzn]`)

### Built-in Presets

| Preset | Matches | `base_only` |
|--------|---------|:-----------:|
| `pyproject-version` | `version = "X.Y.Z"` in TOML | no |
| `python-dunder` | `__version__ = "X.Y.Z"` | no |
| `python-version-info` | `__version_info__ = (X, Y, Z)` | yes |
| `cmake-project` | `project(NAME VERSION X.Y.Z)` | yes |
| `c-define` | `#define PREFIX_VERSION_MAJOR N` | yes |
| `cargo-toml` | `version = "X.Y.Z"` in Cargo.toml | no |
| `package-json` | `"version": "X.Y.Z"` in JSON | no |
| `maven-pom` | `<version>X.Y.Z</version>` | no |
| `gradle-version` | `version = 'X.Y.Z'` in Gradle | no |

Presets marked `base_only` write only the `MAJOR.MINOR.PATCH` portion, ignoring pre-release or post-release suffixes.

The `c-define` preset requires a `prefix` parameter:

```toml
[[locations]]
file = "include/mylib.h"
type = "c-define"
prefix = "MYLIB"
```

### Custom Locations

For files that don't match a built-in preset, use `custom` with explicit regex patterns:

```toml
[[locations]]
file = "docs/conf.py"
type = "custom"
label = "Sphinx config"
pattern = '(release\s*=\s*")[^"]+"'
replacement = '\g<1>{version}"'
extract = 'release\s*=\s*"([^"]+)"'
```

Replacement format variables: `{version}`, `{major}`, `{minor}`, `{patch}`, `{info_tuple}`.

## Development

```bash
pip install --config-settings editable_mode=compat -e ".[dev,yaml]"
pytest
```

## License

MIT License. Copyright (c) 2026 Scott Arne Johnson. See [LICENSE](LICENSE) for details.
