# Phase 6 — DR Synthesis (DR Mode Only)

Map instrument outputs to DR-TEMPLATE sections, producing a complete Design Review report. Skipped during Quick Scan and Targeted Scan modes.

## Inputs
- All phase outputs (Phases 1-5)
- DR-TEMPLATE from `docs/reviews/DR-TEMPLATE.md`
- Section mapping from `checklists/dr-section-mapping.md`

## Steps
1. Load the DR-TEMPLATE
2. For each DR section (S1-S13, K1-K4):
   a. Look up responsible instrument(s) in mapping
   b. Load deduplicated findings for that instrument
   c. Map findings to section checklist items
   d. Rate each item: OK / Observation / Minor / Major / Critical
   e. Write section conclusion and comments
3. Insert S14 from Phase 5 output
4. Compute section-level sub-verdicts
5. Generate action register from all Minor+ findings
6. Assign priority: P1 (Critical), P2 (Major), P3 (Minor), P4 (Observation)
7. Write completed DR to `output/DR{n}-{target}.md`

## Output
- `output/DR{n}-{target}.md` (complete Design Review)
- `output/phase6-dr-synthesis.json` (synthesis metadata)

## Checklist Reference
- `checklists/dr-section-mapping.md`
