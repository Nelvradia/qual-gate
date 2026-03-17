---
instrument: qualitoscope
run: QS{n}
date: {date}
mode: {mode}
trigger: {trigger}
verdict: {verdict}
---

# Qualitoscope Report — QS{n}

**Date:** {date} | **Mode:** {mode} | **Trigger:** {trigger} | **Verdict:** {verdict}

## Executive Summary

| Metric | Value | Status |
|--------|-------|--------|
| Instruments invoked | | |
| Instruments succeeded | | |
| Total findings (deduplicated) | | |
| Cross-correlation findings | | |
| Composite score | | |
| Trajectory | | |

## Severity Summary

| Severity | Count |
|----------|-------|
| Critical | |
| Major | |
| Minor | |
| Observation | |
| OK | |

## Phase Results

### Phase 1 — Instrument Inventory
| Instrument | Present | Config Valid | Last Run |
|-----------|---------|-------------|----------|

### Phase 2 — Delegation
| Instrument | Action | Findings | Critical | Major | Minor |
|-----------|--------|----------|----------|-------|-------|

### Phase 3 — Overlap Resolution
| Overlap Area | Primary | Secondary | Action | Severity Agreed |
|-------------|---------|-----------|--------|-----------------|

### Phase 4 — Cross-Correlation
| Rule | Instruments | Severity | Description |
|------|------------|----------|-------------|

### Phase 5 — S14 Aggregation
| Section | Findings | Weakest Item | Rating |
|---------|----------|-------------|--------|

### Phase 6 — DR Synthesis (DR Mode only)
DR report written to: `output/DR{n}-{target}.md`

### Phase 7 — Delta Analysis
| Metric | Previous (QS{n-1}) | Current (QS{n}) | Delta |
|--------|-------------------|-----------------|-------|
| Composite score | | | |
| Critical | | | |
| Major | | | |
| Minor | | | |
| Regressions | — | | |
| Resolutions | — | | |

## Per-Section Breakdown

| DR Section | Instrument | Findings | Critical | Major | Minor | Obs | Rating |
|-----------|-----------|----------|----------|-------|-------|-----|--------|
| S1 Architecture | architecture-tomographe | | | | | | |
| S2 Documentation | documentation-tomographe | | | | | | |
| S3 Code Quality | code-tomographe | | | | | | |
| S4 Validation | test-tomographe | | | | | | |
| S5 Security | security-tomographe | | | | | | |
| S6 Configuration | compliance-tomographe | | | | | | |
| S7 Observability | observability-tomographe | | | | | | |
| S8 Data Management | data-tomographe | | | | | | |
| S9 Deployment | deployment-tomographe | | | | | | |
| S10 Performance | performance-tomographe | | | | | | |
| S11 UX | ux-tomographe | | | | | | |
| S12 Licensing | compliance-tomographe | | | | | | |
| S13 Maintainability | code-tomographe | | | | | | |
| K1 Enforcer | compliance-tomographe | | | | | | |
| K2 Glossary | documentation-tomographe | | | | | | |
| K3 Design-to-Impl | documentation-tomographe | | | | | | |
| K4 Cross-Doc | documentation-tomographe | | | | | | |
| AI/ML Quality | ai-ml-tomographe | | | | | | |
| **S14 Overall** | **Qualitoscope** | | | | | | |

## Action Register

| ID | Source | Section | Severity | Finding | Action | Priority | Status |
|----|--------|---------|----------|---------|--------|----------|--------|

## Appendix — Run Metadata

| Key | Value |
|-----|-------|
| Run ID | QS{n} |
| Date | {date} |
| Mode | {mode} |
| Trigger | {trigger} |
| Freshness window | {freshness_hours}h |
| Instruments invoked | {count} |
| Duration | {duration} |
| Previous run | QS{n-1} |
