import re
import pytest
from pathlib import Path
from vrzn.version import Version
from vrzn.locations import (
    VersionFormat, VersionLocation, compile_template,
    locations_from_config, check_agreement,
)


class TestCompileTemplate:
    """Test the compile_template function."""

    # --- Format detection ---

    def test_full_format_for_version_placeholder(self):
        loc = compile_template(Path("f"), "test", r'^version = "{version}"')
        assert loc.format == VersionFormat.FULL

    def test_base_format_for_base_placeholder(self):
        loc = compile_template(Path("f"), "test", r"VERSION\s+{base}")
        assert loc.format == VersionFormat.BASE

    def test_base_format_for_info_tuple_placeholder(self):
        loc = compile_template(Path("f"), "test", r"\({info_tuple}\)")
        assert loc.format == VersionFormat.BASE

    def test_component_format_for_major(self):
        loc = compile_template(Path("f"), "test", r"MAJOR\s+{major}")
        assert loc.format == VersionFormat.COMPONENT

    def test_component_format_for_minor(self):
        loc = compile_template(Path("f"), "test", r"MINOR\s+{minor}")
        assert loc.format == VersionFormat.COMPONENT

    def test_component_format_for_patch(self):
        loc = compile_template(Path("f"), "test", r"PATCH\s+{patch}")
        assert loc.format == VersionFormat.COMPONENT

    # --- Error cases ---

    def test_no_placeholder_raises(self):
        with pytest.raises(ValueError, match="no recognized placeholder"):
            compile_template(Path("f"), "test", r"version = something")

    def test_multiple_placeholders_raises(self):
        with pytest.raises(ValueError, match="multiple placeholders"):
            compile_template(Path("f"), "test", r"{major}.{minor}")

    def test_unrecognized_placeholder_not_matched(self):
        """A {foo} placeholder is not in the known set, so treated as no placeholder."""
        with pytest.raises(ValueError, match="no recognized placeholder"):
            compile_template(Path("f"), "test", r"version = {foo}")

    # --- Extraction (read) ---

    def test_extract_full_version(self, tmp_path):
        f = tmp_path / "pyproject.toml"
        f.write_text('version = "1.2.3rc1"\n', encoding="utf-8")
        loc = compile_template(f, "test", r'^version\s*=\s*"{version}"')
        assert loc.read_version() == "1.2.3rc1"

    def test_extract_base_version(self, tmp_path):
        f = tmp_path / "CMakeLists.txt"
        f.write_text("project(mylib VERSION 1.2.3 LANGUAGES CXX)\n", encoding="utf-8")
        loc = compile_template(f, "test", r"project\([^\)]*VERSION\s+{base}")
        assert loc.read_version() == "1.2.3"

    def test_extract_info_tuple(self, tmp_path):
        f = tmp_path / "__init__.py"
        f.write_text("__version_info__ = (1, 2, 3)\n", encoding="utf-8")
        loc = compile_template(f, "test", r"__version_info__\s*=\s*\({info_tuple}\)")
        assert loc.read_version() == "1, 2, 3"

    def test_extract_major(self, tmp_path):
        f = tmp_path / "mylib.h"
        f.write_text("#define MYLIB_VERSION_MAJOR 42\n", encoding="utf-8")
        loc = compile_template(f, "test", r"#define\s+MYLIB_VERSION_MAJOR\s+{major}")
        assert loc.read_version() == "42"

    def test_extract_minor(self, tmp_path):
        f = tmp_path / "mylib.h"
        f.write_text("#define MYLIB_VERSION_MINOR 7\n", encoding="utf-8")
        loc = compile_template(f, "test", r"#define\s+MYLIB_VERSION_MINOR\s+{minor}")
        assert loc.read_version() == "7"

    def test_extract_patch(self, tmp_path):
        f = tmp_path / "mylib.h"
        f.write_text("#define MYLIB_VERSION_PATCH 99\n", encoding="utf-8")
        loc = compile_template(f, "test", r"#define\s+MYLIB_VERSION_PATCH\s+{patch}")
        assert loc.read_version() == "99"

    # --- Write ---

    def test_write_full_version(self, tmp_path):
        f = tmp_path / "pyproject.toml"
        f.write_text('version = "1.0.0"\n', encoding="utf-8")
        loc = compile_template(f, "test", r'^version\s*=\s*"{version}"')
        assert loc.write_version(Version(2, 0, 0, pre=("rc", 1))) is True
        assert 'version = "2.0.0rc1"' in f.read_text(encoding="utf-8")

    def test_write_base_version(self, tmp_path):
        f = tmp_path / "CMakeLists.txt"
        f.write_text("project(mylib VERSION 1.0.0 LANGUAGES CXX)\n", encoding="utf-8")
        loc = compile_template(f, "test", r"project\([^\)]*VERSION\s+{base}")
        assert loc.write_version(Version(2, 3, 4, pre=("rc", 1))) is True
        content = f.read_text(encoding="utf-8")
        assert "VERSION 2.3.4" in content
        # Pre-release suffix should NOT appear (base_only)
        assert "rc1" not in content

    def test_write_info_tuple(self, tmp_path):
        f = tmp_path / "__init__.py"
        f.write_text("__version_info__ = (1, 0, 0)\n", encoding="utf-8")
        loc = compile_template(f, "test", r"__version_info__\s*=\s*\({info_tuple}\)")
        assert loc.write_version(Version(2, 3, 4)) is True
        assert "__version_info__ = (2, 3, 4)" in f.read_text(encoding="utf-8")

    def test_write_major_component(self, tmp_path):
        f = tmp_path / "mylib.h"
        f.write_text("#define MYLIB_VERSION_MAJOR 1\n", encoding="utf-8")
        loc = compile_template(f, "test", r"#define\s+MYLIB_VERSION_MAJOR\s+{major}")
        assert loc.write_version(Version(9, 8, 7)) is True
        assert "MYLIB_VERSION_MAJOR 9" in f.read_text(encoding="utf-8")

    # --- No trailing context edge case ---

    def test_no_trailing_context(self, tmp_path):
        """Template with placeholder at the end (no trailing context)."""
        f = tmp_path / "CMakeLists.txt"
        f.write_text("project(mylib VERSION 1.2.3 LANGUAGES CXX)\n", encoding="utf-8")
        loc = compile_template(f, "test", r"project\([^\)]*VERSION\s+{base}")
        assert loc.read_version() == "1.2.3"

    def test_no_leading_context(self, tmp_path):
        """Template with placeholder at the start (no leading context)."""
        f = tmp_path / "ver.txt"
        f.write_text("1.2.3-suffix\n", encoding="utf-8")
        loc = compile_template(f, "test", r"{version}-suffix")
        assert loc.read_version() == "1.2.3"

    # --- Template stored on location ---

    def test_template_stored(self):
        loc = compile_template(Path("f"), "test", r'^version = "{version}"')
        assert loc.template == r'^version = "{version}"'

    def test_label_stored(self):
        loc = compile_template(Path("f"), "mylabel", r'{version}')
        assert loc.label == "mylabel"

    # --- Backward compatibility properties ---

    def test_component_property_true_for_component(self):
        loc = compile_template(Path("f"), "test", r"MAJOR\s+{major}")
        assert loc.component is True

    def test_component_property_false_for_full(self):
        loc = compile_template(Path("f"), "test", r"{version}")
        assert loc.component is False

    def test_base_only_true_for_base(self):
        loc = compile_template(Path("f"), "test", r"VERSION\s+{base}")
        assert loc.base_only is True

    def test_base_only_true_for_component(self):
        loc = compile_template(Path("f"), "test", r"MAJOR\s+{major}")
        assert loc.base_only is True

    def test_base_only_false_for_full(self):
        loc = compile_template(Path("f"), "test", r"{version}")
        assert loc.base_only is False


