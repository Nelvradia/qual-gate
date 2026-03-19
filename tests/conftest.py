"""Shared fixtures for qual-gate tests."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def valid_instrument_dir() -> Path:
    """Path to a valid instrument fixture directory."""
    return FIXTURES_DIR / "valid-instrument"


@pytest.fixture()
def missing_manifest_dir() -> Path:
    """Path to an instrument fixture with no instrument.yaml."""
    return FIXTURES_DIR / "invalid-instruments" / "missing-manifest"


@pytest.fixture()
def wrong_spec_version_dir() -> Path:
    """Path to an instrument fixture with wrong spec_version."""
    return FIXTURES_DIR / "invalid-instruments" / "wrong-spec-version"


@pytest.fixture()
def orphan_method_dir() -> Path:
    """Path to an instrument fixture with an undeclared method file."""
    return FIXTURES_DIR / "invalid-instruments" / "orphan-method"
