import re
import pytest
from vrzn.presets import get_preset, Preset, PRESET_REGISTRY


def _single_preset(name: str) -> Preset:
    """Get a preset that is expected to be a single Preset, not a list."""
    result = get_preset(name)
    assert isinstance(result, Preset)
    return result


# Sample file contents for testing
PYPROJECT_TOML = '''
[project]
name = "mypackage"
version = "1.2.3"
description = "A test"
'''

PYTHON_DUNDER = '''
"""My package."""
__version__ = "1.2.3"
__all__ = ["main"]
'''

PYTHON_VERSION_INFO = '''
__version_info__ = (1, 2, 3)
__version__ = "1.2.3"
'''

CMAKE_CONTENT = '''
cmake_minimum_required(VERSION 3.20)
project(mylib VERSION 1.2.3 LANGUAGES CXX)
'''

C_HEADER = '''
#ifndef MYLIB_H
#define MYLIB_VERSION_MAJOR 1
#define MYLIB_VERSION_MINOR 2
#define MYLIB_VERSION_PATCH 3
#endif
'''

CARGO_TOML = '''
[package]
name = "mylib"
version = "1.2.3"
edition = "2021"
'''

PACKAGE_JSON = '''
{
  "name": "mypackage",
  "version": "1.2.3",
  "description": "A test"
}
'''

MAVEN_POM = '''
<project>
  <groupId>com.example</groupId>
  <artifactId>myapp</artifactId>
  <version>1.2.3</version>
</project>
'''

GRADLE_SINGLE = '''
plugins {
    id 'java'
}
version = '1.2.3'
'''

GRADLE_DOUBLE = '''
plugins {
    id 'java'
}
version "1.2.3"
'''


class TestPresetExtract:
    """Test that each preset's extract regex finds the version."""

    def test_pyproject_version(self):
        preset = _single_preset("pyproject-version")
        m = re.search(preset.extract, PYPROJECT_TOML, re.MULTILINE)
        assert m and m.group(1) == "1.2.3"

    def test_python_dunder(self):
        preset = _single_preset("python-dunder")
        m = re.search(preset.extract, PYTHON_DUNDER, re.MULTILINE)
        assert m and m.group(1) == "1.2.3"

    def test_python_version_info(self):
        preset = _single_preset("python-version-info")
        m = re.search(preset.extract, PYTHON_VERSION_INFO, re.MULTILINE)
        assert m and m.group(1) == "1, 2, 3"

    def test_cmake_project(self):
        preset = _single_preset("cmake-project")
        m = re.search(preset.extract, CMAKE_CONTENT, re.MULTILINE)
        assert m and m.group(1) == "1.2.3"

    def test_c_define(self):
        presets = get_preset("c-define", prefix="MYLIB")
        assert isinstance(presets, list)
        assert len(presets) == 3
        for p in presets:
            m = re.search(p.extract, C_HEADER, re.MULTILINE)
            assert m is not None

    def test_cargo_toml(self):
        preset = _single_preset("cargo-toml")
        m = re.search(preset.extract, CARGO_TOML, re.MULTILINE)
        assert m and m.group(1) == "1.2.3"

    def test_package_json(self):
        preset = _single_preset("package-json")
        m = re.search(preset.extract, PACKAGE_JSON, re.MULTILINE)
        assert m and m.group(1) == "1.2.3"

    def test_maven_pom(self):
        preset = _single_preset("maven-pom")
        m = re.search(preset.extract, MAVEN_POM, re.MULTILINE)
        assert m and m.group(1) == "1.2.3"

    def test_gradle_single_quotes(self):
        preset = _single_preset("gradle-version")
        m = re.search(preset.extract, GRADLE_SINGLE, re.MULTILINE)
        assert m and m.group(1) == "1.2.3"

    def test_gradle_double_quotes(self):
        preset = _single_preset("gradle-version")
        m = re.search(preset.extract, GRADLE_DOUBLE, re.MULTILINE)
        assert m and m.group(1) == "1.2.3"


class TestPresetReplace:
    """Test that each preset's pattern/replacement correctly updates the version."""

    def test_pyproject_version(self):
        preset = _single_preset("pyproject-version")
        result = re.sub(preset.pattern, preset.replacement.format(version="2.0.0"), PYPROJECT_TOML, flags=re.MULTILINE)
        assert 'version = "2.0.0"' in result

    def test_python_dunder(self):
        preset = _single_preset("python-dunder")
        result = re.sub(preset.pattern, preset.replacement.format(version="2.0.0"), PYTHON_DUNDER, flags=re.MULTILINE)
        assert '__version__ = "2.0.0"' in result

    def test_cmake_project(self):
        preset = _single_preset("cmake-project")
        result = re.sub(
            preset.pattern,
            preset.replacement.format(major=2, minor=0, patch=0, version="2.0.0", info_tuple="2, 0, 0"),
            CMAKE_CONTENT,
            flags=re.MULTILINE,
        )
        assert "VERSION 2.0.0" in result

    def test_package_json(self):
        preset = _single_preset("package-json")
        result = re.sub(preset.pattern, preset.replacement.format(version="2.0.0"), PACKAGE_JSON, flags=re.MULTILINE)
        assert '"version": "2.0.0"' in result


class TestPresetRegistry:
    """Test registry lookup and error handling."""

    def test_unknown_preset_raises(self):
        with pytest.raises(KeyError):
            get_preset("nonexistent")

    def test_c_define_missing_prefix_raises(self):
        with pytest.raises(ValueError, match="prefix"):
            get_preset("c-define")

    def test_all_presets_have_required_fields(self):
        for name in PRESET_REGISTRY:
            if name == "c-define":
                continue  # parameterized
            preset = _single_preset(name)
            assert preset.pattern
            assert preset.replacement
            assert preset.extract
