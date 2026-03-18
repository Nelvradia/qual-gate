# qualitoscope/

**Pure orchestrator for all qual-gate quality instruments.** Delegates to 12 domain tomographes (under `instruments/`), resolves finding overlaps, cross-correlates across instruments, computes S14 (Overall Summary), produces unified DR reports, and tracks project health trends. Does not perform domain scanning itself — every finding originates from a delegated instrument.

**Covers DR Section:** S14 (Overall Summary — aggregated from all instruments)

**Delegates to:** All 12 domain instruments covering S1–S13, K1–K4

---

## Quick Start

```bash
# Full scan (all instruments + S14)
"Read qualitoscope/README.md and execute a full Qualitoscope scan."

# DR Mode (produce a complete Design Review)
"Read qualitoscope/README.md and execute DR Mode for Phase 2 closeout."

# Targeted scan (specific instruments only)
"Read qualitoscope/README.md and execute a targeted scan for security + compliance."

# Delta scan
"Read qualitoscope/README.md and execute a delta scan vs the last run."
```

---

## Scan Phases

| Phase | Name | What It Does | Key Inputs |
|-------|------|-------------|------------|
| **1** | Instrument Inventory | Verify all instruments are present, configured, and runnable | Directory listing, config.yaml validation |
| **2** | Delegation | Invoke each instrument (or validate freshness of cached output) | Instrument READMEs, cached output JSON |
| **3** | Overlap Resolution | Deduplicate findings from instruments with shared concerns | Ownership table, instrument outputs |
| **4** | Cross-Correlation | Detect findings that span multiple instruments | All instrument outputs, correlation rules |
| **5** | S14 Aggregation | Compute Overall Summary — severity counts, composite score, verdict | Deduplicated findings from Phase 3-4 |
| **6** | DR Synthesis | Map instrument outputs to DR-TEMPLATE sections (DR Mode only) | DR-TEMPLATE, instrument→section mapping |
| **7** | Delta Analysis | Compare this run with previous runs for trend tracking | Current + previous QS reports |
| **8** | Report | Compile unified Qualitoscope report | All phase outputs |

---

## Phase 1 — Instrument Inventory

**Goal:** Verify all 12 instruments are present, correctly structured, and have valid configuration.

### Instrument Registry

| ID | Instrument | DR Sections | Location | Repo |
|----|-----------|-------------|----------|------|
| I01 | `architecture-tomographe` | S1 (Architecture) | `instruments/architecture-tomographe/` | qual-gate |
| I02 | `test-tomographe` | S4 (Validation) | `instruments/test-tomographe/` | qual-gate |
| I03 | `code-tomographe` | S3, S13 (Code, Maintainability) | `instruments/code-tomographe/` | qual-gate |
| I04 | `documentation-tomographe` | S2, K2, K3, K4 (Docs, Glossary, Design-to-Impl, Cross-Doc) | `instruments/documentation-tomographe/` | qual-gate |
| I05 | `compliance-tomographe` | S6, S12, K1 (Config, Licensing, Permissions) | `instruments/compliance-tomographe/` | qual-gate |
| I06 | `data-tomographe` | S8 (Data Management) | `instruments/data-tomographe/` | qual-gate |
| I07 | `deployment-tomographe` | S9 (Deployment) | `instruments/deployment-tomographe/` | qual-gate |
| I08 | `observability-tomographe` | S7 (Observability) | `instruments/observability-tomographe/` | qual-gate |
| I09 | `security-tomographe` | S5 (Security) | `instruments/security-tomographe/` | qual-gate |
| I10 | `performance-tomographe` | S10 (Performance) | `instruments/performance-tomographe/` | qual-gate |
| I11 | `ux-tomographe` | S11 (UX) | `instruments/ux-tomographe/` | qual-gate |
| I12 | `ai-ml-tomographe` | AI/ML Quality (new dimension) | `instruments/ai-ml-tomographe/` | qual-gate |

### Steps

