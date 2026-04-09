import json
import pytest
from pathlib import Path
from click.testing import CliRunner
from vrzn.cli import cli


@pytest.fixture
def project(tmp_path):
    """Create a minimal project with vrzn config and version files."""
    # Config
    config = tmp_path / "vrzn.toml"
    config.write_text(
        '[[locations]]\nfile = "pyproject.toml"\ntype = "pyproject-version"\n\n'
        '[[locations]]\nfile = "src/__init__.py"\ntype = "python-dunder"\n',
        encoding="utf-8",
    )
    # Version files
    (tmp_path / "pyproject.toml").write_text('version = "1.2.3"\n', encoding="utf-8")
    src = tmp_path / "src"
    src.mkdir()
    (src / "__init__.py").write_text('__version__ = "1.2.3"\n', encoding="utf-8")
    return tmp_path


@pytest.fixture
def runner():
    return CliRunner()


class TestGet:
    """Test vrzn get command."""

    def test_get_shows_versions(self, runner, project):
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "get"])
        assert result.exit_code == 0
        assert "1.2.3" in result.output

    def test_get_quiet_outputs_version_only(self, runner, project):
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--quiet", "get"])
        assert result.exit_code == 0
        assert result.output.strip() == "1.2.3"

    def test_get_mismatch_exit_code(self, runner, project):
        (project / "src" / "__init__.py").write_text('__version__ = "9.9.9"\n', encoding="utf-8")
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "get"])
        assert result.exit_code == 1

    def test_get_missing_config_exit_code(self, runner, tmp_path):
        result = runner.invoke(cli, ["--config", str(tmp_path / "nonexistent.toml"), "get"])
        assert result.exit_code == 2
