# Phase 2 — Delegation

Invoke each instrument to produce fresh output, or validate that cached output is sufficiently recent.

## Inputs
- Phase 1 instrument inventory
- `config.yaml` freshness settings
- Scan mode (full / DR / targeted)

## Profile Resolution

Before delegating to instruments, resolve the project profile into instrument-specific configurations:

1. **Load validated profile** from Phase 1 output (`project-profile.yaml` already validated).
2. **Resolve path fields** — for each instrument, map profile path values to the instrument's expected config fields:
   | Profile Field | Instrument(s) | Config Key |
   |---|---|---|
   | `paths.source_dirs` | code, security, compliance, architecture | `scope.source_dirs` |
   | `paths.test_dirs` | test | `scope.test_dirs` |
   | `paths.docs_dir` | documentation | `scope.docs_dir` |
   | `paths.ci_config` | deployment | `scope.ci_config` |
   | `paths.compose_file` | deployment, security | `scope.compose_file` |
   | `architecture.layers` | architecture | `layers` |
   | `architecture.entry_points` | architecture | `entry_points` |
3. **Resolve conditional toggles** — for each instrument, determine which phases to skip:
   | Toggle | Instruments Affected | Phases Skipped When False |
   |---|---|---|
   | `toggles.permission_system` | compliance, security, architecture | AC1 (compliance Phase 3), access control (security Phase 7) |
   | `toggles.ai_ml_components` | security, ai-ml | AI threat model (security Phase 6) |
   | `toggles.gdpr_scope` | compliance | GDPR readiness (compliance Phase 4) |
   | `toggles.ai_act_scope` | compliance | AI Act readiness (compliance Phase 5) |
4. **Pass resolved config** to each instrument — instruments receive concrete paths and toggle values, not raw profile references.

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
