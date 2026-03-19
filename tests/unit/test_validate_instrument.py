"""Unit tests for cli.validate_instrument."""

from __future__ import annotations

from pathlib import Path

import pytest

from cli.validate_instrument import (
    ValidationResult,
    check_config_has_thresholds,
    check_fixes_readme,
    check_manifest_exists,
    check_no_orphan_methods,
    check_phases_have_methods,
    check_report_prefix,
    check_required_fields,
    check_required_files_exist,
    check_spec_version,
    validate_instrument,
)


class TestValidInstrument:
    """All 10 checks pass for the valid fixture."""

    def test_all_checks_pass(self, valid_instrument_dir: Path) -> None:
        result = validate_instrument(valid_instrument_dir)
        assert result.passed, (
            f"Expected all checks to pass, got failures: {result.failures}"
        )

    def test_pass_count(self, valid_instrument_dir: Path) -> None:
        result = validate_instrument(valid_instrument_dir)
        assert len(result.passes) == 10, (
            f"Expected 10 passes, got {len(result.passes)}: {result.passes}"
        )


class TestMissingManifest:
    """R01: instrument.yaml missing → immediate failure."""

    def test_fails_on_missing_manifest(self, missing_manifest_dir: Path) -> None:
        result = validate_instrument(missing_manifest_dir)
        assert not result.passed, "Expected failure for missing manifest"
        assert any("R01" in f for f in result.failures), (
            f"Expected R01 failure, got: {result.failures}"
        )

    def test_only_one_failure(self, missing_manifest_dir: Path) -> None:
        """When manifest is missing, no other checks should run."""
        result = validate_instrument(missing_manifest_dir)
        assert len(result.failures) == 1, (
            f"Expected exactly 1 failure, got {len(result.failures)}: {result.failures}"
        )


class TestWrongSpecVersion:
    """R02: spec_version != '2.0' → failure."""

    def test_fails_on_wrong_spec_version(self, wrong_spec_version_dir: Path) -> None:
        result = validate_instrument(wrong_spec_version_dir)
        assert not result.passed, "Expected failure for wrong spec_version"
        assert any("R02" in f for f in result.failures), (
            f"Expected R02 failure, got: {result.failures}"
        )


class TestOrphanMethod:
    """R06: method file on disk but not declared in manifest → failure."""

    def test_fails_on_orphan_method(self, orphan_method_dir: Path) -> None:
        result = validate_instrument(orphan_method_dir)
        assert not result.passed, "Expected failure for orphan method"
        assert any("R06" in f for f in result.failures), (
            f"Expected R06 failure, got: {result.failures}"
        )


class TestIndividualChecks:
    """Test individual check functions in isolation."""

    def test_spec_version_pass(self) -> None:
        result = ValidationResult(Path("."))
        check_spec_version({"spec_version": "2.0"}, result)
        assert result.passed

    def test_spec_version_fail(self) -> None:
        result = ValidationResult(Path("."))
        check_spec_version({"spec_version": "1.0"}, result)
        assert not result.passed

    def test_required_fields_pass(self) -> None:
        result = ValidationResult(Path("."))
        manifest = {
            "spec_version": "2.0",
            "id": "I01",
            "name": "test-tomographe",
            "version": "1.0.0",
            "description": "test",
            "report_prefix": "TT",
            "dr_sections": [],
            "phases": [],
            "required_files": [],
        }
        check_required_fields(manifest, result)
        assert result.passed

    def test_required_fields_fail(self) -> None:
        result = ValidationResult(Path("."))
        check_required_fields({"spec_version": "2.0"}, result)
        assert not result.passed
        assert any("R03" in f for f in result.failures)

    def test_config_thresholds_pass(self, valid_instrument_dir: Path) -> None:
        result = ValidationResult(valid_instrument_dir)
        check_config_has_thresholds(valid_instrument_dir, result)
        assert result.passed

    def test_fixes_readme_pass(self, valid_instrument_dir: Path) -> None:
        result = ValidationResult(valid_instrument_dir)
        check_fixes_readme(valid_instrument_dir, result)
        assert result.passed

    def test_fixes_readme_fail(self, missing_manifest_dir: Path) -> None:
        result = ValidationResult(missing_manifest_dir)
        check_fixes_readme(missing_manifest_dir, result)
        assert not result.passed

    def test_phases_have_methods_pass(self, valid_instrument_dir: Path) -> None:
        result = ValidationResult(valid_instrument_dir)
        manifest = {
            "phases": [
                {"id": 1, "name": "Scan"},
                {"id": 2, "name": "Report"},
            ]
        }
        check_phases_have_methods(valid_instrument_dir, manifest, result)
        assert result.passed

    def test_phases_have_methods_fail(self, valid_instrument_dir: Path) -> None:
        result = ValidationResult(valid_instrument_dir)
        manifest = {
            "phases": [
                {"id": 1, "name": "Scan"},
                {"id": 99, "name": "Nonexistent"},
            ]
        }
        check_phases_have_methods(valid_instrument_dir, manifest, result)
        assert not result.passed

    def test_no_orphan_methods_pass(self, valid_instrument_dir: Path) -> None:
        result = ValidationResult(valid_instrument_dir)
        manifest = {
            "phases": [
                {"id": 1, "name": "Scan"},
                {"id": 2, "name": "Report"},
            ]
        }
        check_no_orphan_methods(valid_instrument_dir, manifest, result)
        assert result.passed

    def test_report_prefix_pass(self, valid_instrument_dir: Path) -> None:
        result = ValidationResult(valid_instrument_dir)
        check_report_prefix(valid_instrument_dir, {"report_prefix": "VT"}, result)
        assert result.passed

    def test_report_prefix_fail(self, valid_instrument_dir: Path) -> None:
        result = ValidationResult(valid_instrument_dir)
        check_report_prefix(valid_instrument_dir, {"report_prefix": "ZZ"}, result)
        assert not result.passed

    def test_required_files_exist_pass(self, valid_instrument_dir: Path) -> None:
        result = ValidationResult(valid_instrument_dir)
        manifest = {"required_files": ["README.md", "config.yaml", "methods/"]}
        check_required_files_exist(valid_instrument_dir, manifest, result)
        assert result.passed

    def test_required_files_exist_fail(self, valid_instrument_dir: Path) -> None:
        result = ValidationResult(valid_instrument_dir)
        manifest = {"required_files": ["nonexistent.txt"]}
        check_required_files_exist(valid_instrument_dir, manifest, result)
        assert not result.passed
