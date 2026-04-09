import json
import pytest
from pathlib import Path
from vrzn.config import find_config, load_config, validate_config, ConfigError


class TestFindConfig:
    """Test config file discovery walking up directories."""

    def test_finds_vrzn_toml(self, tmp_path):
        config_file = tmp_path / "vrzn.toml"
        config_file.write_text('[[locations]]\nfile = "pyproject.toml"\ntype = "pyproject-version"\n')
        result = find_config(start_dir=tmp_path)
        assert result == config_file

    def test_finds_vrzn_yaml(self, tmp_path):
        config_file = tmp_path / "vrzn.yaml"
        config_file.write_text("locations:\n  - file: pyproject.toml\n    type: pyproject-version\n")
        result = find_config(start_dir=tmp_path)
        assert result == config_file

    def test_finds_vrzn_json(self, tmp_path):
        config_file = tmp_path / "vrzn.json"
        config_file.write_text(json.dumps({"locations": [{"file": "pyproject.toml", "type": "pyproject-version"}]}))
        result = find_config(start_dir=tmp_path)
        assert result == config_file

    def test_finds_pyproject_toml_with_tool_vrzn(self, tmp_path):
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text('[tool.vrzn]\n\n[[tool.vrzn.locations]]\nfile = "pyproject.toml"\ntype = "pyproject-version"\n')
        result = find_config(start_dir=tmp_path)
        assert result == config_file

    def test_skips_pyproject_without_tool_vrzn(self, tmp_path):
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text('[project]\nname = "something"\n')
        result = find_config(start_dir=tmp_path)
        assert result is None

    def test_priority_vrzn_toml_over_yaml(self, tmp_path):
        (tmp_path / "vrzn.toml").write_text('[[locations]]\nfile = "a.toml"\ntype = "pyproject-version"\n')
        (tmp_path / "vrzn.yaml").write_text("locations:\n  - file: b.toml\n    type: pyproject-version\n")
        result = find_config(start_dir=tmp_path)
        assert result is not None
        assert result.name == "vrzn.toml"

    def test_walks_up_directory(self, tmp_path):
        config_file = tmp_path / "vrzn.toml"
        config_file.write_text('[[locations]]\nfile = "pyproject.toml"\ntype = "pyproject-version"\n')
        subdir = tmp_path / "src" / "deep"
        subdir.mkdir(parents=True)
        result = find_config(start_dir=subdir)
        assert result == config_file

    def test_returns_none_when_not_found(self, tmp_path):
        result = find_config(start_dir=tmp_path)
        assert result is None

    def test_warns_on_multiple_configs(self, tmp_path, capsys):
        (tmp_path / "vrzn.toml").write_text('[[locations]]\nfile = "a"\ntype = "pyproject-version"\n')
        (tmp_path / "vrzn.json").write_text('{"locations": [{"file": "b", "type": "pyproject-version"}]}')
        result = find_config(start_dir=tmp_path)
        assert result is not None
        assert result.name == "vrzn.toml"
        captured = capsys.readouterr()
        assert "multiple" in captured.err.lower() or "multiple" in captured.err


class TestLoadConfig:
    """Test config file loading across formats."""

    def test_load_toml(self, tmp_path):
        config_file = tmp_path / "vrzn.toml"
        config_file.write_text('[[locations]]\nfile = "pyproject.toml"\ntype = "pyproject-version"\n')
        config = load_config(config_file)
        assert len(config["locations"]) == 1
        assert config["locations"][0]["type"] == "pyproject-version"

    def test_load_json(self, tmp_path):
        config_file = tmp_path / "vrzn.json"
        config_file.write_text(json.dumps({"locations": [{"file": "p.toml", "type": "pyproject-version"}]}))
        config = load_config(config_file)
        assert len(config["locations"]) == 1

    def test_load_yaml(self, tmp_path):
        config_file = tmp_path / "vrzn.yaml"
        config_file.write_text("locations:\n  - file: pyproject.toml\n    type: pyproject-version\n")
        config = load_config(config_file)
        assert len(config["locations"]) == 1

    def test_load_pyproject_toml_extracts_tool_vrzn(self, tmp_path):
        config_file = tmp_path / "pyproject.toml"
        config_file.write_text(
            '[project]\nname = "x"\n\n[tool.vrzn]\n\n'
            '[[tool.vrzn.locations]]\nfile = "pyproject.toml"\ntype = "pyproject-version"\n'
        )
        config = load_config(config_file)
        assert "locations" in config
        assert config["locations"][0]["type"] == "pyproject-version"


class TestValidateConfig:
    """Test config validation."""

    def test_valid_preset(self):
        config = {"locations": [{"file": "pyproject.toml", "type": "pyproject-version"}]}
        validate_config(config)  # should not raise

    def test_valid_custom(self):
        config = {"locations": [{"file": "f.py", "type": "custom", "template": r'{version}'}]}
        validate_config(config)

    def test_missing_file_raises(self):
        config = {"locations": [{"type": "pyproject-version"}]}
        with pytest.raises(ConfigError, match="file"):
            validate_config(config)

    def test_missing_type_raises(self):
        config = {"locations": [{"file": "pyproject.toml"}]}
        with pytest.raises(ConfigError, match="type"):
            validate_config(config)

    def test_unknown_preset_raises(self):
        config = {"locations": [{"file": "f", "type": "nonexistent"}]}
        with pytest.raises(ConfigError, match="Unknown"):
            validate_config(config)

    def test_custom_missing_template_raises(self):
        config = {"locations": [{"file": "f", "type": "custom"}]}
        with pytest.raises(ConfigError, match="template"):
            validate_config(config)

    def test_c_define_missing_prefix_raises(self):
        config = {"locations": [{"file": "h.h", "type": "c-define"}]}
        with pytest.raises(ConfigError, match="prefix"):
            validate_config(config)

    def test_c_define_with_prefix_valid(self):
        config = {"locations": [{"file": "h.h", "type": "c-define", "prefix": "MYLIB"}]}
        validate_config(config)

    def test_empty_locations_raises(self):
        config = {"locations": []}
        with pytest.raises(ConfigError, match="[Nn]o locations"):
            validate_config(config)

    def test_missing_locations_key_raises(self):
        config = {}
        with pytest.raises(ConfigError, match="locations"):
            validate_config(config)
