"""Validate an instrument directory against the instrument.yaml manifest spec.

Invocation:
    python -m cli.validate_instrument instruments/architecture-tomographe/

Exit 0 = all checks pass, exit 1 = one or more failures.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

REQUIRED_TOP_LEVEL_FIELDS = frozenset({
    "spec_version",
    "id",
    "name",
    "version",
    "description",
    "report_prefix",
    "dr_sections",
    "phases",
    "required_files",
})

QUALITOSCOPE_CONFIG = Path(__file__).resolve().parent.parent / "qualitoscope" / "config.yaml"


class ValidationResult:
    """Collects pass/fail results for a single instrument."""

    def __init__(self, instrument_dir: Path) -> None:
        self.instrument_dir = instrument_dir
        self.passes: list[str] = []
        self.failures: list[str] = []

    def ok(self, rule: str, detail: str = "") -> None:
        msg = f"[PASS] {rule}"
        if detail:
            msg += f": {detail}"
        self.passes.append(msg)

    def fail(self, rule: str, detail: str) -> None:
        self.failures.append(f"[FAIL] {rule}: {detail}")

    @property
    def passed(self) -> bool:
        return len(self.failures) == 0


def load_yaml(path: Path) -> dict | None:
    """Load a YAML file, returning None on parse error."""
    try:
        with open(path) as f:
            return yaml.safe_load(f)
    except (yaml.YAMLError, OSError):
        return None


def load_qualitoscope_config() -> dict | None:
    """Load qualitoscope/config.yaml if it exists."""
    if QUALITOSCOPE_CONFIG.exists():
        return load_yaml(QUALITOSCOPE_CONFIG)
    return None


def check_manifest_exists(instrument_dir: Path, result: ValidationResult) -> dict | None:
    """Rule 1: instrument.yaml exists and parses."""
    manifest_path = instrument_dir / "instrument.yaml"
    if not manifest_path.exists():
        result.fail("R01-manifest-exists", "instrument.yaml not found")
        return None

    data = load_yaml(manifest_path)
    if data is None:
        result.fail("R01-manifest-exists", "instrument.yaml failed to parse as YAML")
        return None

    result.ok("R01-manifest-exists")
    return data


def check_spec_version(manifest: dict, result: ValidationResult) -> None:
    """Rule 2: spec_version is '2.0'."""
    version = manifest.get("spec_version")
    if version == "2.0":
        result.ok("R02-spec-version")
    else:
        result.fail("R02-spec-version", f"expected '2.0', got '{version}'")


def check_required_fields(manifest: dict, result: ValidationResult) -> None:
    """Rule 3: Required top-level fields present."""
    missing = REQUIRED_TOP_LEVEL_FIELDS - set(manifest.keys())
    if missing:
        result.fail("R03-required-fields", f"missing: {sorted(missing)}")
    else:
        result.ok("R03-required-fields")


def check_required_files_exist(
    instrument_dir: Path, manifest: dict, result: ValidationResult
) -> None:
    """Rule 4: All required_files exist on disk."""
    required = manifest.get("required_files", [])
    missing = []
    for entry in required:
        path = instrument_dir / entry
        if entry.endswith("/"):
            if not path.is_dir():
                missing.append(entry)
        else:
            if not path.exists():
                missing.append(entry)

    if missing:
        result.fail("R04-required-files", f"missing on disk: {missing}")
    else:
        result.ok("R04-required-files")


def check_phases_have_methods(
    instrument_dir: Path, manifest: dict, result: ValidationResult
) -> None:
    """Rule 5: All phases in manifest have corresponding methods/{NN}-*.md files."""
    phases = manifest.get("phases", [])
    methods_dir = instrument_dir / "methods"
    missing = []

    for phase in phases:
        phase_id = phase.get("id")
        if phase_id is None:
            continue
        prefix = f"{phase_id:02d}-"
        matches = list(methods_dir.glob(f"{prefix}*.md")) if methods_dir.is_dir() else []
        if not matches:
            missing.append(f"phase {phase_id} ({phase.get('name', '?')})")

    if missing:
        result.fail("R05-phases-have-methods", f"no method file for: {missing}")
    else:
        result.ok("R05-phases-have-methods")


def check_no_orphan_methods(
    instrument_dir: Path, manifest: dict, result: ValidationResult
) -> None:
    """Rule 6: No orphan method files (on disk but not declared in manifest)."""
    methods_dir = instrument_dir / "methods"
    if not methods_dir.is_dir():
        result.ok("R06-no-orphan-methods", "no methods/ dir")
        return

    declared_ids = {p.get("id") for p in manifest.get("phases", [])}
    orphans = []

    for md_file in sorted(methods_dir.glob("*.md")):
        match = re.match(r"^(\d+)-", md_file.name)
        if match:
            file_phase_id = int(match.group(1))
            if file_phase_id not in declared_ids:
                orphans.append(md_file.name)

    if orphans:
        result.fail("R06-no-orphan-methods", f"undeclared method files: {orphans}")
    else:
        result.ok("R06-no-orphan-methods")


def check_config_has_thresholds(instrument_dir: Path, result: ValidationResult) -> None:
    """Rule 7: config.yaml has thresholds section."""
    config_path = instrument_dir / "config.yaml"
    if not config_path.exists():
        result.fail("R07-config-thresholds", "config.yaml not found")
        return

    config = load_yaml(config_path)
    if config is None:
        result.fail("R07-config-thresholds", "config.yaml failed to parse")
        return

    if "thresholds" in config:
        result.ok("R07-config-thresholds")
    else:
        result.fail("R07-config-thresholds", "no 'thresholds' section in config.yaml")


def check_fixes_readme(instrument_dir: Path, result: ValidationResult) -> None:
    """Rule 8: fixes/README.md exists."""
    fixes_readme = instrument_dir / "fixes" / "README.md"
    if fixes_readme.exists():
        result.ok("R08-fixes-readme")
    else:
        result.fail("R08-fixes-readme", "fixes/README.md not found")


def check_report_prefix(
    instrument_dir: Path, manifest: dict, result: ValidationResult
) -> None:
    """Rule 9: report_prefix matches templates/report-template.md run: field."""
    prefix = manifest.get("report_prefix")
    if not prefix:
        result.fail("R09-report-prefix", "report_prefix not set in manifest")
        return

    template_path = instrument_dir / "templates" / "report-template.md"
    if not template_path.exists():
        result.fail("R09-report-prefix", "templates/report-template.md not found")
        return

    content = template_path.read_text()
    # Look for run: PREFIX{n} or run: PREFIX{...} pattern in frontmatter
    pattern = rf"run:\s+{re.escape(prefix)}"
    if re.search(pattern, content):
        result.ok("R09-report-prefix")
    else:
        result.fail(
            "R09-report-prefix",
            f"prefix '{prefix}' not found in report-template.md run: field",
        )


def check_qualitoscope_registration(
    manifest: dict, result: ValidationResult
) -> None:
    """Rule 10: id and dr_sections match qualitoscope/config.yaml (if registered)."""
    qs_config = load_qualitoscope_config()
    if qs_config is None:
        result.ok("R10-qualitoscope-registration", "qualitoscope/config.yaml not found, skipped")
        return

    instrument_id = manifest.get("id")
    instrument_name = manifest.get("name")
    manifest_sections = manifest.get("dr_sections", [])
    instruments = qs_config.get("instruments", [])

    # Find matching entry by id or name
    match = None
    for entry in instruments:
        if entry.get("id") == instrument_id or entry.get("name") == instrument_name:
            match = entry
            break

    if match is None:
        result.ok("R10-qualitoscope-registration", "not registered in qualitoscope/config.yaml")
        return

    # Check id match
    if match.get("id") != instrument_id:
        result.fail(
            "R10-qualitoscope-registration",
            f"id mismatch: manifest={instrument_id}, qualitoscope={match.get('id')}",
        )
        return

    # Check sections match
    qs_sections = sorted(match.get("sections", []))
    manifest_sections_sorted = sorted(manifest_sections)
    if qs_sections != manifest_sections_sorted:
        result.fail(
            "R10-qualitoscope-registration",
            f"dr_sections mismatch: manifest={manifest_sections_sorted}, "
            f"qualitoscope={qs_sections}",
        )
    else:
        result.ok("R10-qualitoscope-registration")


def validate_instrument(instrument_dir: Path) -> ValidationResult:
    """Run all 10 validation checks against an instrument directory."""
    result = ValidationResult(instrument_dir)

    # Rule 1: manifest exists and parses
    manifest = check_manifest_exists(instrument_dir, result)
    if manifest is None:
        return result

    # Rules 2-3: schema basics
    check_spec_version(manifest, result)
    check_required_fields(manifest, result)

    # Rules 4-6: file structure
    check_required_files_exist(instrument_dir, manifest, result)
    check_phases_have_methods(instrument_dir, manifest, result)
    check_no_orphan_methods(instrument_dir, manifest, result)

    # Rules 7-8: config and fixes
    check_config_has_thresholds(instrument_dir, result)
    check_fixes_readme(instrument_dir, result)

    # Rule 9: report prefix consistency
    check_report_prefix(instrument_dir, manifest, result)

    # Rule 10: qualitoscope registration
    check_qualitoscope_registration(manifest, result)

    return result


def main() -> int:
    """CLI entry point. Validates one or more instrument directories."""
    if len(sys.argv) < 2:
        print("Usage: python -m cli.validate_instrument <instrument_dir> [...]", file=sys.stderr)
        return 1

    exit_code = 0
    for arg in sys.argv[1:]:
        instrument_dir = Path(arg).resolve()
        if not instrument_dir.is_dir():
            print(f"ERROR: {arg} is not a directory", file=sys.stderr)
            exit_code = 1
            continue

        result = validate_instrument(instrument_dir)

        print(f"\n{'=' * 60}")
        print(f"Instrument: {instrument_dir.name}")
        print(f"{'=' * 60}")

        for msg in result.passes:
            print(f"  {msg}")
        for msg in result.failures:
            print(f"  {msg}")

        status = "PASS" if result.passed else "FAIL"
        print(f"\n  Result: {status} ({len(result.passes)} passed, {len(result.failures)} failed)")

        if not result.passed:
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
