# Phase 1 — Profile Validation & Instrument Inventory

Phase 1 requires `project-profile.yaml` to exist. If absent, Phase 0 should have run first.
If Phase 0 was skipped and no profile exists, Phase 1 reports a Critical finding (profile missing).

Validate the target project's profile, then verify all 13 instruments are present, correctly structured, and have valid configuration.

## Inputs
- `project-profile.yaml` in target project root
- Directory listing of project root
- Each instrument's `config.yaml`

## Step 0 — Profile Validation

Before checking instruments, validate the project profile:

1. **Check profile existence:** Look for `project-profile.yaml` in the target project root.
   - If missing: **Critical** — cannot proceed without a profile. Instruct the user to create one from `project-profile.example.yaml`.
2. **Validate required fields:**
   - `name` must be a non-empty string → **Critical** if missing or empty.
   - `stack.languages` must be a non-empty list of strings → **Critical** if missing or empty.
3. **Type-check optional fields:** For each declared field, verify the value matches the expected type from `project-profile.schema.yaml`.
   - Wrong type (e.g. string where list expected) → **Minor**.
4. **Path existence check:** For each path field that is declared (non-null), check whether the path exists in the target project.
   - Declared path does not exist → **Observation** (logged, not blocking — the path may be created later).
5. **Apply defaults:** For any optional field not declared in the profile, apply the default from the schema. Log which defaults were applied at DEBUG level.

### Profile Severity Rules

| Finding | Severity |
|---------|----------|
| `project-profile.yaml` missing entirely | **Critical** |
| `name` missing or empty | **Critical** |
| `stack.languages` missing or empty | **Critical** |
| Optional field has wrong type | **Minor** |
| Declared path does not exist on disk | **Observation** |
| Optional field absent (default applied) | **OK** (logged) |

## Steps (Instrument Inventory)

1. Check each instrument directory exists
2. Validate required files: `README.md`, `config.yaml`, `output/`, `templates/`, `checklists/`
3. Parse `config.yaml` for valid YAML syntax
4. Check DR section coverage: every section S1–S13, K1–K4 mapped to at least one instrument
5. Record last run date from each instrument's output directory

## Output
- `output/phase1-instrument-inventory.json`

## Severity Rules (Instrument Inventory)

| Finding | Severity |
|---------|----------|
| Instrument directory missing entirely | **Critical** |
| README.md or config.yaml missing | **Major** |
| config.yaml invalid YAML | **Major** |
| output/ or templates/ directory missing | **Minor** |
| checklists/ directory missing | **Observation** |

## Checklist Reference
- `checklists/instrument-readiness.md`
