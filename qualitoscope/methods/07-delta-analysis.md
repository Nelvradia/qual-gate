# Phase 7 — Delta Analysis

Compare the current scan with previous runs to identify trends and regressions.

## Inputs
- Current run findings (Phases 3-5)
- Previous QS report JSON (`output/QS{n-1}*.json`)

## Steps
1. Load previous run's aggregated findings
2. Diff current vs previous:
   - New findings (regressions)
   - Resolved findings (improvements)
   - Changed severity (upgrades/downgrades)
3. Compute metrics:
   - Score delta (current - previous)
   - Per-section trend (each DR section's finding count over time)
   - Regression count and resolution count
   - Time to resolution (average runs between created and resolved)
4. Classify trajectory: Improving / Stable (±10%) / Degrading
5. Identify worst regressor and best improver sections

## Output
- `output/phase7-delta-analysis.json`

## Severity Rules
| Finding | Severity |
|---------|----------|
| New Critical finding (regression) | Critical |
| New Major finding (regression) | Major |
| Score dropped >10% | Major |
| Score dropped 5-10% | Minor |
| Score stable or improved | OK |
| First run (no baseline) | Observation |
