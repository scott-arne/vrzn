"""Built-in preset registry for common version file formats."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Preset:
    """A preset pattern definition for a version file format.

    :param name: Preset identifier used in config files.
    :param description: Human-readable description of what this matches.
    :param pattern: Regex pattern for replacement (used with re.subn).
    :param replacement: Format string with {version}, {major}, {minor}, {patch}, {info_tuple}.
    :param extract: Regex with group(1) capturing the version string.
    :param base_only: If True, only MAJOR.MINOR.PATCH is written.
    """

    name: str
    description: str
    pattern: str
    replacement: str
    extract: str
    base_only: bool = False


PRESET_REGISTRY: dict[str, Preset | str] = {
    "pyproject-version": Preset(
        name="pyproject-version",
        description='version = "X.Y.Z" in TOML',
        pattern=r'(^version\s*=\s*")[^"]+(")',
        replacement=r'\g<1>{version}\g<2>',
        extract=r'^version\s*=\s*"([^"]+)"',
    ),
    "python-dunder": Preset(
        name="python-dunder",
        description='__version__ = "X.Y.Z" in Python',
        pattern=r'(__version__\s*=\s*["\'])[^"\']+(["\'])',
        replacement=r'\g<1>{version}\g<2>',
        extract=r'__version__\s*=\s*["\']([^"\']+)["\']',
    ),
    "python-version-info": Preset(
        name="python-version-info",
        description="__version_info__ = (X, Y, Z) tuple in Python",
        pattern=r"(__version_info__\s*=\s*\()[^)]+(\))",
        replacement=r"\g<1>{info_tuple}\g<2>",
        extract=r"__version_info__\s*=\s*\(([^)]+)\)",
        base_only=True,
    ),
    "cmake-project": Preset(
        name="cmake-project",
        description="project(NAME VERSION X.Y.Z) in CMakeLists.txt",
        pattern=r"(project\([^\)]*VERSION\s+)\d+\.\d+\.\d+",
        replacement=r"\g<1>{major}.{minor}.{patch}",
        extract=r"project\([^\)]*VERSION\s+(\d+\.\d+\.\d+)",
        base_only=True,
    ),
    "c-define": "parameterized",  # sentinel — handled by get_preset
    "cargo-toml": Preset(
        name="cargo-toml",
        description='version = "X.Y.Z" in Cargo.toml',
        pattern=r'(^version\s*=\s*")[^"]+(")',
        replacement=r'\g<1>{version}\g<2>',
        extract=r'^version\s*=\s*"([^"]+)"',
    ),
    "package-json": Preset(
        name="package-json",
        description='"version": "X.Y.Z" in package.json',
        pattern=r'("version"\s*:\s*")[^"]+(")',
        replacement=r'\g<1>{version}\g<2>',
        extract=r'"version"\s*:\s*"([^"]+)"',
    ),
    "maven-pom": Preset(
        name="maven-pom",
        description="<version>X.Y.Z</version> in pom.xml",
        pattern=r"(<version>)[^<]+(</version>)",
        replacement=r"\g<1>{version}\g<2>",
        extract=r"<version>([^<]+)</version>",
    ),
    "gradle-version": Preset(
        name="gradle-version",
        description="version = 'X.Y.Z' or version \"X.Y.Z\" in Gradle",
        pattern=r"""(version\s*=?\s*['"])[^'"]+(['"])""",
        replacement=r"\g<1>{version}\g<2>",
        extract=r"""version\s*=?\s*['"]([^'"]+)['"]""",
    ),
}


def _make_c_define_presets(prefix: str) -> list[Preset]:
    """Generate three presets for C/C++ #define version macros.

    :param prefix: The macro prefix (e.g., "MYLIB" for MYLIB_VERSION_MAJOR).
    :returns: List of three Preset objects (MAJOR, MINOR, PATCH).
    """
    result = []
    for component in ("MAJOR", "MINOR", "PATCH"):
        macro = f"{prefix}_VERSION_{component}"
        result.append(Preset(
            name=f"c-define ({component})",
            description=f"#define {macro} N",
            pattern=rf"(#define\s+{macro}\s+)\d+",
            replacement=rf"\g<1>{{{component.lower()}}}",
            extract=rf"#define\s+{macro}\s+(\d+)",
            base_only=True,
        ))
    return result


def get_preset(name: str, **params: str) -> Preset | list[Preset]:
    """Look up a preset by name, with optional parameters.

    :param name: Preset name from the registry.
    :param params: Additional parameters (e.g., prefix for c-define).
    :returns: Single Preset or list of Presets (for parameterized types).
    :raises KeyError: If the preset name is not recognized.
    :raises ValueError: If required parameters are missing.
    """
    if name not in PRESET_REGISTRY:
        raise KeyError(f"Unknown preset: {name!r}")

    if name == "c-define":
        prefix = params.get("prefix")
        if not prefix:
            raise ValueError("c-define preset requires a 'prefix' parameter")
        return _make_c_define_presets(prefix)

    return PRESET_REGISTRY[name]
