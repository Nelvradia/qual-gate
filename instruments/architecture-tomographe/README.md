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
| **1** | Module Mapping | Enumerate modules, packages, crates, and public API surfaces | manifest tools, file listing, LLM analysis |
| **2** | Dependency Analysis | Build mod graph, detect circular deps, layer violations | dependency tools, LLM analysis |
| **3** | Pattern Detection | Identify dominant architecture patterns per module | LLM analysis |
| **4** | Violation Scan | Cross-layer imports, god modules, tight coupling | file analysis, LLM analysis |
| **5** | Drift Assessment | Compare code structure vs documented architecture | LLM analysis |
| **6** | Evolution Readiness | Assess extensibility, seam availability, plugin points | LLM analysis |
| **7** | Report | Compile findings into AR{n} report | Template filling |

---

## Phase 1 — Module Mapping

**Goal:** Build a complete map of modules, packages, or crates and their public API surfaces.

### LLM steps

1. Read the project root and all subdirectories. Identify the top-level modules, packages, crates, or namespaces by reading the relevant manifest and source files. In Rust these are crates (`Cargo.toml`); in Python, top-level packages (`__init__.py`); in Go, packages (`go.mod` + directory structure); in Java/Kotlin, packages (`pom.xml` or `build.gradle`); in Node, the `package.json` name and `exports` field.
2. For each module/package, count public API surface: exported functions, classes, types, and constants.
3. Identify which modules act as re-export hubs (modules that import many others and re-export them) — these are dependency hubs regardless of language.
4. Build a module inventory table.

### Accelerator tools (optional)

```bash
# Rust — list workspace crates and public items
cargo metadata --format-version 1 2>/dev/null | jq -r '.workspace_members[]' | sort
cargo tree --workspace --depth 1 2>/dev/null

# Go — list all packages
go list ./...

# Python — list top-level packages
python -c "import pkgutil; [print(m.name) for m in pkgutil.iter_modules()]"
```

### Deliverables

- Module inventory table (module/package/crate, file count, pub item count)
- Dependency hub identification (modules with highest fan-in/fan-out)

---

## Phase 2 — Dependency Analysis

**Goal:** Detect circular dependencies, layer violations, and unhealthy coupling.

### LLM steps

1. For each module identified in Phase 1, read its import/use statements.
2. Build a directed dependency graph: which module imports which.
3. Check for circular dependencies: module A imports B imports A.
4. Check for layer violations using the `layers` configuration in config.yaml — the layer rules describe logical layers; apply them to whatever modules are found.
5. Check that independent components (as declared in config.yaml `layers.*.independent_of`) do not import each other.

Note: this phase analyses _module-level_ import direction, not package-level dependencies. Package-level dependency analysis is handled by the dependency-tomographe.

### Accelerator tools (optional)

```bash
# Rust — workspace dependency graph and circular dep detection
cargo tree --workspace 2>/dev/null
cargo tree --workspace 2>/dev/null | grep -E '^\w+-\w+ .* \(\*\)' | head -10

# Node/TypeScript — circular dependency detection
madge --circular src/

# Go — module dependency graph
go mod graph
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Circular dependency between modules | **Critical** |
| Lower layer importing from a higher layer | **Major** |
| Component importing another component's internals | **Critical** |
| >10 direct dependencies on a single module | **Minor** |

---

## Phase 3 — Pattern Detection

**Goal:** Identify the dominant architectural patterns in each module and verify consistency.

### LLM steps

1. Read the module structure from Phase 1.
2. For each top-level module, identify the dominant architectural pattern based on its structure: layered (api → service → db), hexagonal (ports + adapters), pipeline, event-driven, monolith, etc.
3. Check whether the pattern is consistent across the codebase or whether modules use conflicting patterns.
4. Verify that the observed patterns match the `Expected Patterns` section in the configuration (if defined).

Expected patterns are defined in config.yaml per module.

### Severity Rules

| Finding | Severity |
|---------|----------|
| Module deviates from expected pattern | **Major** |
| Mixed patterns within a single module | **Minor** |
| Business logic in shared/common module | **Major** |
| Hardcoded behavior in access control (not config-driven) | **Major** |

---

## Phase 4 — Violation Scan

**Goal:** Find specific architectural violations.

### LLM steps

1. Read all source files. For each, note its module/layer assignment.
2. Check for god modules: files that are very long (check against `god_module_lines` threshold) AND imported by many other modules (check against `god_module_dependents` threshold).
3. Check for cross-layer type leakage: framework/transport types appearing in persistence layers, or persistence types appearing in API layers. The specific types differ by language and framework but the principle is universal.
4. Check for component isolation: if two components are declared independent, verify neither imports the other's internal modules.
5. Check for raw data access in the wrong layer (e.g. SQL strings or ORM calls outside the designated persistence module).

### Accelerator tools (optional)

```bash
# All ecosystems — find large files (adjust extension as needed)
find src/ -name '*.rs' -exec wc -l {} \; 2>/dev/null | sort -rn | head -20
find src/ -name '*.py' -exec wc -l {} \; 2>/dev/null | sort -rn | head -20
find src/ -name '*.go' -exec wc -l {} \; 2>/dev/null | sort -rn | head -20