```bash
# Verify all instrument directories exist
for inst in architecture-tomographe test-tomographe code-tomographe documentation-tomographe \
  compliance-tomographe data-tomographe deployment-tomographe \
  observability-tomographe security-tomographe performance-tomographe \
  ux-tomographe ai-ml-tomographe; do
  if [ -d "instruments/$inst" ]; then
    echo "OK: instruments/$inst"
  else
    echo "MISSING: instruments/$inst"
  fi
done

# Verify each instrument has required structure
for inst in code-tomographe documentation-tomographe compliance-tomographe \
  data-tomographe deployment-tomographe observability-tomographe \
  security-tomographe performance-tomographe ux-tomographe ai-ml-tomographe; do
  echo "--- instruments/$inst ---"
  [ -f "instruments/$inst/README.md" ]      && echo "  README.md: OK"      || echo "  README.md: MISSING"
  [ -f "instruments/$inst/config.yaml" ]    && echo "  config.yaml: OK"    || echo "  config.yaml: MISSING"
  [ -d "output" ]                           && echo "  output/: OK"             || echo "  output/: MISSING (create before running)"
  [ -d "instruments/$inst/templates" ]      && echo "  templates/: OK"     || echo "  templates/: MISSING"
  [ -d "instruments/$inst/checklists" ]     && echo "  checklists/: OK"    || echo "  checklists/: MISSING"
done

# Validate config.yaml files parse correctly
for inst in code-tomographe compliance-tomographe data-tomographe \
  deployment-tomographe documentation-tomographe observability-tomographe \
  security-tomographe performance-tomographe ux-tomographe ai-ml-tomographe; do
  yq '.' "instruments/$inst/config.yaml" > /dev/null 2>&1 \
    && echo "OK: instruments/$inst/config.yaml" \
    || echo "INVALID YAML: instruments/$inst/config.yaml"
done
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Instrument directory missing entirely | **Critical** |
| README.md or config.yaml missing | **Major** |
| config.yaml invalid YAML | **Major** |
| output/ or templates/ directory missing | **Minor** |
| checklists/ directory missing | **Observation** |

### Output: `output/phase1-instrument-inventory.json`

```json
{
  "timestamp": "ISO-8601",
  "instruments_expected": 12,
  "instruments_found": 12,
  "instruments_valid": 12,
  "details": [
    {
      "id": "I01",
      "name": "architecture-tomographe",
      "present": true,
      "has_readme": true,
      "has_config": true,
      "has_output_dir": true,  // refers to output/ at repo root
      "config_valid": true,
      "last_run": "ISO-8601 or null"
    }
  ]
}
```

---

## Phase 2 — Delegation

**Goal:** Invoke each instrument to produce fresh output, or validate that cached output is sufficiently recent.

### Freshness Rules

| Mode | Rule |
|------|------|
| **Quick Scan** | Reuse cached output if < `freshness_window_hours` old (default: 24h) |
| **DR Mode** | Always re-run all instruments fresh (no cache) |
| **Targeted** | Re-run only the specified instruments; reuse others if fresh |

### Steps

```bash
# PROJECT_NAME is read from qualitoscope/config.yaml
# For each instrument, check output freshness
for inst in architecture-tomographe test-tomographe code-tomographe documentation-tomographe \
  compliance-tomographe data-tomographe deployment-tomographe \
  observability-tomographe security-tomographe performance-tomographe \
  ux-tomographe ai-ml-tomographe; do

  latest="output/${YYYYMMDD}_${PROJECT_NAME}/${inst}-latest.json"
  if [ -f "$latest" ]; then
    age_hours=$(( ( $(date +%s) - $(stat -c %Y "$latest") ) / 3600 ))
    echo "instruments/$inst: output is ${age_hours}h old"
  else
    echo "instruments/$inst: no output found — must run"
  fi
