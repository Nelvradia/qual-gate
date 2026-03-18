# Phase 1 — Instrument Inventory

Verify all 13 instruments are present, correctly structured, and have valid configuration.

## Inputs
- Directory listing of project root
- Each instrument's `config.yaml`

## Steps
1. Check each instrument directory exists
2. Validate required files: `README.md`, `config.yaml`, `output/`, `templates/`, `checklists/`
3. Parse `config.yaml` for valid YAML syntax
4. Check DR section coverage: every section S1–S13, K1–K4 mapped to at least one instrument
5. Record last run date from each instrument's output directory

## Output
- `output/phase1-instrument-inventory.json`

## Severity Rules
| Finding | Severity |
|---------|----------|
| Instrument directory missing entirely | Critical |
| README.md or config.yaml missing | Major |
| config.yaml invalid YAML | Major |
| output/ or templates/ directory missing | Minor |
| checklists/ directory missing | Observation |

## Checklist Reference
- `checklists/instrument-readiness.md`
