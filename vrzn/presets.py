"""Built-in preset registry for common version file formats."""


PRESET_REGISTRY: dict[str, str] = {
    "pyproject-version": r'^version\s*=\s*"{version}"',
    "python-dunder": r"""__version__\s*=\s*["']{version}["']""",
    "python-version-info": r"__version_info__\s*=\s*\({info_tuple}\)",
    "cmake-project": r"project\([^\)]*VERSION\s+{base}",
    "c-define": "parameterized",
    "cargo-toml": r'^version\s*=\s*"{version}"',
    "package-json": r'"version"\s*:\s*"{version}"',
    "maven-pom": r"<version>{version}</version>",
    "gradle-version": r"""version\s*=?\s*["']{version}["']""",
}


def _make_c_define_templates(prefix: str) -> list[str]:
    """Generate three templates for C/C++ #define version macros.

    :param prefix: The macro prefix (e.g., "MYLIB" for MYLIB_VERSION_MAJOR).
    :returns: List of three template strings (MAJOR, MINOR, PATCH).
    """
    return [
        rf"#define\s+{prefix}_VERSION_MAJOR\s+{{major}}",
        rf"#define\s+{prefix}_VERSION_MINOR\s+{{minor}}",
        rf"#define\s+{prefix}_VERSION_PATCH\s+{{patch}}",
    ]


def get_preset(name: str, **params: str) -> str | list[str]:
    """Look up a preset template by name, with optional parameters.

    :param name: Preset name from the registry.
    :param params: Additional parameters (e.g., prefix for c-define).
    :returns: Single template string or list of template strings.
    :raises KeyError: If the preset name is not recognized.
    :raises ValueError: If required parameters are missing.
    """
    if name not in PRESET_REGISTRY:
        raise KeyError(f"Unknown preset: {name!r}")

    if name == "c-define":
        prefix = params.get("prefix")
        if not prefix:
            raise ValueError("c-define preset requires a 'prefix' parameter")
        return _make_c_define_templates(prefix)

    return PRESET_REGISTRY[name]