done
```

### Delegation Protocol

For each instrument that needs to run:

1. Read the instrument's `README.md` for methodology
2. Execute a full scan following the instrument's phase sequence
3. Verify output files were produced in `output/YYYY-MM-DD_{project_name}/`
4. Read the instrument's report from `output/YYYY-MM-DD_{project_name}/`
5. Record the instrument's findings in the Qualitoscope's working set

**Parallel execution:** Instruments are independent — up to 5 can be delegated concurrently using sub-agents. Group by estimated run time:
- Fast (static analysis): code, documentation, compliance, deployment (~2-3 min each)
- Medium (data inspection): data, observability, AI/ML (~5-10 min each)
- Slow (live testing): security, performance, UX, test (~10-20 min each)

### Severity Rules

| Finding | Severity |
|---------|----------|
| Instrument fails to produce output (error during scan) | **Major** |
| Instrument output is stale and re-run was skipped | **Minor** |
| Instrument output present and fresh | **OK** |

### Output: `output/phase2-delegation.json`

```json
{
  "timestamp": "ISO-8601",
  "mode": "full|dr|targeted",
  "instruments_invoked": 12,
  "instruments_succeeded": 12,
  "instruments_failed": 0,
  "instruments_cached": 0,
  "details": [
    {
      "id": "I01",
      "name": "architecture-tomographe",
      "action": "invoked|cached|skipped",
      "output_path": "output/YYYY-MM-DD_{project_name}/AR1-architecture.md",
      "findings_count": 5,
      "critical": 0,
      "major": 1,
      "minor": 3,
      "observation": 1
    }
  ]
}
```

---

## Phase 3 — Overlap Resolution

**Goal:** Deduplicate findings from instruments that check the same thing. Apply ownership rules to determine which instrument is authoritative for each overlapping concern.

### Ownership Table

| Overlap Area | Primary Owner | Secondary | Resolution Rule |
|---|---|---|---|
| **Privacy tiers (P0-P3)** | data | compliance | `data` owns classification checking ("column X is P2"). `compliance` owns policy compliance ("P2 data has retention policy"). Deduplicate classification findings — keep `data`'s version. |
| **Permission System** | compliance | security | `compliance` owns config completeness (all domains registered, metrics defined). `security` owns access control correctness (does the permission service actually block?). Findings about *missing* entries → `compliance`. Findings about *bypass* → `security`. |
| **Supply chain / deps** | security | code | `security` owns vulnerability scanning (CVEs, advisories). `code` owns dependency health (outdated, bloat, MSRV). If both flag the same crate, keep `security`'s severity rating. |
| **Health endpoints** | observability | performance | `observability` owns endpoint existence and correctness. `performance` owns response time and resource cost. Deduplicate existence checks — keep `observability`'s version. |
| **VERSION files** | deployment | documentation | `deployment` owns release process (tag matches VERSION). `documentation` owns cross-doc coherence (VERSION matches docs). Different aspects of same artifact — both findings kept, tagged with owner. |
| **AI personality configuration** | UX | AI/ML, security | `UX` owns personality consistency. `AI/ML` owns prompt quality. `security` owns manipulation resistance. Three distinct aspects — all kept, tagged with owner. |
| **Prompt injection** | security | AI/ML | `security` owns attack detection. `AI/ML` owns quality degradation measurement. If both flag, merge into single finding with `security` severity. |
| **Audit trail** | observability | security | `observability` owns log completeness. `security` owns access logging correctness. Different aspects — both kept, tagged. |

### Steps

1. Load all instrument findings from Phase 2
2. For each finding, compute a fingerprint (file + check_type + location)
3. Group findings with matching fingerprints
4. For each group with >1 finding:
   a. Look up the overlap area in the ownership table
   b. Keep the primary owner's finding; discard or demote the secondary's
   c. Tag the kept finding with `resolved_overlap: true` and `secondary_instrument: X`
5. Findings with no overlap pass through unchanged

### Severity Rules

| Finding | Severity |
|---------|----------|
| Overlap found and resolved per ownership table | **OK** (informational) |
| Overlap found but instruments disagree on severity | **Observation** — flag for human review |
| Overlap found for area not in ownership table | **Minor** — new overlap needs ownership rule |

### Output: `output/phase3-overlap-resolution.json`

```json
{
  "timestamp": "ISO-8601",
  "total_findings_before_dedup": 47,
  "overlaps_detected": 6,
  "overlaps_resolved": 5,
  "overlaps_flagged": 1,
  "total_findings_after_dedup": 42,
  "resolved": [
    {
      "fingerprint": "permission-config.yaml:domain_count",
      "overlap_area": "Permission System",
      "primary": "compliance",
      "discarded_from": "security",
      "severity_agreed": true
    }
  ],
  "flagged": [
    {
      "fingerprint": "src/llm/sanitize.rs:input_validation",
      "overlap_area": "Prompt injection",
      "instruments": ["security", "ai-ml"],
      "security_severity": "Major",
      "ai_ml_severity": "Minor",
      "reason": "Severity disagreement — requires human review"
    }
  ]
}
```

---

## Phase 4 — Cross-Correlation

**Goal:** Detect findings that span multiple instruments — issues that no single instrument can catch because they require information from two or more domains.

### Correlation Rules

| ID | Rule | Instruments | What It Catches |
|----|------|------------|-----------------|
| **XC-01** | High-churn file is also a permission module | test × security | Security-sensitive code with inadequate test coverage |
| **XC-02** | New component added but no permission entry | code × compliance | Component bypasses permission system |
| **XC-03** | DB migration landed but schema documentation not updated | data × documentation | Schema map drift |
| **XC-04** | New metric registered but no dashboard panel | observability × documentation | Observable data with no visibility |
| **XC-05** | AI configuration changed but no prompt quality eval | AI/ML × documentation | Prompt regression risk |
| **XC-06** | CI job added but not merge-blocking | deployment × test | Test exists but doesn't gate anything |
| **XC-07** | UX component added but no accessibility test | UX × test | Accessibility gap for new UI |
| **XC-08** | Dependency updated but security scan stale | code × security | Supply chain vulnerability window |

### Steps

For each correlation rule:

```
XC-01: High-churn + permission module
  1. From test instrument: get list of high-churn files (top 20% by commit frequency)
  2. From security instrument: get list of permission modules (files in src/permissions/)
  3. Intersect: files that appear in both lists
  4. For each intersection: check test coverage from test instrument
  5. Flag if coverage < 80% for a high-churn permission file

