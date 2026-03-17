# architecture-tomographe

**Architectural health scanner for the target project.** Audits module boundaries, dependency graphs, pattern conformance, and structural drift between code and documented architecture. Ensures the project's process architecture, service boundaries, and permission system remain intact as the codebase evolves.

**Covers DR Sections:** S1 (Architecture & Design)

---

## Quick Start

```bash
"Read instruments/architecture-tomographe/README.md and execute a full architecture scan."
"Read instruments/architecture-tomographe/README.md and execute Phase 4 (Violation Scan) only."
```

---

## Scan Phases

| Phase | Name | What It Does | Tools |
|-------|------|-------------|-------|
| **1** | Module Mapping | Enumerate crates, modules, public API surfaces | `cargo metadata`, grep, file listing |
| **2** | Dependency Analysis | Build mod graph, detect circular deps, layer violations | `cargo tree`, grep, LLM analysis |
| **3** | Pattern Detection | Identify dominant architecture patterns per crate | LLM analysis, grep |
| **4** | Violation Scan | Cross-layer imports, god modules, tight coupling | grep, LLM analysis |
| **5** | Drift Assessment | Compare code structure vs documented architecture | diff, LLM analysis |
| **6** | Evolution Readiness | Assess extensibility, seam availability, plugin points | LLM analysis |
| **7** | Report | Compile findings into AR{n} report | Template filling |

---

## Phase 1 — Module Mapping

**Goal:** Build a complete map of crates, modules, and their public API surfaces.

### Steps

```bash
# List all workspace crates
cargo metadata --format-version 1 2>/dev/null | jq -r '.workspace_members[]' | sort

# Enumerate modules per crate
for crate_dir in <service_dirs>; do
  echo "=== $crate_dir ==="
  find src/$crate_dir -name '*.rs' | sort
done

# Count public items per module
grep -rn 'pub fn \|pub struct \|pub enum \|pub trait \|pub type \|pub const ' \
  src/ --include='*.rs' | \
  sed 's|/[^/]*$||' | sort | uniq -c | sort -rn | head -20

# Identify module re-export hubs
grep -rn 'pub mod \|pub use ' src/lib.rs src/main.rs \
  --include='*.rs' 2>/dev/null
```

### Deliverables

- Module inventory table (crate, module, file count, pub item count)
- Dependency hub identification (modules with highest fan-in/fan-out)

---

## Phase 2 — Dependency Analysis

**Goal:** Detect circular dependencies, layer violations, and unhealthy coupling.

### Steps

```bash
# Crate-level dependency graph
cargo tree --workspace --depth 1 2>/dev/null

# Check for circular dependencies between workspace crates
cargo tree --workspace 2>/dev/null | grep -E '^\w+-\w+ .* \(\*\)' | head -10

# Module-level: find cross-layer imports
# Layers: api → service → db (allowed direction)
# Violations: db → service, db → api, service → api
grep -rn 'use crate::api' src/service/ src/db/ --include='*.rs'
grep -rn 'use crate::service' src/db/ --include='*.rs'

# Check service independence (services should not import other services' internals)
grep -rn 'use <crate_name>::\|use crate::<other_service>' <service>/src/ --include='*.rs' 2>/dev/null
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Circular dependency between crates | **Critical** |
| db → service or db → api import | **Major** |
| service → api import | **Major** |
| Service importing another service's internals | **Critical** |
| >10 direct dependencies on a single module | **Minor** |

---

## Phase 3 — Pattern Detection

**Goal:** Identify the dominant architectural patterns in each crate and verify consistency.

### Expected Patterns

| Crate | Expected Pattern | Key Indicators |
|-------|-----------------|----------------|
| `<primary_service>` | Service layer (api → service → db) | Thin API handlers, service trait, db module separation |
| `<access_control>` | Policy engine | Tier-based dispatch, config-driven rules, fail-closed |
| `<health_monitor>` | Health monitor | Periodic checks, alerting, independent restart logic |
| `common` | Shared library | Types, error definitions, no business logic |

### Steps

1. For each crate, enumerate the top-level module structure
2. Verify the expected layering (api → service → db) in the primary service
3. Check that components implement a consistent trait/interface
4. Verify access control config drives behavior (not hardcoded)
5. Confirm the health monitor has no business logic dependencies

### Severity Rules

| Finding | Severity |
|---------|----------|
| Crate deviates from expected pattern | **Major** |
| Mixed patterns within a single crate | **Minor** |
| Business logic in common crate | **Major** |
| Hardcoded behavior in access control (not config-driven) | **Major** |

---

## Phase 4 — Violation Scan

**Goal:** Find specific architectural violations.

### Steps

```bash
# God modules (files >500 lines with high fan-in)
find src/ -name '*.rs' -exec wc -l {} \; 2>/dev/null | sort -rn | head -20

