"""Integration test: validate all 13 core instruments against the manifest spec.

Runs the full validate_instrument() pipeline against each real instrument
directory. Confirms manifests (C3-C5) are consistent with their README/config
and the validation tool (C6) works against real instruments.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cli.validate_instrument import validate_instrument

INSTRUMENTS_DIR = Path(__file__).resolve().parent.parent.parent / "instruments"

CORE_INSTRUMENTS = [
    "architecture-tomographe",
    "test-tomographe",
    "code-tomographe",
    "documentation-tomographe",
    "compliance-tomographe",
    "data-tomographe",
    "deployment-tomographe",
    "observability-tomographe",
    "security-tomographe",
    "performance-tomographe",
    "ux-tomographe",
    "ai-ml-tomographe",
    "dependency-tomographe",
]


@pytest.mark.parametrize("instrument_name", CORE_INSTRUMENTS)
def test_core_instrument_validates(instrument_name: str) -> None:
    """Each core instrument must pass all 10 validation checks."""
    instrument_dir = INSTRUMENTS_DIR / instrument_name
    assert instrument_dir.is_dir(), f"Instrument directory not found: {instrument_dir}"

    result = validate_instrument(instrument_dir)

    assert result.passed, (
        f"{instrument_name} failed validation:\n"
        + "\n".join(f"  {f}" for f in result.failures)
    )


def test_all_13_instruments_present() -> None:
    """Verify we're actually testing all 13 instruments."""
    assert len(CORE_INSTRUMENTS) == 13, (
        f"Expected 13 core instruments, got {len(CORE_INSTRUMENTS)}"
    )
