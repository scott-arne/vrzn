"""Version location file I/O and agreement checking."""

import re
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, NamedTuple, Optional

from vrzn.presets import get_preset
from vrzn.version import Version, parse_version


class VersionFormat(Enum):
    """Classification of what a template placeholder captures.

    FULL: Full PEP 440 version string (e.g., "1.2.3rc1").
    BASE: Base version only, MAJOR.MINOR.PATCH (e.g., "1.2.3").
    COMPONENT: A single integer component (e.g., MAJOR, MINOR, or PATCH).
    """

    FULL = "full"
    BASE = "base"
    COMPONENT = "component"


# Mapping of placeholder names to (extraction_regex, VersionFormat).
_PLACEHOLDERS: dict[str, tuple[str, VersionFormat]] = {
    "version": (r"[^\s\"'<>\)\]]+", VersionFormat.FULL),
    "base": (r"\d+\.\d+\.\d+", VersionFormat.BASE),
    "info_tuple": (r"\d+,\s*\d+,\s*\d+", VersionFormat.BASE),
    "major": (r"\d+", VersionFormat.COMPONENT),
    "minor": (r"\d+", VersionFormat.COMPONENT),
    "patch": (r"\d+", VersionFormat.COMPONENT),
}

# Regex to find placeholders like {version}, {major}, etc.
_PLACEHOLDER_RE = re.compile(r"\{(" + "|".join(_PLACEHOLDERS) + r")\}")


def compile_template(file: Path, label: str, template: str) -> "VersionLocation":
    """Compile a template string into a VersionLocation.

    The template must contain exactly one placeholder from the known set
    (e.g., ``{version}``, ``{major}``). The surrounding text becomes the
    context that anchors the extraction regex and the replacement string.

    :param file: Absolute path to the version file.
    :param label: Display name for this location.
    :param template: Template string with exactly one placeholder.
    :returns: A fully configured VersionLocation.
    :raises ValueError: If the template has zero, multiple, or unrecognized placeholders.
    """
    matches = list(_PLACEHOLDER_RE.finditer(template))
    if len(matches) == 0:
        raise ValueError(
            f"Template has no recognized placeholder: {template!r}. "
            f"Expected one of: {', '.join('{' + k + '}' for k in _PLACEHOLDERS)}"
        )
    if len(matches) > 1:
        found = [m.group(0) for m in matches]
        raise ValueError(
            f"Template has multiple placeholders: {found}. "
            f"Each template must contain exactly one placeholder."
        )

    match = matches[0]
    placeholder_name = match.group(1)
    extraction_regex, fmt = _PLACEHOLDERS[placeholder_name]

    before = template[: match.start()]
    after = template[match.end() :]

    # Build the extraction regex with capture groups.
    # Non-empty before/after context segments become capture groups.
    regex_parts = []
    replacement_parts = []
    group_index = 1

    if before:
        regex_parts.append(f"({before})")
        replacement_parts.append(f"\\g<{group_index}>")
        group_index += 1

    # The version data capture group
    version_group = group_index
    regex_parts.append(f"({extraction_regex})")
    group_index += 1

    if after:
        regex_parts.append(f"({after})")
        replacement_parts.append(f"\\g<{group_index}>")

    # Insert the placeholder format key where the version data goes
    replacement_parts.insert(
        1 if before else 0,
        "{" + placeholder_name + "}",
    )

    regex = "".join(regex_parts)
    replacement = "".join(replacement_parts)

    return VersionLocation(
        file=file,
        label=label,
        template=template,
        _regex=regex,
        _replacement=replacement,
        _version_group=version_group,
        format=fmt,
    )


