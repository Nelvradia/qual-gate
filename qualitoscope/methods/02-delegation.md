# Phase 2 — Delegation

Invoke each instrument to produce fresh output, or validate that cached output is sufficiently recent.

## Inputs
- Phase 1 instrument inventory
- `config.yaml` freshness settings
- Scan mode (full / DR / targeted)

## Steps
1. For each instrument in the inventory:
   a. Check if `output/latest.json` exists
   b. Compute age in hours: `(now - file_mtime) / 3600`
   c. Compare against freshness threshold for current scan mode
   d. If stale or DR mode: invoke the instrument (read its README.md, execute full scan)
   e. If fresh and not DR mode: reuse cached output
2. Record action taken per instrument (invoked / cached / skipped)
3. Verify output files were produced for invoked instruments
4. Load findings from each instrument's output

## Parallel Execution
Instruments are independent — up to `delegation.max_parallel` (default: 5) can run concurrently.

**Grouping by speed:**
- Fast (static): code, documentation, compliance, deployment
- Medium (data): data, observability, AI/ML
- Slow (live): security, performance, UX, test, architecture

## Output
- `output/phase2-delegation.json`

## Severity Rules
| Finding | Severity |
|---------|----------|
| Instrument fails to produce output | Major |
| Instrument output stale and re-run skipped | Minor |
| Instrument output present and fresh | OK |