class TestVersionLocationRead:
    """Test reading versions from files."""

    def test_read_version(self, tmp_path):
        f = tmp_path / "pyproject.toml"
        f.write_text('version = "1.2.3"\n', encoding="utf-8")
        loc = compile_template(f, "test", r'^version\s*=\s*"{version}"')
        assert loc.read_version() == "1.2.3"

    def test_read_version_not_found(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("nothing here\n", encoding="utf-8")
        loc = compile_template(f, "test", r'^version\s*=\s*"{version}"')
        assert loc.read_version() is None

    def test_read_version_file_missing(self, tmp_path):
        loc = compile_template(tmp_path / "missing.txt", "test", r"{version}")
        assert loc.read_version() is None

    def test_read_version_parsed(self, tmp_path):
        f = tmp_path / "init.py"
        f.write_text('__version__ = "1.0.0rc1"\n', encoding="utf-8")
        loc = compile_template(f, "test", r"""__version__\s*=\s*["']{version}["']""")
        v = loc.read_version_parsed()
        assert v == Version(1, 0, 0, pre=("rc", 1))

    def test_read_version_parsed_returns_none_for_component(self, tmp_path):
        f = tmp_path / "mylib.h"
        f.write_text("#define MYLIB_VERSION_MAJOR 1\n", encoding="utf-8")
        loc = compile_template(f, "test", r"#define\s+MYLIB_VERSION_MAJOR\s+{major}")
        assert loc.read_version_parsed() is None


class TestVersionLocationWrite:
    """Test writing versions to files."""

    def test_write_version(self, tmp_path):
        f = tmp_path / "pyproject.toml"
        f.write_text('version = "1.0.0"\n', encoding="utf-8")
        loc = compile_template(f, "test", r'^version\s*=\s*"{version}"')
        result = loc.write_version(Version(2, 0, 0))
        assert result is True
        assert 'version = "2.0.0"' in f.read_text(encoding="utf-8")

    def test_write_version_base_only(self, tmp_path):
        f = tmp_path / "CMakeLists.txt"
        f.write_text("project(mylib VERSION 1.0.0 LANGUAGES CXX)\n", encoding="utf-8")
        loc = compile_template(f, "test", r"project\([^\)]*VERSION\s+{base}")
        result = loc.write_version(Version(2, 0, 0, pre=("rc", 1)))
        assert result is True
        assert "VERSION 2.0.0" in f.read_text(encoding="utf-8")

    def test_write_version_pattern_not_matched(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("nothing here\n", encoding="utf-8")
        loc = compile_template(f, "test", r'^version\s*=\s*"{version}"')
        result = loc.write_version(Version(2, 0, 0))
        assert result is False

    def test_write_version_info_tuple(self, tmp_path):
        f = tmp_path / "__init__.py"
        f.write_text("__version_info__ = (1, 0, 0)\n", encoding="utf-8")
        loc = compile_template(f, "test", r"__version_info__\s*=\s*\({info_tuple}\)")
        result = loc.write_version(Version(2, 3, 4, pre=("rc", 1)))
        assert result is True
        assert "__version_info__ = (2, 3, 4)" in f.read_text(encoding="utf-8")

    def test_write_version_file_missing(self, tmp_path):
        loc = compile_template(tmp_path / "missing.txt", "test", r"{version}")
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

    def test_c_define_expands(self, tmp_path):
        config = {"locations": [{"file": "mylib.h", "type": "c-define", "prefix": "MYLIB"}]}
        locations = locations_from_config(config, project_root=tmp_path)
        assert len(locations) == 3

    def test_label_override(self, tmp_path):
        config = {"locations": [{"file": "pyproject.toml", "type": "pyproject-version", "label": "My Label"}]}
        locations = locations_from_config(config, project_root=tmp_path)
        assert locations[0].label == "My Label"

    def test_component_format_propagated_from_config(self, tmp_path):
        """locations_from_config sets format=COMPONENT for c-define entries."""
        config = {"locations": [{"file": "mylib.h", "type": "c-define", "prefix": "MYLIB"}]}
        locations = locations_from_config(config, project_root=tmp_path)
        assert len(locations) == 3
        for loc in locations:
            assert loc.format == VersionFormat.COMPONENT

    def test_custom_template_location(self, tmp_path):
        config = {"locations": [{
            "file": "conf.py", "type": "custom",
            "template": r'release\s*=\s*"{version}"',
        }]}
        locations = locations_from_config(config, project_root=tmp_path)
        assert len(locations) == 1
        assert locations[0].label == "custom"
        assert locations[0].format == VersionFormat.FULL

    def test_custom_template_location_with_label(self, tmp_path):
        config = {"locations": [{
            "file": "conf.py", "type": "custom",
            "label": "Sphinx", "template": r'release\s*=\s*"{version}"',
        }]}
        locations = locations_from_config(config, project_root=tmp_path)
        assert locations[0].label == "Sphinx"

    def test_custom_template_end_to_end(self, tmp_path):
        f = tmp_path / "conf.py"
        f.write_text('release = "1.0.0"\n', encoding="utf-8")
        config = {"locations": [{
            "file": "conf.py", "type": "custom",
            "template": r'release\s*=\s*"{version}"',
        }]}
        locations = locations_from_config(config, project_root=tmp_path)
        assert locations[0].read_version() == "1.0.0"
        locations[0].write_version(Version(2, 0, 0))
        assert 'release = "2.0.0"' in f.read_text(encoding="utf-8")


class TestCheckAgreement:
    """Test version agreement checking."""

    def test_all_agree(self, tmp_path):
        f1 = tmp_path / "a.toml"
        f2 = tmp_path / "b.py"
        f1.write_text('version = "1.0.0"\n', encoding="utf-8")
        f2.write_text('__version__ = "1.0.0"\n', encoding="utf-8")
        locations = [
            compile_template(f1, "a", r'^version\s*=\s*"{version}"'),
            compile_template(f2, "b", r"""__version__\s*=\s*["']{version}["']"""),
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
            compile_template(f1, "a", r'^version\s*=\s*"{version}"'),
            compile_template(f2, "b", r"""__version__\s*=\s*["']{version}["']"""),
        ]
        consensus, mismatches = check_agreement(locations)
        assert len(mismatches) == 1

    def test_tiebreaker_first_listed(self, tmp_path):
        f1 = tmp_path / "a.toml"
        f2 = tmp_path / "b.py"
        f1.write_text('version = "1.0.0"\n', encoding="utf-8")
        f2.write_text('__version__ = "2.0.0"\n', encoding="utf-8")
        locations = [
            compile_template(f1, "a", r'^version\s*=\s*"{version}"'),
            compile_template(f2, "b", r"""__version__\s*=\s*["']{version}["']"""),
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
            compile_template(f1, "a", r'^version\s*=\s*"{version}"'),
            compile_template(f2, "b", r"""__version__\s*=\s*["']{version}["']"""),
            compile_template(f3, "c", r"""__version__\s*=\s*["']{version}["']"""),
        ]
        consensus, mismatches = check_agreement(locations)
        assert consensus == Version(2, 0, 0)
        assert len(mismatches) == 1

    def test_no_readable_returns_none(self, tmp_path):
        locations = [
            compile_template(tmp_path / "missing.txt", "a", r"{version}"),
        ]
        consensus, mismatches = check_agreement(locations)
        assert consensus is None

    def test_component_locations_excluded_from_agreement(self, tmp_path):
        """c-define component locations should not cause mismatches."""
        f1 = tmp_path / "pyproject.toml"
        f2 = tmp_path / "mylib.h"
        f1.write_text('version = "1.2.3"\n', encoding="utf-8")
        f2.write_text(
            "#define MYLIB_VERSION_MAJOR 1\n"
            "#define MYLIB_VERSION_MINOR 2\n"
            "#define MYLIB_VERSION_PATCH 3\n",
            encoding="utf-8",
        )
        locations = [
            compile_template(f1, "pyproject", r'^version\s*=\s*"{version}"'),
            compile_template(f2, "c-define (MAJOR)", r"#define\s+MYLIB_VERSION_MAJOR\s+{major}"),
            compile_template(f2, "c-define (MINOR)", r"#define\s+MYLIB_VERSION_MINOR\s+{minor}"),
            compile_template(f2, "c-define (PATCH)", r"#define\s+MYLIB_VERSION_PATCH\s+{patch}"),
        ]
        consensus, mismatches = check_agreement(locations)
        assert consensus == Version(1, 2, 3)
        assert len(mismatches) == 0