@dataclass
class VersionLocation:
    """A file location containing a version string.

    Constructed via :func:`compile_template` rather than directly.

    :param file: Absolute path to the file.
    :param label: Display name for this location.
    :param template: Original template string with placeholder.
    :param _regex: Compiled extraction/replacement regex.
    :param _replacement: Format string with backreferences and placeholder key.
    :param _version_group: Capture group index for the version data.
    :param format: The VersionFormat classification.
    """

    file: Path
    label: str
    template: str
    _regex: str
    _replacement: str
    _version_group: int
    format: VersionFormat

    @property
    def component(self) -> bool:
        """Backward-compatible property: True if format is COMPONENT."""
        return self.format == VersionFormat.COMPONENT

    @property
    def base_only(self) -> bool:
        """Backward-compatible property: True if format is BASE or COMPONENT."""
        return self.format in (VersionFormat.BASE, VersionFormat.COMPONENT)

    def read_version(self) -> Optional[str]:
        """Extract the current version string from this location.

        :returns: Version string or None if not found.
        """
        if not self.file.exists():
            return None
        content = self.file.read_text(encoding="utf-8")
        match = re.search(self._regex, content, re.MULTILINE)
        if match:
            return match.group(self._version_group)
        return None

    def read_version_parsed(self) -> Optional[Version]:
        """Extract the current version as a parsed Version object.

        Returns None for COMPONENT format locations since they hold
        single integers that are not parseable as full versions.

        :returns: Version or None if not found or unparseable.
        """
        if self.format == VersionFormat.COMPONENT:
            return None
        raw = self.read_version()
        if raw is None:
            return None
        try:
            return parse_version(raw)
        except ValueError:
            return None

    def write_version(self, ver: Version) -> bool:
        """Replace the version string in this file.

        :param ver: Version to write.
        :returns: True if the file was modified.
        """
        if not self.file.exists():
            return False
        content = self.file.read_text(encoding="utf-8")

        version_str = ver.base if self.base_only else ver.normalized
        new = self._replacement.format(
            major=ver.major, minor=ver.minor, patch=ver.patch,
            version=version_str, base=ver.base, info_tuple=ver.info_tuple,
        )
        new_content, count = re.subn(self._regex, new, content, flags=re.MULTILINE)
        if count == 0:
            return False
        self.file.write_text(new_content, encoding="utf-8")
        return True


class Mismatch(NamedTuple):
    """A version location that disagrees with consensus."""

    location: VersionLocation
    found: Optional[Version]


def locations_from_config(config: dict[str, Any], project_root: Path) -> list[VersionLocation]:
    """Build VersionLocation list from parsed config.

    :param config: Validated config dict with "locations" key.
    :param project_root: Root directory for resolving relative file paths.
    :returns: List of VersionLocation instances.
    """
    result = []
    for entry in config["locations"]:
        file_path = (project_root / entry["file"]).resolve()
        loc_type = entry["type"]

        if loc_type == "custom":
            result.append(compile_template(
                file=file_path,
                label=entry.get("label", "custom"),
                template=entry["template"],
            ))
        elif loc_type == "c-define":
            templates = get_preset("c-define", prefix=entry["prefix"])
            assert isinstance(templates, list)
            label_override = entry.get("label")
            labels = [f"c-define ({c})" for c in ("MAJOR", "MINOR", "PATCH")]
            for template, default_label in zip(templates, labels):
                result.append(compile_template(
                    file=file_path,
                    label=label_override or default_label,
                    template=template,
                ))
        else:
            template = get_preset(loc_type)
            assert isinstance(template, str)
            result.append(compile_template(
                file=file_path,
                label=entry.get("label", loc_type),
                template=template,
            ))
    return result


def check_agreement(locations: list[VersionLocation]) -> tuple[Optional[Version], list[Mismatch]]:
    """Check whether all locations agree on the version.

    Component locations (e.g., individual c-define MAJOR/MINOR/PATCH entries)
    are excluded from agreement checking since they hold single integers
    rather than full version strings.

    :param locations: List of version locations to check.
    :returns: Tuple of (consensus version or None, list of mismatches).
    """
    versions: list[tuple[VersionLocation, Optional[Version]]] = []
    for loc in locations:
        if loc.format == VersionFormat.COMPONENT:
            continue
        versions.append((loc, loc.read_version_parsed()))

    parsed = [(loc, v) for loc, v in versions if v is not None]
    if not parsed:
        return None, []

    # Find consensus: most common version, tiebreaker is first-listed
    counts: Counter[Version] = Counter()
    first_seen: dict[Version, int] = {}
    for i, (_, v) in enumerate(parsed):
        counts[v] += 1
        if v not in first_seen:
            first_seen[v] = i

    max_count = max(counts.values())
    candidates = [v for v, c in counts.items() if c == max_count]
    consensus = min(candidates, key=lambda v: first_seen[v])

    mismatches = []
    for loc, v in versions:
        if v is None or v != consensus:
            mismatches.append(Mismatch(location=loc, found=v))

    return consensus, mismatches
