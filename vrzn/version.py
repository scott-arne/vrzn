"""PEP 440 version model with parsing, normalization, and comparison."""

import re
from dataclasses import dataclass
from functools import total_ordering
from typing import Optional

# PEP 440 pre-release labels and their normalized forms
_PRE_LABELS = {
    "a": "a", "alpha": "a",
    "b": "b", "beta": "b",
    "c": "rc", "rc": "rc", "preview": "rc",
}

# Pre-release label ordering for comparison and validation
PRE_LABEL_ORDER = {"a": 0, "b": 1, "rc": 2}

# Regex for full PEP 440 version parsing (accepts common non-normalized forms)
_PEP440_RE = re.compile(
    r"^(?:(?P<epoch>\d+)!)?"
    r"(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)"
    r"(?:"
    r"[-.]?(?P<pre_label>a|alpha|b|beta|c|rc|preview)[-.]?(?P<pre_num>\d+)"
    r")?"
    r"(?:"
    r"[.]?(?:post)[-.]?(?P<post_num>\d+)"
    r")?"
    r"(?:"
    r"[.]?(?:dev)[-.]?(?P<dev_num>\d+)"
    r")?$",
    re.IGNORECASE,
)


@total_ordering
@dataclass(frozen=True)
class Version:
    """A PEP 440 version with base release and optional suffixes."""

    major: int
    minor: int
    patch: int
    pre: Optional[tuple[str, int]] = None
    post: Optional[int] = None
    dev: Optional[int] = None
    epoch: Optional[int] = None

    @property
    def normalized(self) -> str:
        """Return the canonical PEP 440 normalized version string.

        :returns: Normalized version string.
        """
        parts = []
        if self.epoch is not None:
            parts.append(f"{self.epoch}!")
        parts.append(self.base)
        if self.pre is not None:
            parts.append(f"{self.pre[0]}{self.pre[1]}")
        if self.post is not None:
            parts.append(f".post{self.post}")
        if self.dev is not None:
            parts.append(f".dev{self.dev}")
        return "".join(parts)

    @property
    def base(self) -> str:
        """Return the MAJOR.MINOR.PATCH base version string.

        :returns: Base version string without suffixes.
        """
        return f"{self.major}.{self.minor}.{self.patch}"

    @property
    def info_tuple(self) -> str:
        """Return the version_info tuple string (base integers only).

        :returns: Comma-separated tuple string of major, minor, patch.
        """
        return f"{self.major}, {self.minor}, {self.patch}"

    @property
    def is_release(self) -> bool:
        """Return True if this is a final release (no pre/post/dev suffix).

        :returns: True if final release, False otherwise.
        """
        return self.pre is None and self.post is None and self.dev is None

    def _sort_key(self) -> tuple:
        """Return a tuple for PEP 440 ordering.

        Ordering: epoch, then base, then pre (absent pre > any pre),
        then post (absent post < any post), then dev (absent dev > any dev).

        :returns: Tuple for sorting and comparison.
        """
        epoch = self.epoch if self.epoch is not None else 0
        if self.pre is not None:
            pre_key = (0, PRE_LABEL_ORDER[self.pre[0]], self.pre[1])
        else:
            pre_key = (1,)
        post_key = self.post if self.post is not None else -1
        if self.dev is not None:
            dev_key = (0, self.dev)
        else:
            dev_key = (1,)
        return (epoch, self.major, self.minor, self.patch, pre_key, post_key, dev_key)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._sort_key() == other._sort_key()

    def __lt__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self._sort_key() < other._sort_key()

    def __hash__(self) -> int:
        return hash(self._sort_key())

    def __str__(self) -> str:
        return self.normalized

    def __repr__(self) -> str:
        return f"Version('{self.normalized}')"

    def bump_major(self, pre_label: Optional[str] = None) -> "Version":
        """Bump major version. Zeros minor and patch, clears suffixes.

        :param pre_label: If given, start a pre-release with this label.
        :returns: New Version with bumped major.
        """
        pre = (pre_label, 1) if pre_label else None
        return Version(self.major + 1, 0, 0, pre=pre, epoch=self.epoch)

    def bump_minor(self, pre_label: Optional[str] = None) -> "Version":
        """Bump minor version. Zeros patch, clears suffixes.

        :param pre_label: If given, start a pre-release with this label.
        :returns: New Version with bumped minor.
        """
        pre = (pre_label, 1) if pre_label else None
        return Version(self.major, self.minor + 1, 0, pre=pre, epoch=self.epoch)

    def bump_patch(self, pre_label: Optional[str] = None) -> "Version":
        """Bump patch version. Clears suffixes.

        :param pre_label: If given, start a pre-release with this label.
        :returns: New Version with bumped patch.
        """
        pre = (pre_label, 1) if pre_label else None
        return Version(self.major, self.minor, self.patch + 1, pre=pre, epoch=self.epoch)

    def bump_pre(self, label: Optional[str] = None) -> "Version":
        """Increment pre-release number, or promote to a new label.

        :param label: Pre-release label to promote to (a, b, rc).
        :returns: New Version with bumped pre-release.
        :raises ValueError: If no pre-release is active, or label goes backward.
        """
        if self.pre is None:
            raise ValueError("Cannot bump pre-release: no active pre-release suffix")

        current_label, current_num = self.pre

        if label is None:
            return Version(
                self.major, self.minor, self.patch,
                pre=(current_label, current_num + 1), epoch=self.epoch,
            )

        current_order = PRE_LABEL_ORDER[current_label]
        target_order = PRE_LABEL_ORDER[label]

        if target_order < current_order:
            raise ValueError(
                f"Cannot change pre-release label backward: {current_label} -> {label}"
            )
        elif target_order == current_order:
            return Version(
                self.major, self.minor, self.patch,
                pre=(label, current_num + 1), epoch=self.epoch,
            )
        else:
            return Version(
                self.major, self.minor, self.patch,
                pre=(label, 1), epoch=self.epoch,
            )

    def bump_release(self) -> "Version":
        """Finalize a pre-release by stripping the pre-release suffix.

        :returns: New Version without pre-release suffix.
        :raises ValueError: If version is already a final release.
        """
        if self.pre is None:
            raise ValueError("Cannot bump release: already a final release")
        return Version(self.major, self.minor, self.patch, epoch=self.epoch)


