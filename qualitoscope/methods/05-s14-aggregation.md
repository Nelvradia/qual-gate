# Phase 5 — S14 Aggregation

Compute the Overall Summary (DR Section S14) from all deduplicated and cross-correlated findings. This is the only DR section not produced by any individual instrument.

## Inputs
- Deduplicated findings from Phase 3
- Cross-correlation findings from Phase 4

## Steps
1. Merge all findings (Phase 3 + Phase 4)
2. Count by severity: Critical, Major, Minor, Observation, OK
3. Compute composite health score:
   ```
   score = 1.0
     - (critical × 0.25)
     - (major × 0.10)
     - (minor × 0.02)
     - (observation × 0.005)
   Clamp to [0.0, 1.0]
   ```
4. Classify score: Green (≥0.90), Yellow (≥0.70), Red (≥0.50), Critical (<0.50)
5. Apply verdict rules:
   - PASS: 0 Critical, 0 Major
   - PASS-WITH-CONDITIONS: 0 Critical, ≤3 Major with tracking issues
   - FAIL: ≥1 Critical, OR >3 Major, OR untracked Major
6. Identify weakest section (highest severity-weighted count)
7. Identify strongest section (fewest findings)
8. Compute trajectory (requires ≥2 runs): Improving / Stable / Degrading

## Output
- `output/phase5-s14-aggregation.json`

## Severity Rules
| Finding | Severity |
|---------|----------|
| Composite score Critical (<0.50) | Critical |
| Composite score Red (0.50-0.69) | Major |
| Composite score Yellow (0.70-0.89) | Minor |
| Composite score Green (≥0.90) | OK |
