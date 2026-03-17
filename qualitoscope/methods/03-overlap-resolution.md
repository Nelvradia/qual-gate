# Phase 3 — Overlap Resolution

Deduplicate findings from instruments that check the same concern. Apply ownership rules to determine which instrument is authoritative.

## Inputs
- All instrument findings from Phase 2
- Ownership table from `checklists/overlap-ownership.md`

## Steps
1. Load all findings from all instruments
2. Compute fingerprint per finding: `{file}:{check_type}:{location}`
3. Group findings with matching fingerprints
4. For each group with >1 finding:
   a. Look up overlap area in ownership table
   b. Keep primary owner's finding, discard secondary's
   c. Tag kept finding: `resolved_overlap: true`, `secondary_instrument: X`
5. If instruments disagree on severity: flag for human review
6. If overlap area not in table: flag as new overlap needing rule
7. Single-instrument findings pass through unchanged

## Output
- `output/phase3-overlap-resolution.json`

## Severity Rules
| Finding | Severity |
|---------|----------|
| Overlap resolved per ownership table | OK |
| Severity disagreement between instruments | Observation |
| Overlap for area not in ownership table | Minor |

## Checklist Reference
- `checklists/overlap-ownership.md`
