"""Version location file I/O and agreement checking."""

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple, Optional

from vrzn.presets import Preset, get_preset
from vrzn.version import Version, parse_version


@dataclass
class VersionLocation:
    """A file location containing a version string.

    :param file: Absolute path to the file.
    :param label: Display name for this location.
    :param pattern: Regex pattern for replacement (used with re.subn).
    :param replacement: Format string with {version}, {major}, {minor}, {patch}, {info_tuple}.
    :param extract: Regex with group(1) capturing the version string.
    :param base_only: If True, only MAJOR.MINOR.PATCH is written.
    """

    file: Path
    label: str
    pattern: str
    replacement: str
    extract: str
    base_only: bool = False

    def read_version(self) -> Optional[str]:
        """Extract the current version string from this location.

        :returns: Version string or None if not found.
        """
        if not self.file.exists():
            return None
        content = self.file.read_text(encoding="utf-8")
        match = re.search(self.extract, content, re.MULTILINE)
        if match:
            return match.group(1)
        return None

    def read_version_parsed(self) -> Optional[Version]:
        """Extract the current version as a parsed Version object.

        :returns: Version or None if not found or unparseable.
        """
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
        new = self.replacement.format(
            major=ver.major, minor=ver.minor, patch=ver.patch,
            version=version_str, info_tuple=ver.info_tuple,
        )
        new_content, count = re.subn(self.pattern, new, content, flags=re.MULTILINE)
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
            result.append(VersionLocation(
                file=file_path,
                label=entry.get("label", "custom"),
                pattern=entry["pattern"],
                replacement=entry["replacement"],
                extract=entry["extract"],
                base_only=entry.get("base_only", False),
            ))
        elif loc_type == "c-define":
            presets = get_preset("c-define", prefix=entry["prefix"])
            label_override = entry.get("label")
            for p in presets:
                result.append(VersionLocation(
                    file=file_path,
                    label=label_override or p.name,
                    pattern=p.pattern,
                    replacement=p.replacement,
                    extract=p.extract,
                    base_only=p.base_only,
                ))
        else:
            preset = get_preset(loc_type)
            result.append(VersionLocation(
                file=file_path,
                label=entry.get("label", preset.name),
                pattern=preset.pattern,
                replacement=preset.replacement,
                extract=preset.extract,
                base_only=preset.base_only,
            ))
    return result


def check_agreement(locations: list[VersionLocation]) -> tuple[Optional[Version], list[Mismatch]]:
    """Check whether all locations agree on the version.

    :param locations: List of version locations to check.
    :returns: Tuple of (consensus version or None, list of mismatches).
    """
    versions: list[tuple[VersionLocation, Optional[Version]]] = []
    for loc in locations:
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