def parse_version(version_str: str) -> Version:
    """Parse a version string into a Version object.

    Accepts PEP 440 versions and common variants with hyphens/dots as
    separators. Also handles comma-separated tuples and epoch prefixes.

    :param version_str: Version string in any supported format.
    :returns: Parsed Version object.
    :raises ValueError: If the string cannot be parsed.
    """
    raw = version_str.strip()
    if not raw:
        raise ValueError(f"Cannot parse version: {version_str!r}")

    # Handle comma-separated tuple format
    if "," in raw:
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) < 3:
            raise ValueError(f"Cannot parse version: {version_str!r}")
        return Version(int(parts[0]), int(parts[1]), int(parts[2]))

    m = _PEP440_RE.match(raw)
    if not m:
        raise ValueError(f"Cannot parse version: {version_str!r}")

    pre = None
    if m.group("pre_label"):
        label = _PRE_LABELS[m.group("pre_label").lower()]
        pre = (label, int(m.group("pre_num")))

    post = int(m.group("post_num")) if m.group("post_num") else None
    dev = int(m.group("dev_num")) if m.group("dev_num") else None
    epoch = int(m.group("epoch")) if m.group("epoch") else None

    return Version(
        major=int(m.group("major")),
        minor=int(m.group("minor")),
        patch=int(m.group("patch")),
        pre=pre, post=post, dev=dev, epoch=epoch,
    )
