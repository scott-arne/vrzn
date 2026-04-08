import pytest
from pathlib import Path
from vrzn.version import Version
from vrzn.locations import VersionLocation, locations_from_config, check_agreement


class TestVersionLocationRead:
    """Test reading versions from files."""

    def test_read_version(self, tmp_path):
        f = tmp_path / "pyproject.toml"
        f.write_text('version = "1.2.3"\n', encoding="utf-8")
        loc = VersionLocation(
            file=f, label="test",
            pattern=r'(^version\s*=\s*")[^"]+(")',
            replacement=r'\g<1>{version}\g<2>',
            extract=r'^version\s*=\s*"([^"]+)"',
            base_only=False,
        )
        assert loc.read_version() == "1.2.3"

    def test_read_version_not_found(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("nothing here\n", encoding="utf-8")
        loc = VersionLocation(
            file=f, label="test",
            pattern="x", replacement="y",
            extract=r'version = "([^"]+)"',
            base_only=False,
        )
        assert loc.read_version() is None

    def test_read_version_file_missing(self, tmp_path):
        loc = VersionLocation(
            file=tmp_path / "missing.txt", label="test",
            pattern="x", replacement="y", extract="x",
            base_only=False,
        )
        assert loc.read_version() is None

    def test_read_version_parsed(self, tmp_path):
        f = tmp_path / "init.py"
        f.write_text('__version__ = "1.0.0rc1"\n', encoding="utf-8")
        loc = VersionLocation(
            file=f, label="test",
            pattern=r'(__version__\s*=\s*")[^"]+(")',
            replacement=r'\g<1>{version}\g<2>',
            extract=r'__version__\s*=\s*"([^"]+)"',
            base_only=False,
        )
        v = loc.read_version_parsed()
        assert v == Version(1, 0, 0, pre=("rc", 1))


class TestVersionLocationWrite:
    """Test writing versions to files."""

    def test_write_version(self, tmp_path):
        f = tmp_path / "pyproject.toml"
        f.write_text('version = "1.0.0"\n', encoding="utf-8")
        loc = VersionLocation(
            file=f, label="test",
            pattern=r'(^version\s*=\s*")[^"]+(")',
            replacement=r'\g<1>{version}\g<2>',
            extract=r'^version\s*=\s*"([^"]+)"',
            base_only=False,
        )
        result = loc.write_version(Version(2, 0, 0))
        assert result is True
        assert 'version = "2.0.0"' in f.read_text(encoding="utf-8")

    def test_write_version_base_only(self, tmp_path):
        f = tmp_path / "CMakeLists.txt"
        f.write_text("project(mylib VERSION 1.0.0 LANGUAGES CXX)\n", encoding="utf-8")
        loc = VersionLocation(
            file=f, label="test",
            pattern=r"(project\([^\)]*VERSION\s+)\d+\.\d+\.\d+",
            replacement=r"\g<1>{major}.{minor}.{patch}",
            extract=r"project\([^\)]*VERSION\s+(\d+\.\d+\.\d+)",
            base_only=True,
        )
        result = loc.write_version(Version(2, 0, 0, pre=("rc", 1)))
        assert result is True
        assert "VERSION 2.0.0" in f.read_text(encoding="utf-8")

    def test_write_version_pattern_not_matched(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("nothing here\n", encoding="utf-8")
        loc = VersionLocation(
            file=f, label="test",
            pattern=r'(version = ")[^"]+(")',
            replacement=r'\g<1>{version}\g<2>',
            extract=r'version = "([^"]+)"',
            base_only=False,
        )
        result = loc.write_version(Version(2, 0, 0))
        assert result is False

    def test_write_version_info_tuple(self, tmp_path):
        f = tmp_path / "__init__.py"
        f.write_text("__version_info__ = (1, 0, 0)\n", encoding="utf-8")
        loc = VersionLocation(
            file=f, label="test",
            pattern=r"(__version_info__\s*=\s*\()[^)]+(\))",
            replacement=r"\g<1>{info_tuple}\g<2>",
            extract=r"__version_info__\s*=\s*\(([^)]+)\)",
            base_only=True,
        )
        result = loc.write_version(Version(2, 3, 4, pre=("rc", 1)))
        assert result is True
        assert "__version_info__ = (2, 3, 4)" in f.read_text(encoding="utf-8")

    def test_write_version_file_missing(self, tmp_path):
        loc = VersionLocation(
            file=tmp_path / "missing.txt", label="test",
            pattern="x", replacement="y", extract="x",
            base_only=False,
        )
        result = loc.write_version(Version(2, 0, 0))
        assert result is False


class TestLocationsFromConfig:
    """Test building VersionLocation list from config."""

    def test_preset_location(self, tmp_path):
        config = {"locations": [{"file": "pyproject.toml", "type": "pyproject-version"}]}
        locations = locations_from_config(config, project_root=tmp_path)
        assert len(locations) == 1
        assert locations[0].label == "pyproject-version"
        assert locations[0].file == tmp_path / "pyproject.toml"

    def test_custom_location(self, tmp_path):
        config = {"locations": [{
            "file": "conf.py", "type": "custom",
            "label": "Sphinx", "pattern": "p", "replacement": "r", "extract": "e",
        }]}
        locations = locations_from_config(config, project_root=tmp_path)
        assert locations[0].label == "Sphinx"

    def test_custom_location_default_label(self, tmp_path):
        config = {"locations": [{
            "file": "conf.py", "type": "custom",
            "pattern": "p", "replacement": "r", "extract": "e",
        }]}
        locations = locations_from_config(config, project_root=tmp_path)
        assert locations[0].label == "custom"

    def test_c_define_expands(self, tmp_path):
        config = {"locations": [{"file": "mylib.h", "type": "c-define", "prefix": "MYLIB"}]}
        locations = locations_from_config(config, project_root=tmp_path)
        assert len(locations) == 3

    def test_label_override(self, tmp_path):
        config = {"locations": [{"file": "pyproject.toml", "type": "pyproject-version", "label": "My Label"}]}
        locations = locations_from_config(config, project_root=tmp_path)
        assert locations[0].label == "My Label"


class TestCheckAgreement:
    """Test version agreement checking."""

    def test_all_agree(self, tmp_path):
        f1 = tmp_path / "a.toml"
        f2 = tmp_path / "b.py"
        f1.write_text('version = "1.0.0"\n', encoding="utf-8")
        f2.write_text('__version__ = "1.0.0"\n', encoding="utf-8")
        locations = [
            VersionLocation(f1, "a", "", "", r'^version\s*=\s*"([^"]+)"', False),
            VersionLocation(f2, "b", "", "", r'__version__\s*=\s*"([^"]+)"', False),
        ]
        consensus, mismatches = check_agreement(locations)
        assert consensus == Version(1, 0, 0)
        assert len(mismatches) == 0

    def test_mismatch_detected(self, tmp_path):
        f1 = tmp_path / "a.toml"
        f2 = tmp_path / "b.py"
        f1.write_text('version = "1.0.0"\n', encoding="utf-8")
        f2.write_text('__version__ = "2.0.0"\n', encoding="utf-8")
        locations = [
            VersionLocation(f1, "a", "", "", r'^version\s*=\s*"([^"]+)"', False),
            VersionLocation(f2, "b", "", "", r'__version__\s*=\s*"([^"]+)"', False),
        ]
        consensus, mismatches = check_agreement(locations)
        assert len(mismatches) == 1

    def test_tiebreaker_first_listed(self, tmp_path):
        f1 = tmp_path / "a.toml"
        f2 = tmp_path / "b.py"
        f1.write_text('version = "1.0.0"\n', encoding="utf-8")
        f2.write_text('__version__ = "2.0.0"\n', encoding="utf-8")
        locations = [
            VersionLocation(f1, "a", "", "", r'^version\s*=\s*"([^"]+)"', False),
            VersionLocation(f2, "b", "", "", r'__version__\s*=\s*"([^"]+)"', False),
        ]
        consensus, _ = check_agreement(locations)
        assert consensus == Version(1, 0, 0)

    def test_majority_wins_over_first_listed(self, tmp_path):
        f1 = tmp_path / "a.toml"
        f2 = tmp_path / "b.py"
        f3 = tmp_path / "c.py"
        f1.write_text('version = "1.0.0"\n', encoding="utf-8")
        f2.write_text('__version__ = "2.0.0"\n', encoding="utf-8")
        f3.write_text('__version__ = "2.0.0"\n', encoding="utf-8")
        locations = [
            VersionLocation(f1, "a", "", "", r'^version\s*=\s*"([^"]+)"', False),
            VersionLocation(f2, "b", "", "", r'__version__\s*=\s*"([^"]+)"', False),
            VersionLocation(f3, "c", "", "", r'__version__\s*=\s*"([^"]+)"', False),
        ]
        consensus, mismatches = check_agreement(locations)
        assert consensus == Version(2, 0, 0)
        assert len(mismatches) == 1

    def test_no_readable_returns_none(self, tmp_path):
        locations = [
            VersionLocation(tmp_path / "missing.txt", "a", "", "", "x", False),
        ]
        consensus, mismatches = check_agreement(locations)
        assert consensus is None
