import re
import pytest
from pathlib import Path
from vrzn.presets import get_preset, PRESET_REGISTRY
from vrzn.locations import compile_template
from vrzn.version import Version


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
    """Test that each preset template extracts the version via compile_template."""

    def test_pyproject_version(self, tmp_path):
        f = tmp_path / "pyproject.toml"
        f.write_text(PYPROJECT_TOML, encoding="utf-8")
        template = get_preset("pyproject-version")
        assert isinstance(template, str)
        loc = compile_template(f, "test", template)
        assert loc.read_version() == "1.2.3"

    def test_python_dunder(self, tmp_path):
        f = tmp_path / "__init__.py"
        f.write_text(PYTHON_DUNDER, encoding="utf-8")
        template = get_preset("python-dunder")
        assert isinstance(template, str)
        loc = compile_template(f, "test", template)
        assert loc.read_version() == "1.2.3"

    def test_python_version_info(self, tmp_path):
        f = tmp_path / "__init__.py"
        f.write_text(PYTHON_VERSION_INFO, encoding="utf-8")
        template = get_preset("python-version-info")
        assert isinstance(template, str)
        loc = compile_template(f, "test", template)
        assert loc.read_version() == "1, 2, 3"

    def test_cmake_project(self, tmp_path):
        f = tmp_path / "CMakeLists.txt"
        f.write_text(CMAKE_CONTENT, encoding="utf-8")
        template = get_preset("cmake-project")
        assert isinstance(template, str)
        loc = compile_template(f, "test", template)
        assert loc.read_version() == "1.2.3"

    def test_c_define(self, tmp_path):
        f = tmp_path / "mylib.h"
        f.write_text(C_HEADER, encoding="utf-8")
        templates = get_preset("c-define", prefix="MYLIB")
        assert isinstance(templates, list)
        assert len(templates) == 3
        for template in templates:
            loc = compile_template(f, "test", template)
            assert loc.read_version() is not None

    def test_cargo_toml(self, tmp_path):
        f = tmp_path / "Cargo.toml"
        f.write_text(CARGO_TOML, encoding="utf-8")
        template = get_preset("cargo-toml")
        assert isinstance(template, str)
        loc = compile_template(f, "test", template)
        assert loc.read_version() == "1.2.3"

    def test_package_json(self, tmp_path):
        f = tmp_path / "package.json"
        f.write_text(PACKAGE_JSON, encoding="utf-8")
        template = get_preset("package-json")
        assert isinstance(template, str)
        loc = compile_template(f, "test", template)
        assert loc.read_version() == "1.2.3"

    def test_maven_pom(self, tmp_path):
        f = tmp_path / "pom.xml"
        f.write_text(MAVEN_POM, encoding="utf-8")
        template = get_preset("maven-pom")
        assert isinstance(template, str)
        loc = compile_template(f, "test", template)
        assert loc.read_version() == "1.2.3"

    def test_gradle_single_quotes(self, tmp_path):
        f = tmp_path / "build.gradle"
        f.write_text(GRADLE_SINGLE, encoding="utf-8")
        template = get_preset("gradle-version")
        assert isinstance(template, str)
        loc = compile_template(f, "test", template)
        assert loc.read_version() == "1.2.3"

    def test_gradle_double_quotes(self, tmp_path):
        f = tmp_path / "build.gradle"
        f.write_text(GRADLE_DOUBLE, encoding="utf-8")
        template = get_preset("gradle-version")
        assert isinstance(template, str)
        loc = compile_template(f, "test", template)
        assert loc.read_version() == "1.2.3"


class TestPresetReplace:
    """Test that each preset template correctly updates the version via write_version."""

    def test_pyproject_version(self, tmp_path):
        f = tmp_path / "pyproject.toml"
        f.write_text(PYPROJECT_TOML, encoding="utf-8")
        template = get_preset("pyproject-version")
        assert isinstance(template, str)
        loc = compile_template(f, "test", template)
        loc.write_version(Version(2, 0, 0))
        assert 'version = "2.0.0"' in f.read_text(encoding="utf-8")

    def test_python_dunder(self, tmp_path):
        f = tmp_path / "__init__.py"
        f.write_text(PYTHON_DUNDER, encoding="utf-8")
        template = get_preset("python-dunder")
        assert isinstance(template, str)
        loc = compile_template(f, "test", template)
        loc.write_version(Version(2, 0, 0))
        assert '__version__ = "2.0.0"' in f.read_text(encoding="utf-8")

    def test_cmake_project(self, tmp_path):
        f = tmp_path / "CMakeLists.txt"
        f.write_text(CMAKE_CONTENT, encoding="utf-8")
        template = get_preset("cmake-project")
        assert isinstance(template, str)
        loc = compile_template(f, "test", template)
        loc.write_version(Version(2, 0, 0))
        assert "VERSION 2.0.0" in f.read_text(encoding="utf-8")

    def test_package_json(self, tmp_path):
        f = tmp_path / "package.json"
        f.write_text(PACKAGE_JSON, encoding="utf-8")
        template = get_preset("package-json")
        assert isinstance(template, str)
        loc = compile_template(f, "test", template)
        loc.write_version(Version(2, 0, 0))
        assert '"version": "2.0.0"' in f.read_text(encoding="utf-8")

    def test_c_define_write(self, tmp_path):
        f = tmp_path / "mylib.h"
        f.write_text(C_HEADER, encoding="utf-8")
        templates = get_preset("c-define", prefix="MYLIB")
        assert isinstance(templates, list)
        for template in templates:
            loc = compile_template(f, "test", template)
            loc.write_version(Version(9, 8, 7))
        content = f.read_text(encoding="utf-8")
        assert "MYLIB_VERSION_MAJOR 9" in content
        assert "MYLIB_VERSION_MINOR 8" in content
        assert "MYLIB_VERSION_PATCH 7" in content


class TestPresetRegistry:
    """Test registry lookup and error handling."""

    def test_unknown_preset_raises(self):
        with pytest.raises(KeyError):
            get_preset("nonexistent")

    def test_c_define_missing_prefix_raises(self):
        with pytest.raises(ValueError, match="prefix"):
            get_preset("c-define")

    def test_all_presets_are_valid_templates(self):
        """Every non-parameterized preset is a string with exactly one placeholder."""
        for name, value in PRESET_REGISTRY.items():
            if name == "c-define":
                continue  # parameterized
            assert isinstance(value, str)
            # Should compile without error
            loc = compile_template(Path("dummy"), name, value)
            assert loc.template == value
