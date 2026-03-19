"""Profile resolution chain with inheritance support.

Loads a project-profile.yaml, resolves the ``extends`` chain, and returns
the merged result with qual-gate merge semantics.

Invocation:
    python -m cli.resolve_profile project-profile.yaml
"""

from __future__ import annotations

import copy
import sys
import urllib.request
from pathlib import Path

import yaml


class ProfileError(Exception):
    """Base exception for profile resolution errors."""


class ProfileDepthError(ProfileError):
    """Raised when inheritance chain exceeds max depth."""


class ProfileCircularError(ProfileError):
    """Raised when a circular reference is detected."""


class ProfileToggleError(ProfileError):
    """Raised when a child tries to disable a parent toggle."""


class ProfileLoadError(ProfileError):
    """Raised when a profile cannot be loaded."""


MAX_DEPTH = 3


def resolve_profile(profile_path: Path) -> dict:
    """Load profile, resolve inheritance, return merged result.

    Args:
        profile_path: Path to the child (leaf) profile YAML file.

    Returns:
        Fully merged profile dict with all inheritance resolved.

    Raises:
        ProfileDepthError: If inheritance exceeds 3 levels.
        ProfileCircularError: If a circular reference is detected.
        ProfileToggleError: If a child disables a parent toggle.
        ProfileLoadError: If a profile cannot be loaded.
    """
    visited: set[str] = set()
    return _resolve(str(profile_path.resolve()), visited, depth=0)


def _resolve(source: str, visited: set[str], depth: int) -> dict:
    """Recursive resolution with cycle and depth detection."""
    if depth >= MAX_DEPTH:
        raise ProfileDepthError(
            f"Inheritance chain exceeds max depth of {MAX_DEPTH}. "
            f"Chain so far: {visited}"
        )

    canonical = _canonical_source(source)
    if canonical in visited:
        raise ProfileCircularError(
            f"Circular reference detected: '{canonical}' already visited. "
            f"Chain: {visited}"
        )
    visited.add(canonical)

    profile = load_profile(source)
    extends = profile.pop("extends", None)

    if extends is None:
        return profile

    # Resolve parent relative to current profile's location
    parent_source = _resolve_relative(extends, source)
    parent = _resolve(parent_source, visited, depth + 1)

    # Validate toggle safety before merging
    toggle_errors = validate_toggles(parent, profile)
    if toggle_errors:
        raise ProfileToggleError(
            f"Toggle safety violations in '{source}': {toggle_errors}"
        )

    return merge_profiles(parent, profile)


def _canonical_source(source: str) -> str:
    """Normalize source to a canonical form for cycle detection."""
    if source.startswith(("http://", "https://")):
        return source
    return str(Path(source).resolve())


def _resolve_relative(extends: str, current_source: str) -> str:
    """Resolve an extends path relative to the current profile's location."""
    if extends.startswith(("http://", "https://")):
        return extends
    if current_source.startswith(("http://", "https://")):
        return extends
    parent_dir = Path(current_source).resolve().parent
    return str((parent_dir / extends).resolve())


def load_profile(source: str | Path) -> dict:
    """Load a profile from a local path or HTTPS URL.

    Args:
        source: Local file path or HTTPS URL.

    Returns:
        Parsed YAML dict.

    Raises:
        ProfileLoadError: If the source cannot be loaded or parsed.
    """
    source_str = str(source)

    if source_str.startswith(("http://", "https://")):
        return _load_url(source_str)
    return _load_file(Path(source_str))


def _load_file(path: Path) -> dict:
    """Load YAML from a local file."""
    if not path.exists():
        raise ProfileLoadError(f"Profile not found: {path}")
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ProfileLoadError(f"YAML parse error in {path}: {e}") from e

    if not isinstance(data, dict):
        raise ProfileLoadError(f"Profile must be a YAML mapping, got {type(data).__name__}: {path}")
    return data


def _load_url(url: str) -> dict:
    """Load YAML from an HTTPS URL using stdlib only."""
    try:
        with urllib.request.urlopen(url, timeout=30) as resp:  # noqa: S310
            content = resp.read().decode("utf-8")
    except (urllib.error.URLError, OSError) as e:
        raise ProfileLoadError(f"Failed to fetch profile from {url}: {e}") from e

    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ProfileLoadError(f"YAML parse error from {url}: {e}") from e

    if not isinstance(data, dict):
        raise ProfileLoadError(f"Profile must be a YAML mapping, got {type(data).__name__}: {url}")
    return data


def merge_profiles(parent: dict, child: dict) -> dict:
    """Deep-merge parent and child profiles with qual-gate semantics.

    Merge rules:
    - Scalars: child overrides parent
    - Lists: child REPLACES parent (explicit > implicit)
    - Objects/dicts: deep merge (child keys override, parent keys preserved)

    Args:
        parent: The resolved parent profile.
        child: The child profile (overrides).

    Returns:
        Merged profile dict.
    """
    merged = copy.deepcopy(parent)

    for key, child_value in child.items():
        if key not in merged:
            merged[key] = copy.deepcopy(child_value)
        elif isinstance(child_value, dict) and isinstance(merged[key], dict):
            merged[key] = merge_profiles(merged[key], child_value)
        else:
            # Scalars and lists: child replaces parent
            merged[key] = copy.deepcopy(child_value)

    return merged


def validate_toggles(parent: dict, child: dict) -> list[str]:
    """Ensure child doesn't disable parent toggles.

    A parent toggle set to True establishes a quality floor. Children can
    enable additional toggles but cannot disable inherited ones.

    Args:
        parent: Resolved parent profile.
        child: Child profile to validate.

    Returns:
        List of error messages. Empty = valid.
    """
    errors: list[str] = []
    parent_toggles = parent.get("toggles", {})
    child_toggles = child.get("toggles", {})

    if not isinstance(parent_toggles, dict) or not isinstance(child_toggles, dict):
        return errors

    for toggle_name, parent_value in parent_toggles.items():
        if parent_value is True and child_toggles.get(toggle_name) is False:
            errors.append(
                f"Cannot disable inherited toggle '{toggle_name}' "
                f"(parent sets it to true)"
            )

    return errors


def main() -> int:
    """CLI entry point for profile resolution."""
    if len(sys.argv) < 2:
        print("Usage: python -m cli.resolve_profile <profile.yaml>", file=sys.stderr)
        return 1

    profile_path = Path(sys.argv[1])
    try:
        resolved = resolve_profile(profile_path)
    except ProfileError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1

    yaml.dump(resolved, sys.stdout, default_flow_style=False, sort_keys=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