XC-02: New component without permission entry
  1. From code instrument: get list of all registered components (component domain registrations)
  2. From compliance instrument: get list of all permission configuration domain entries
  3. Diff: components present in code but absent from permission configuration
  4. Flag each missing entry as Critical (bypasses permission system)

XC-03: Migration without schema documentation update
  1. From data instrument: get latest migration version per database
  2. From documentation instrument: get schema documentation declared versions
  3. Compare: if migration version > documented version → schema documentation is stale
  4. Flag as Minor (documentation drift, not a functional bug)

XC-04: Metric without dashboard
  1. From observability instrument: get list of registered Prometheus metrics
  2. From documentation instrument: get list of Grafana dashboard panels (if dashboards scanned)
  3. Diff: metrics with no corresponding dashboard panel
  4. Flag as Observation (data exists but isn't visualized)

XC-05: AI configuration change without eval
  1. From documentation instrument: check AI configuration last-modified date
  2. From AI/ML instrument: check last prompt quality evaluation date
  3. If AI configuration modified after last eval → prompt regression risk
  4. Flag as Minor (needs re-evaluation, not necessarily broken)

XC-06: CI job not gating
  1. From deployment instrument: get list of all CI jobs
  2. From test instrument: get list of merge-blocking jobs
  3. Diff: jobs that run tests but aren't merge-blocking
  4. Flag as Minor (test exists but doesn't prevent bad merges)

XC-07: UX component without a11y test
  1. From UX instrument: get list of UI components
  2. From test instrument: get list of accessibility test targets
  3. Diff: components with no a11y test coverage
  4. Flag as Minor (new component should have a11y coverage)

XC-08: Dep update without security scan
  1. From code instrument: get list of recently updated dependencies (Cargo.lock changes)
  2. From security instrument: get last supply chain scan date
  3. If deps updated after last scan → vulnerability window exists
  4. Flag as Minor (re-run security scan to close the window)
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Component bypasses permission system (XC-02) | **Critical** |
| High-churn permission file with low coverage (XC-01) | **Major** |
| Supply chain vulnerability window (XC-08) | **Major** |
| Schema map drift (XC-03) | **Minor** |
| Prompt regression risk (XC-05) | **Minor** |
| CI job not gating (XC-06) | **Minor** |
| UX component without a11y test (XC-07) | **Minor** |
| Metric without dashboard (XC-04) | **Observation** |

### Output: `output/phase4-cross-correlation.json`

```json
{
  "timestamp": "ISO-8601",
  "rules_evaluated": 8,
  "rules_triggered": 3,
  "cross_findings": [
    {
      "rule": "XC-02",
      "severity": "Critical",
      "description": "Component 'payments' has no permission configuration entry",
      "instruments": ["code", "compliance"],
      "evidence": {
        "code": "src/components/payments.rs: component domain registration returns 'payments'",
        "compliance": "permission configuration domains list does not contain 'payments'"
      }
    }
  ]
}
```

---

## Phase 5 — S14 Aggregation

**Goal:** Compute the Overall Summary (DR Section S14) from all deduplicated and cross-correlated findings. This is the only DR section that no individual instrument produces — it's the Qualitoscope's unique contribution.

### Steps

1. Collect all findings from Phase 3 (deduplicated) + Phase 4 (cross-correlated)
2. Count by severity:

```
| Severity    | Count |
|-------------|-------|
| Critical    |       |
| Major       |       |
| Minor       |       |
| Observation |       |
| OK          |       |
```

3. Compute composite health score:

```
score = 1.0
  - (critical_count × 0.25)      # each Critical knocks 25%
  - (major_count × 0.10)          # each Major knocks 10%
  - (minor_count × 0.02)          # each Minor knocks 2%
  - (observation_count × 0.005)   # each Observation knocks 0.5%

# Clamp to [0.0, 1.0]
# Interpret:
#   >= 0.90  → Green
#   >= 0.70  → Yellow
#   >= 0.50  → Red
#   <  0.50  → Critical
```

4. Apply verdict rules:

| Verdict | Rule |
|---------|------|
| **PASS** | 0 Critical, 0 Major |
| **PASS-WITH-CONDITIONS** | 0 Critical, ≤3 Major with tracking issues created |
| **FAIL** | ≥1 Critical, OR >3 Major, OR untracked Major |

5. Identify weakest and strongest sections:
   - Weakest: DR section with highest severity-weighted finding count
   - Strongest: DR section with fewest or zero findings

6. Compute trajectory (requires ≥2 runs):
   - Compare current severity counts with previous run
   - Classify: **Improving** (fewer findings) / **Stable** (±10%) / **Degrading** (more findings)

### Output: `output/phase5-s14-aggregation.json`

```json
{
  "timestamp": "ISO-8601",
  "total_findings": 42,
  "severity_counts": {
    "critical": 0,
    "major": 2,
    "minor": 11,
    "observation": 8,
    "ok": 21
  },
  "composite_score": 0.74,
  "composite_rating": "Yellow",
  "verdict": "PASS-WITH-CONDITIONS",
  "weakest_section": "S5 (Security)",
  "strongest_section": "S1 (Architecture)",
  "trajectory": "Improving",
  "trajectory_detail": {
    "previous_run": "QS1",
    "previous_score": 0.68,
    "delta": "+0.06",
    "critical_delta": 0,
    "major_delta": -1,
    "minor_delta": -3
  }
}
```

---

## Phase 6 — DR Synthesis (DR Mode Only)

**Goal:** Map instrument outputs to DR-TEMPLATE sections, producing a complete Design Review report. This phase is skipped during Quick Scan and Targeted Scan modes.

### DR Section → Instrument Mapping

| DR Section | Primary Instrument | Secondary | Notes |
|---|---|---|---|
| S1 Architecture | I01 `architecture-tomographe` | — | Pattern fitness, violations, drift |
| S2 Documentation | I04 `documentation-tomographe` | — | Doc inventory, staleness, cross-refs |
| S3 Code Quality | I03 `code-tomographe` | — | fmt, clippy, complexity, duplication |
| S4 Validation | I02 `test-tomographe` | — | Test coverage, health, alignment |
| S5 Security | I09 `security-tomographe` | I12 `ai-ml-tomographe` | AI threats from I12 feed into S5 |
| S6 Configuration | I05 `compliance-tomographe` | — | Config validation, env management |
| S7 Observability | I08 `observability-tomographe` | — | Metrics, alerting, logging, dashboards |
| S8 Data Management | I06 `data-tomographe` | — | Schema, migrations, privacy, backup |
| S9 Deployment | I07 `deployment-tomographe` | — | CI, reproducibility, rollback, release |
| S10 Performance | I10 `performance-tomographe` | — | Profiling, benchmarks, resource usage |
| S11 UX | I11 `ux-tomographe` | — | Components, a11y, personality, flows |
| S12 Licensing | I05 `compliance-tomographe` | — | License compat, export control |
| S13 Maintainability | I03 `code-tomographe` | — | Tech debt, complexity scoring |
| S14 Overall Summary | Phase 5 output | — | Aggregated from all instruments |
| K1 Permission System | I05 `compliance-tomographe` | I09 `security-tomographe` | Completeness from I05, correctness from I09 |
| K2 Glossary | I04 `documentation-tomographe` | — | lint_glossary.py results |
| K3 Design-to-Impl | I04 `documentation-tomographe` | — | Phase 4 delta analysis |
| K4 Cross-Doc | I04 `documentation-tomographe` | — | Schema/metrics documentation coherence |

### Steps

1. Load the DR-TEMPLATE from `docs/reviews/DR-TEMPLATE.md`
2. For each DR section (S1–S13, K1–K4):
   a. Look up the responsible instrument(s) in the mapping table
   b. Load findings for that instrument from Phase 3 output (deduplicated)
   c. Map findings to the section's checklist items
   d. Rate each checklist item: OK / Observation / Minor / Major / Critical
   e. Write the section conclusion and reviewer comments
3. Insert S14 from Phase 5 output
4. Compute section-level sub-verdicts
5. Write the completed DR report to `output/DR{n}-{target}.md`
6. Generate the action register from all Minor+ findings
7. Assign priority to each action item (P1–P4)

### Output: `output/YYYY-MM-DD_{project_name}/DR{n}-{target}.md` + `output/YYYY-MM-DD_{project_name}/phase6-dr-synthesis.json`

The DR report follows the project's `DR-TEMPLATE.md` format. The JSON contains metadata about the synthesis process.

---

## Phase 7 — Delta Analysis

**Goal:** Compare the current scan with previous runs to identify trends and regressions.

### Steps

```bash
# List all previous QS reports
ls -t output/*_${PROJECT_NAME}/QS*.json 2>/dev/null

# Compare current vs previous
# For each instrument:
#   current_findings[instrument] - previous_findings[instrument]
#   → new findings (regressions)
#   → resolved findings (improvements)
```

### Metrics Tracked

| Metric | Computation |
|--------|------------|
| **Total findings** | Sum of all severities |
| **Composite score** | Weighted severity formula from Phase 5 |
| **Per-section trend** | Each DR section's finding count over time |
| **Regression count** | New findings not present in previous run |
| **Resolution count** | Previous findings no longer present |
| **Time to resolution** | Average runs between finding-created and finding-resolved |
| **Worst regressor** | DR section with most new findings |
| **Best improver** | DR section with most resolved findings |

### Severity Rules

| Finding | Severity |
|---------|----------|
| Critical regression (new Critical finding) | **Critical** |
| Major regression (new Major finding) | **Major** |
| Score dropped >10% vs previous run | **Major** |
| Score dropped 5-10% | **Minor** |
| Score stable or improved | **OK** |
| First run (no baseline) | **Observation** (no comparison possible) |

### Output: `output/phase7-delta-analysis.json`

```json
{
  "timestamp": "ISO-8601",
  "current_run": "QS2",
  "previous_run": "QS1",
  "score_current": 0.74,
  "score_previous": 0.68,
  "score_delta": "+0.06",
  "trajectory": "Improving",
  "regressions": 2,
  "resolutions": 8,
  "worst_regressor": "S5 (Security)",
  "best_improver": "S3 (Code Quality)",
  "per_section": [
    {
      "section": "S1",
      "current_findings": 3,
      "previous_findings": 5,
      "delta": -2,
      "trend": "Improving"
    }
  ]
}
```

---

## Phase 8 — Report

**Goal:** Compile all phase outputs into a unified Qualitoscope report.

### Report Variants

| Mode | Report File | Contents |
|------|------------|----------|
| **Quick Scan** | `output/YYYY-MM-DD_{project_name}/QS{n}-qualitoscope.md` | Phases 1-5 + 7-8 (no DR synthesis) |
| **DR Mode** | `output/YYYY-MM-DD_{project_name}/QS{n}-qualitoscope.md` + `output/YYYY-MM-DD_{project_name}/DR{n}-{target}.md` | All 8 phases including DR report |
| **Targeted** | `output/YYYY-MM-DD_{project_name}/QS{n}-qualitoscope-targeted.md` | Subset of instruments + cross-correlations |

### Steps

1. Merge all phase JSON outputs
2. Apply severity ratings per finding
3. Fill report template (`templates/report-template.md`)
4. Compute overall verdict
5. Generate action register with GitLab issue references
6. Write final report

---

## Output Directory Structure

```
qualitoscope/
├── README.md                          # This file
├── config.yaml                        # Orchestration config
├── methods/
│   ├── 01-instrument-inventory.md
│   ├── 02-delegation.md
│   ├── 03-overlap-resolution.md
│   ├── 04-cross-correlation.md
│   ├── 05-s14-aggregation.md
│   ├── 06-dr-synthesis.md
│   ├── 07-delta-analysis.md
│   └── 08-report.md
├── checklists/
│   ├── instrument-readiness.md        # All 12 instruments present and configured
│   ├── dr-section-mapping.md          # Instrument → DR section mapping
│   └── overlap-ownership.md           # Ownership rules for shared concerns
└── templates/
    └── report-template.md

output/                                  ← repo root
└── YYYY-MM-DD_{project_name}/           ← one folder per run
    ├── QS{n}-qualitoscope.md
    ├── DR{n}-{target}.md
    ├── AR{n}-architecture.md
    ├── CQ{n}-code.md
    ├── SS{n}-security.md
    ├── ... (all instrument reports)
    ├── phase1-instrument-inventory.json
    ├── phase2-delegation.json
    └── scratch/
        ├── security/
        └── code/
```

---

## Configuration (config.yaml)

```yaml
project_name: ""   # e.g. "my-project"

base_dir: instruments

instruments:
  - id: I01
    name: architecture-tomographe
    sections: [S1]
  - id: I02
    name: test-tomographe
    sections: [S4]
  - id: I03
    name: code-tomographe
    sections: [S3, S13]
  - id: I04
    name: documentation-tomographe
    sections: [S2, K2, K3, K4]
  - id: I05
    name: compliance-tomographe
    sections: [S6, S12, K1]
  - id: I06
    name: data-tomographe
    sections: [S8]
  - id: I07
    name: deployment-tomographe
    sections: [S9]
  - id: I08
    name: observability-tomographe
    sections: [S7]
  - id: I09
    name: security-tomographe
    sections: [S5]
  - id: I10
    name: performance-tomographe
    sections: [S10]
  - id: I11
    name: ux-tomographe
    sections: [S11]
  - id: I12
    name: ai-ml-tomographe
    sections: [AI-ML]

thresholds:
  verdict:
    pass_max_critical: 0
    pass_max_major: 0
    conditional_max_critical: 0
    conditional_max_major: 3
  composite_score:
    green: 0.90
    yellow: 0.70
    red: 0.50

freshness:
  quick_scan_hours: 24
  targeted_scan_hours: 12
  dr_mode: always_fresh

delegation:
  max_parallel: 5
  timeout_minutes: 30

delta:
  output_root: output/   # folders created as output/YYYY-MM-DD_{project_name}/
  keep_runs: 20
```

---

## Severity & Verdict

Same severity scale as all other instruments (OK / Observation / Minor / Major / Critical).

| Verdict | Rule |
|---------|------|
| **PASS** | 0 Critical, 0 Major |
| **PASS-WITH-CONDITIONS** | 0 Critical, ≤3 Major with tracking issues |
| **FAIL** | ≥1 Critical, OR >3 Major, OR untracked Major |

---

## Run History

| Run | Date | Mode | Instruments | Findings | Score | Verdict | Report |
|-----|------|------|-------------|----------|-------|---------|--------|

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../LICENSE).