# Rust — transport types leaking into persistence layer
grep -rn 'axum\|hyper\|StatusCode\|Json<' src/db/ --include='*.rs' 2>/dev/null
grep -rn 'rusqlite\|SqlitePool\|Connection' src/api/ --include='*.rs' 2>/dev/null

# Rust — raw SQL outside db layer
grep -rn 'SELECT\|INSERT\|UPDATE\|DELETE\|CREATE TABLE' src/component/ --include='*.rs' 2>/dev/null
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| God module >800 lines with >5 dependents | **Major** |
| Transport/framework types in persistence layer | **Major** |
| Persistence types in API layer | **Major** |
| Component importing another component directly | **Minor** |
| Raw data access outside the designated persistence module | **Major** |
| Access control bypass | **Critical** |

---

## Phase 5 — Drift Assessment

**Goal:** Compare actual code structure against documented architecture.

### LLM steps

Read the files listed in `doc_sources` in config.yaml (CLAUDE.md, ADRs, architecture docs) and compare what is described there against what is found in the code. Identify any discrepancy between documented and actual module boundaries, component ownership, and service separation.

### Drift Indicators

| Indicator | Severity |
|-----------|----------|
| Module exists in code but not in docs | **Minor** |
| Documented component missing from code | **Minor** |
| Access control config disagrees with docs | **Major** |
| Database used that's not in the documented data model | **Critical** |
| Process boundary violated (e.g., one service directly calling another's internals) | **Critical** |

---

## Phase 6 — Evolution Readiness

**Goal:** Assess how easy it is to add new capabilities without breaking existing ones.

### Assessment Criteria

- [ ] A new module can be added by creating files in the appropriate directory and registering it in the module manifest (`mod.rs`, `__init__.py`, `index.ts`, etc.)
- [ ] New configuration-driven behaviour can be added via config only (no hardcoded changes)
- [ ] New persistence schema can be added via migration without affecting existing schema
- [ ] Shared types in the common/core module are stable (low churn)
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

Compile all findings into `output/YYYY-MM-DD_{project_name}/AR{n}-architecture.md` (see `qualitoscope/config.yaml` for `project_name`) using the report template.

### Report Contents

1. **Summary table** — key metrics at a glance
2. **Module map** — module/package inventory
3. **Dependency graph** — critical paths and violations
4. **Pattern conformance** — per-module assessment
5. **Violation register** — all findings with severity
6. **Drift log** — code-vs-docs discrepancies
7. **Evolution score** — readiness assessment
8. **Action register** — prioritized remediation items

---

## Configuration

This instrument reads project-specific paths from `project-profile.yaml` in the target project root. If a profile field is absent, the default from the profile schema applies. Instrument-specific thresholds remain in this instrument's `config.yaml`.

---

## Run History

| Run | Date | Trigger | Report |
|-----|------|---------|--------|
| AR1 | _pending_ | Initial baseline | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
