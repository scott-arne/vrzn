# vrzn

**Author:** Scott Arne Johnson ([scott.arne.johnson@gmail.com](mailto:scott.arne.johnson@gmail.com))

Language-agnostic version management across project files.

## Installation

```bash
pip install vrzn
```

For YAML config support:

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

Then use vrzn to manage your versions:

```bash
# See all version locations and their status
vrzn get

# Set a specific version everywhere
vrzn set 1.0.0

# Bump the version
vrzn bump patch          # 1.0.0 -> 1.0.1
vrzn bump minor          # 1.0.1 -> 1.1.0
vrzn bump major          # 1.1.0 -> 2.0.0

# Pre-release workflows
vrzn bump patch --pre rc  # 2.0.0 -> 2.0.1rc1
vrzn bump pre             # 2.0.1rc1 -> 2.0.1rc2
vrzn bump release         # 2.0.1rc2 -> 2.0.1
```

## Configuration

vrzn searches up the directory tree for config in this order:
1. `vrzn.toml`
2. `vrzn.yaml`
3. `vrzn.json`
4. `pyproject.toml` (under `[tool.vrzn]`)

### Built-in Presets

| Preset | Matches | base_only |
|--------|---------|-----------|
| `pyproject-version` | `version = "X.Y.Z"` in TOML | no |
| `python-dunder` | `__version__ = "X.Y.Z"` | no |
| `python-version-info` | `__version_info__ = (X, Y, Z)` | yes |
| `cmake-project` | `project(NAME VERSION X.Y.Z)` | yes |
| `c-define` | `#define PREFIX_VERSION_MAJOR N` | yes |
| `cargo-toml` | `version = "X.Y.Z"` in Cargo.toml | no |
| `package-json` | `"version": "X.Y.Z"` in JSON | no |
| `maven-pom` | `<version>X.Y.Z</version>` | no |
| `gradle-version` | `version = 'X.Y.Z'` in Gradle | no |

### Custom Locations

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
