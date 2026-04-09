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


class TestSet:
    """Test vrzn set command."""

    def test_set_updates_all_files(self, runner, project):
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--yes", "set", "2.0.0"])
        assert result.exit_code == 0
        assert 'version = "2.0.0"' in (project / "pyproject.toml").read_text(encoding="utf-8")
        assert '__version__ = "2.0.0"' in (project / "src" / "__init__.py").read_text(encoding="utf-8")

    def test_set_normalizes_version(self, runner, project):
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--yes", "set", "2.0.0-rc1"])
        assert result.exit_code == 0
        assert '__version__ = "2.0.0rc1"' in (project / "src" / "__init__.py").read_text(encoding="utf-8")

    def test_set_dry_run_no_changes(self, runner, project):
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--dry-run", "set", "9.9.9"])
        assert result.exit_code == 0
        assert 'version = "1.2.3"' in (project / "pyproject.toml").read_text(encoding="utf-8")

    def test_set_invalid_version(self, runner, project):
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--yes", "set", "bad"])
        assert result.exit_code == 1

    def test_set_prompts_without_yes(self, runner, project):
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "set", "2.0.0"], input="n\n")
        assert result.exit_code == 0
        assert 'version = "1.2.3"' in (project / "pyproject.toml").read_text(encoding="utf-8")


class TestBump:
    """Test vrzn bump command."""

    def test_bump_patch(self, runner, project):
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--yes", "bump", "patch"])
        assert result.exit_code == 0
        assert 'version = "1.2.4"' in (project / "pyproject.toml").read_text(encoding="utf-8")

    def test_bump_minor(self, runner, project):
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--yes", "bump", "minor"])
        assert result.exit_code == 0
        assert 'version = "1.3.0"' in (project / "pyproject.toml").read_text(encoding="utf-8")

    def test_bump_major(self, runner, project):
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--yes", "bump", "major"])
        assert result.exit_code == 0
        assert 'version = "2.0.0"' in (project / "pyproject.toml").read_text(encoding="utf-8")

    def test_bump_patch_with_pre(self, runner, project):
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--yes", "bump", "patch", "--pre", "rc"])
        assert result.exit_code == 0
        assert 'version = "1.2.4rc1"' in (project / "pyproject.toml").read_text(encoding="utf-8")

    def test_bump_pre_increments(self, runner, project):
        (project / "pyproject.toml").write_text('version = "1.0.0rc1"\n', encoding="utf-8")
        (project / "src" / "__init__.py").write_text('__version__ = "1.0.0rc1"\n', encoding="utf-8")
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--yes", "bump", "pre"])
        assert result.exit_code == 0
        assert 'version = "1.0.0rc2"' in (project / "pyproject.toml").read_text(encoding="utf-8")

    def test_bump_release_finalizes(self, runner, project):
        (project / "pyproject.toml").write_text('version = "1.0.0rc1"\n', encoding="utf-8")
        (project / "src" / "__init__.py").write_text('__version__ = "1.0.0rc1"\n', encoding="utf-8")
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--yes", "bump", "release"])
        assert result.exit_code == 0
        assert 'version = "1.0.0"' in (project / "pyproject.toml").read_text(encoding="utf-8")

    def test_bump_pre_no_active_errors(self, runner, project):
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--yes", "bump", "pre"])
        assert result.exit_code == 1

    def test_bump_release_already_final_errors(self, runner, project):
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--yes", "bump", "release"])
        assert result.exit_code == 1

    def test_bump_dry_run(self, runner, project):
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--dry-run", "bump", "patch"])
        assert result.exit_code == 0
        assert 'version = "1.2.3"' in (project / "pyproject.toml").read_text(encoding="utf-8")

    def test_bump_with_mismatch_warns(self, runner, project):
        (project / "src" / "__init__.py").write_text('__version__ = "9.9.9"\n', encoding="utf-8")
        result = runner.invoke(cli, ["--config", str(project / "vrzn.toml"), "--yes", "bump", "patch"])
        assert result.exit_code == 0  # proceeds with --yes