# Cross-cutting concerns leaking (e.g., HTTP types in db layer)
grep -rn 'axum\|hyper\|StatusCode\|Json<' src/db/ --include='*.rs' 2>/dev/null
grep -rn 'rusqlite\|SqlitePool\|Connection' src/api/ --include='*.rs' 2>/dev/null

# Component isolation: components should not import other components directly
for component in src/component/*.rs; do
  name=$(basename "$component" .rs)
  [ "$name" = "mod" ] && continue
  others=$(grep -l "use crate::component::$name" src/component/*.rs 2>/dev/null | grep -v "$component" | grep -v "mod.rs")
  if [ -n "$others" ]; then
    echo "VIOLATION: $name imported by: $others"
  fi
done

# Direct SQL in component files (should use db/ layer)
grep -rn 'SELECT\|INSERT\|UPDATE\|DELETE\|CREATE TABLE' src/component/ --include='*.rs' 2>/dev/null

# Access control bypass attempts
grep -rn 'enforce\|tier\|permission' src/ --include='*.rs' | \
  grep -v 'access_client\|check_permission\|//\|test' | head -10
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| God module >800 lines with >5 dependents | **Major** |
| HTTP types in db layer | **Major** |
| SQL types in API layer | **Major** |
| Component importing another component directly | **Minor** |
| Raw SQL in component files (not db/ layer) | **Major** |
| Access control bypass | **Critical** |

---

## Phase 5 — Drift Assessment

**Goal:** Compare actual code structure against documented architecture.

### Steps

1. Read documented architecture from:
   - `CLAUDE.md` (Architecture section)
   - `docs/architecture.md` (if exists)
   - `.claude/decisions/` (ADRs)
2. Compare crate boundaries in code vs docs
3. Verify database separation matches schema documentation
4. Check access control assignments match permission/access control configuration
5. Verify component/module domain registration matches documented component list

### Drift Indicators

| Indicator | Severity |
|-----------|----------|
| Crate exists in code but not in docs | **Minor** |
| Documented component missing from code | **Minor** |
| Access control config disagrees with docs | **Major** |
| Database used that's not in the documented data model | **Critical** |
| Process boundary violated (e.g., one service directly calling another's internals) | **Critical** |

---

## Phase 6 — Evolution Readiness

**Goal:** Assess how easy it is to add new capabilities without breaking existing ones.

### Assessment Criteria

- [ ] New component can be added by creating a small set of files (component, db, api) + registering in mod.rs
- [ ] New access control domain can be added via config only (no code changes to the access control service)
- [ ] New database table can be added via migration without affecting existing tables
- [ ] Shared types in `common` crate are stable (low churn)
- [ ] API versioning strategy exists or is unnecessary at current stage
- [ ] Plugin/extension points are documented

### Scoring

| Score | Meaning |
|-------|---------|
| **Green** (>0.8) | New features require minimal structural changes |
| **Yellow** (0.6-0.8) | Some friction — registration files need updates, some coupling |
| **Red** (<0.6) | High friction — adding features requires changes across many modules |

---

## Phase 7 — Report

Compile all findings into `output/YYYY-MM-DD/AR{n}-architecture.md` using the report template.

### Report Contents

1. **Summary table** — key metrics at a glance
2. **Module map** — crate/module inventory
3. **Dependency graph** — critical paths and violations
4. **Pattern conformance** — per-crate assessment
5. **Violation register** — all findings with severity
6. **Drift log** — code-vs-docs discrepancies
7. **Evolution score** — readiness assessment
8. **Action register** — prioritized remediation items

---

## Configuration

See `config.yaml` for thresholds and scope.

---

## Run History

| Run | Date | Trigger | Report |
|-----|------|---------|--------|
| AR1 | _pending_ | Initial baseline | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
