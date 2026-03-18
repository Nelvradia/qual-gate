---
instrument: dependency-tomographe
run: DT{n}
date: {YYYY-MM-DD}
trigger: {manual | pre-release | scheduled | post-dependency-change}
verdict: {PASS | CONDITIONAL | FAIL}
---

# Dependency Report — DT{n}

**Date:** {YYYY-MM-DD} | **Run:** DT{n} | **Verdict:** {PASS | CONDITIONAL | FAIL}

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Ecosystems scanned | |
| Total direct dependencies | |
| Total transitive dependencies | |
| Unused direct dependencies | |
| Licence Critical findings | |
| Licence Major findings | |
| Health / maintenance findings | |
| Pinning / lockfile findings | |
| Transitive risk findings | |
| **Overall verdict** | |

---

## Phase 1 — Ecosystem Inventory

| Ecosystem | Manifest | Direct Deps | Dev-Only Deps | Lockfile Present |
|-----------|----------|------------|---------------|-----------------|
| | | | | |

---

## Phase 2 — Usage Analysis

### Declared but unused

| Package | Ecosystem | Declared as | Finding |
|---------|-----------|------------|---------|
| | | | |

### Imported but undeclared

| Import | Ecosystem | Source file | Finding |
|--------|-----------|------------|---------|
| | | | |

---

## Phase 3 — Licence Risk Register

| Package | Ecosystem | Licence | Tier | Obligation | Severity | Action |
|---------|-----------|---------|------|------------|----------|--------|
| | | | | | | |

### Copyleft propagation analysis

{Free text — for each non-permissive dep, describe the link type, whether it contaminates the binary, and the required action or documented strategy.}

### Attribution file status

- Attribution file present: {Yes / No}
- All permissive deps attributed: {Yes / No / Partial}
- Missing from attribution: {list}

---

## Phase 4 — Health Register

| Package | Ecosystem | Finding | Last Release | Severity | Action |
|---------|-----------|---------|-------------|----------|--------|
| | | | | | |

---

## Phase 5 — Pinning Assessment

| Manifest | Lockfile Present | Wildcard Constraints | Semver Lag | Severity |
|----------|-----------------|---------------------|------------|----------|
| | | | | |

---

## Phase 6 — Transitive Surface

| Ecosystem | Total Transitive Deps | Diamond Conflicts | Vendored Dirs | Severity |
|-----------|-----------------------|-------------------|---------------|----------|
| | | | | |

### Diamond conflicts

| Package | Versions in use | Affected ecosystems | Severity |
|---------|----------------|---------------------|----------|
| | | | |

### Vendored code assessment

| Directory | Attribution present | LICENSE file present | Update strategy | Severity |
|-----------|--------------------|--------------------|-----------------|----------|
| | | | | |

---

## Overall Findings Summary

| Phase | OK | Observation | Minor | Major | Critical |
|-------|----|------------|-------|-------|----------|
| 2 — Usage Analysis | | | | | |
| 3 — Licence Risk | | | | | |
| 4 — Dependency Health | | | | | |
| 5 — Version & Pinning | | | | | |
| 6 — Transitive Risk | | | | | |
| **Total** | | | | | |

---

## Action Register

| ID | Phase | Severity | Package / Finding | Required Action | Priority | Status |
|----|-------|----------|-------------------|----------------|----------|--------|
| DT{n}-01 | | | | | P1 | Open |
| DT{n}-02 | | | | | P2 | Open |
