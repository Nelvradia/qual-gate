---
title: "qual-gate — Roadmap to v1.0.0"
status: current
last-updated: 2026-03-19
---

# qual-gate — Roadmap to v1.0.0

> From project-specific methodology repo to universal quality gate.

**Goal:** Make qual-gate work reliably on any software project — any language, any stack,
any architecture — without manual customisation beyond a single project profile.

**Scope:** This roadmap covers only Horizon 1 (v0.3.0 → v1.0.0). See `VISION.md` for
Horizons 2–4.

---

## Overview

Six workstreams, roughly ordered by dependency:

```
WS1: Project Profile Schema ──────────────┐
                                           ├─→ WS4: Orchestrator Completeness
WS2: Auto-Discovery (Phase 0) ────────────┘         │
                                                     │
WS3: Generalise Instruments ─────────────────────────┤
                                                     │
WS5: Remediation Library ───────────────────────────┘
                                                     │
WS6: Documentation & Onboarding ─────────────────────┘
```

WS1 unblocks WS2, WS3, and WS4. WS5 and WS6 can start in parallel at any time.

---

## WS1 — Project Profile Schema

**Why:** 12+ config files contain hardcoded paths (`config/access-control.yaml`,
`docs/four-pillars/brainstorm/`, `infra/scripts/lint_glossary.py`). Users must manually
edit every config for their project. A single `project-profile.yaml` replaces all of it.

### Issues

#### WS1-01: Define project-profile.yaml specification

Design the schema that describes a target project. Must cover:

- **Identity:** project name, version, repo URL.
- **Stack:** languages, build systems, CI platform, package managers.
- **Architecture:** boundary marker (crate/package/module/namespace), layer names and
  paths, entry points.
- **Paths:** source dirs, test dirs, docs dir, config dir. All currently scattered across
  13 instrument configs.
- **Conventions:** permission/access control config (optional), glossary (optional),
  schema map (optional), metrics registry (optional).
- **Platforms:** target platforms (web, mobile, desktop) and their key storage mechanisms.
- **Toggles:** which optional domains apply (permission system, AI/ML components,
  GDPR scope, AI Act scope).

Provide sensible defaults so that a minimal profile works:

```yaml
# Minimal viable profile
name: my-project
stack:
  languages: [python]
```

Everything else auto-discovered or defaulted.

**Deliverable:** `project-profile.schema.yaml` (JSON Schema or equivalent) +
`project-profile.example.yaml` with full annotations.

**Estimate:** 4–6h

---

#### WS1-02: Centralise path references from instrument configs

Audit every `config.yaml` across all 13 instruments. Extract path references into the
project profile. Instrument configs retain only instrument-specific thresholds.

**Files affected:**

| Instrument | Hardcoded paths to extract |
|---|---|
| documentation-tomographe | `docs/four-pillars/brainstorm/`, `docs/four-pillars/gaps/`, `docs/operations/`, `.claude/decisions/`, `infra/scripts/lint_glossary.py`, `docs/schema-map.md`, `docs/metrics-registry.md`, `config/access-control.yaml` |
| compliance-tomographe | `config/access-control.yaml`, `config/component-permission-manifest.yaml`, `tests/access-control/`, `config/`, `docs/business_case/` |
| security-tomographe | `config/access-control.yaml` (+ platform-specific key storage patterns) |
| architecture-tomographe | `CLAUDE.md`, `docs/four-pillars/`, `.claude/decisions/` |
| All instruments | `source_dirs: []`, `test_dirs: []` (currently empty, must come from profile) |

**Approach:** Each instrument's `config.yaml` gets a new top-level key:

```yaml
# Instrument configs become:
thresholds:
  # ... instrument-specific thresholds (unchanged)
# All path references removed — read from project-profile.yaml at scan time
```

Instruments reference profile values via a documented convention (e.g. `${profile.paths.docs_dir}`
or the AI reads both files and resolves references).

**Estimate:** 6–8h

---

#### WS1-03: Add profile validation to qualitoscope Phase 1

Phase 1 currently verifies instrument presence. Extend it to:

1. Check for `project-profile.yaml` in the target project root.
2. Validate against the schema (WS1-01).
3. Report missing required fields as `Critical` findings (scan cannot proceed without them).
4. Report missing optional fields as `Observation` (scan proceeds with defaults).

**Estimate:** 2–3h

---

## WS2 — Auto-Discovery (Phase 0)

**Why:** Filling in `project-profile.yaml` manually is a barrier to adoption. Phase 0
detects the target project's stack and layout, then generates a draft profile for the
user to confirm.

### Issues

#### WS2-01: Design Phase 0 auto-discovery methodology

Write the Phase 0 methodology document (`qualitoscope/methods/00-auto-discovery.md`).

Detection heuristics (LLM steps + accelerator commands):

| Signal | Detection method |
|---|---|
| Languages | File extensions (`.rs`, `.py`, `.ts`, `.go`, `.kt`, `.java`, `.cpp`) |
| Build systems | Presence of `Cargo.toml`, `pyproject.toml`, `package.json`, `go.mod`, `build.gradle`, `CMakeLists.txt`, `Makefile` |
| CI platform | `.gitlab-ci.yml`, `.github/workflows/`, `azure-pipelines.yml`, `Jenkinsfile` |
| Package managers | `Cargo.lock`, `poetry.lock`, `pnpm-lock.yaml`, `yarn.lock`, `go.sum` |
| Source dirs | Convention-based (`src/`, `lib/`, `app/`, `cmd/`) + build file references |
| Test dirs | Convention-based (`tests/`, `test/`, `spec/`, `__tests__/`) + build file references |
| Docs dir | `docs/`, `doc/`, `documentation/` |
| Architecture | Workspace members (Cargo), monorepo structure, entry points from build files |
| Platforms | Android manifests, `ios/`, Electron/Tauri configs, `Dockerfile` |

Phase 0 output: a draft `project-profile.yaml` written to the target project root,
clearly marked as auto-generated, with comments prompting the user to verify.

**Estimate:** 4–6h

---

#### WS2-02: Integrate Phase 0 into qualitoscope orchestration

Update `qualitoscope/README.md` to insert Phase 0 before Phase 1. Phase 0 runs
automatically if no `project-profile.yaml` exists. If one already exists, Phase 0
is skipped.

Update the phase numbering (Phase 0–8 instead of Phase 1–8) and delegation logic.

**Estimate:** 2–3h

---

## WS3 — Generalise Instruments

**Why:** Several instruments contain logic specific to the original target project
(skill/enforcer architecture, glossary terms, access control assumptions). These must
be parameterised to work on any project.

### Issues

#### WS3-01: Generalise cross-correlation rules

Two of eight rules use project-specific terminology:

| Rule | Current | Generalised |
|---|---|---|
| XC-02 | `skill_without_enforcer` — "Skill without enforcer entry" | `component_without_auth_entry` — "Component/service without access control entry" |
| XC-05 | `soul_change_without_eval` — "AI configuration change without eval" | `ai_config_change_without_eval` — "AI configuration change without evaluation" |

Update in:
- `qualitoscope/config.yaml` (lines 73–74, 85–86)
- `qualitoscope/methods/04-cross-correlation.md` (rule table + severity table)

Make both rules conditional: XC-02 only fires if `profile.conventions.permission_config`
is set. XC-05 only fires if `profile.toggles.ai_ml_components` is true.

**Estimate:** 2h

---

#### WS3-02: Generalise architecture checklist

`instruments/architecture-tomographe/checklists/pattern-fitness.md` contains 10 items,
5 of which are project-specific:

```
- [ ] Service follows api → skill → db layer boundary          # project-specific
- [ ] Skills do not import other skills directly                # project-specific
- [ ] Permission service operates independently                 # project-specific
- [ ] Monitoring service operates independently                 # project-specific
- [ ] Permission service behavior is config-driven              # project-specific
```

**Approach:** Split into two sections:

1. **Universal checks** (always apply):
   - No circular dependencies between modules/crates/packages
   - Raw data access confined to data layer (not in API or business logic)
   - HTTP/transport types confined to API layer
   - Common/shared module contains only shared types (no business logic)
   - No auth/permission bypass paths in service code

2. **Profile-driven checks** (generated from `project-profile.yaml`):
   - Layer boundary enforcement (layers come from profile)
   - Service independence constraints (services come from profile)
   - Config-driven behaviour checks (only if permission system enabled)

**Estimate:** 3–4h

---

#### WS3-03: Make glossary linter configurable

`instruments/glossary-linter.sh` has three hardcoded elements:

1. **Bare terms** (line 41–48): `domain`, `context`, `trigger`, `session`, `template`,
   `thread` — specific to the original project's vocabulary.
2. **Allowlist path** (line 31): `quality/instruments/glossary-allowlist.txt` — should
   be configurable.
3. **Language filter** (line 70): `--type rust` — only scans Rust files.
4. **Doc reference** (line 111): `docs/four-pillars/gaps/G01-glossary.md` — project-specific.

**Changes:**

- Accept `--terms-file <path>` to load bare terms from a YAML/text file instead of
  hardcoding them.
- Accept `--allowlist <path>` to override the default allowlist location.
- Accept `--type <lang>` to scan languages other than Rust (default: all languages,
  or inferred from profile).
- Accept `--glossary-doc <path>` to customise the remediation reference.
- Ship a `glossary-terms.example.yaml` showing the format.
- Move current hardcoded terms to `glossary-terms.example.yaml` as a reference.

**Estimate:** 3–4h

---

#### WS3-04: Make access control scanning conditional

Multiple instruments assume a permission/access control system exists:

- compliance-tomographe Phase 3 (AC1 checklist)
- security-tomographe Phase 7 (Access Control)
- architecture-tomographe pattern fitness (permission service checks)
- XC-02 cross-correlation rule

**Change:** All access-control-related phases and checks become conditional on
`profile.toggles.permission_system: true`. When false, these phases are skipped
with an `Observation: "No permission system configured — skipping AC checks"`.

**Estimate:** 3–4h

---

#### WS3-05: Generalise platform-specific security checks

security-tomographe Phase 4 checks for Android Keystore, iOS Secure Enclave, desktop
keyring, and web TLS patterns. These are already somewhat generic but reference
specific classes (`AndroidKeyStore`, `BiometricPrompt`, `KeyStore`).

**Change:** Organise checks by platform and only run checks for platforms declared in
`profile.platforms.targets`. Add platform detection heuristics for projects that don't
declare platforms explicitly.

**Estimate:** 2–3h

---

## WS4 — Orchestrator Completeness

**Why:** The dependency-tomographe exists and is fully implemented but is not registered
in the orchestrator. The orchestrator also needs updates to consume the project profile.

### Issues

#### WS4-01: Wire dependency-tomographe as I13

Add to `qualitoscope/config.yaml`:

```yaml
  - id: I13
    name: dependency-tomographe
    sections: [S12, S5]
```

Update:
- `qualitoscope/README.md` Phase 1 instrument inventory (12 → 13)
- `qualitoscope/README.md` Phase 2 delegation (include I13)
- `qualitoscope/methods/03-overlap-resolution.md` overlap ownership table:
  - dependency-tomographe owns: unused deps, SBOM completeness, dep health/abandonment
  - security-tomographe owns: CVE severity (shared with dependency supply chain findings)
  - compliance-tomographe owns: licence classification (shared with dependency licence matrix)
- Phase 5 aggregation weights (add I13 weight)
- DR section mapping: I13 → S12 (Licensing/Dependencies) + S5 (Supply Chain subset)

**Estimate:** 3–4h

---

#### WS4-02: Update orchestrator to consume project profile

Modify qualitoscope Phase 1 to:

1. Load and validate `project-profile.yaml` (WS1-03).
2. Resolve profile values into each instrument's config at delegation time (Phase 2).
3. Pass `project_name` from profile to output folder naming (replaces the manual
   `project_name: ""` in `qualitoscope/config.yaml`).

**Estimate:** 3–4h

---

#### WS4-03: Review and update DR section mapping

With I13 added and instruments generalised, review the full DR section mapping:

| Section | Instruments | Notes |
|---|---|---|
| S1 Architecture | I01 | Unchanged |
| S2 Documentation | I04 | Unchanged |
| S3 Code Quality | I03 | Unchanged |
| S4 Testing | I02 | Unchanged |
| S5 Security | I09 + I13 (supply chain subset) | I13 now contributes |
| S6 Compliance | I05 | Unchanged |
| S7 Observability | I08 | Unchanged |
| S8 Data | I06 | Unchanged |
| S9 Deployment | I07 | Unchanged |
| S10 Performance | I10 | Unchanged |
| S11 UX | I11 | Unchanged |
| S12 Dependencies | I05 (licence) + I13 (SBOM, health) | I13 now contributes |
| S13 Technical Debt | I03 | Unchanged |
| AI-ML | I12 | Non-DR dimension — decide: add as S14 or keep separate |
| K1–K4 | I05, I04 | Unchanged |

**Decision needed:** Should AI-ML become S14 in the DR template, or remain a
supplementary dimension outside the DR structure?

**Estimate:** 2–3h

---

## WS5 — Remediation Library (`fixes/`)

**Why:** 12 of 13 instruments have empty `fixes/` directories. A finding without
remediation guidance is noise. This is what makes qual-gate actionable.

### Issues

#### WS5-01: Define fixes/ content standard

Each instrument's `fixes/` directory should contain:

```
fixes/
├── README.md                     # Index of all fix guides
├── {finding-category}.md         # One file per category of finding
└── ...
```

Each fix guide follows a standard structure:

```markdown
# Fix: {Finding Category}

## What this means
One-paragraph explanation of why this finding matters.

## How to fix

### Python
{language-specific remediation steps + code examples}

### Rust
{language-specific remediation steps + code examples}

### TypeScript
{language-specific remediation steps + code examples}

### General
{language-agnostic guidance for other stacks}

## Prevention
How to prevent this finding from recurring (tooling, CI checks, conventions).
```

**Estimate:** 2–3h

---

#### WS5-02: Populate security-tomographe fixes

Priority: highest. Security findings are the most urgent to remediate.

Categories:
- Hardcoded secrets / credentials in source
- Known CVE in dependency (links to dependency-tomographe)
- Missing TLS / insecure transport
- Container running as root
- Missing input validation / injection risk
- Insecure key storage per platform
- Missing rate limiting / brute force protection

**Estimate:** 6–8h

---

#### WS5-03: Populate code-tomographe fixes

Priority: high. Most frequently raised findings.

Categories:
- Linter / formatter violations (per-language tooling setup)
- High cyclomatic complexity (refactoring patterns)
- Dead code removal
- Code duplication (extraction patterns)
- Technical debt classification and prioritisation

**Estimate:** 4–6h

---

#### WS5-04: Populate compliance-tomographe fixes

Priority: high. Compliance findings often block releases.

Categories:
- Copyleft licence contamination
- Missing attribution / NOTICE file
- Hardcoded addresses / missing config externalisation
- GDPR: missing privacy tier classification
- GDPR: missing data export / deletion endpoints
- AI Act: missing risk classification
- Access control coverage gaps

**Estimate:** 4–6h

---

#### WS5-05: Populate test-tomographe fixes

Priority: medium.

Categories:
- Missing unit test coverage for public functions
- Missing integration tests for component boundaries
- Flaky test diagnosis and quarantine
- Missing CI gating (tests not blocking merge)
- Test quality issues (no assertions, brittle mocks)

**Estimate:** 3–4h

---

#### WS5-06: Populate remaining instrument fixes

Priority: lower, can be done incrementally.

Instruments: architecture, documentation, data, deployment, observability, performance,
UX, AI/ML.

**Estimate:** 2–3h per instrument, 16–24h total. Can be parallelised.

---

## WS6 — Documentation & Onboarding

**Why:** qual-gate currently has no getting-started guide. A new user cloning the repo
has to read the qualitoscope README and reverse-engineer the workflow. For v1.0, the
onboarding path must be obvious.

### Issues

#### WS6-01: Getting Started guide

A `docs/getting-started.md` (or section in README) covering:

1. Clone qual-gate
2. Point it at your project
3. Run auto-discovery (Phase 0) → generates `project-profile.yaml`
4. Review and confirm the profile
5. Run a single instrument scan
6. Run a full qualitoscope scan
7. Read the output report

Include a worked example with a real open-source project.

**Estimate:** 4–6h

---

#### WS6-02: Project Profile reference

Full documentation of every field in `project-profile.yaml`:

- What it controls
- Default value
- Which instruments use it
- Example values for common stacks (Python/Django, Rust/Axum, TypeScript/React,
  Go/gRPC, Java/Spring, multi-language monorepo)

**Estimate:** 3–4h

---

#### WS6-03: Instrument authoring guide

For contributors and power users. Covers:

- Instrument directory structure and required files
- How to write LLM steps vs. accelerator commands
- Severity scale and when to use each level
- Config schema conventions
- How to wire a new instrument into the orchestrator
- Testing your instrument against a sample project

This is a stepping stone toward the formal instrument specification in Horizon 2.

**Estimate:** 4–6h

---

#### WS6-04: Update README for v1.0

The root `README.md` needs to reflect:

- 13 instruments (currently shows 12 in some places)
- Project profile workflow
- Auto-discovery
- Link to getting-started guide
- Updated quick-start commands

**Estimate:** 2–3h

---

#### WS6-05: Add CHANGELOG

Start a `CHANGELOG.md` following Keep a Changelog format. Backfill entries for
v0.1.0 (initial release), v0.2.0, v0.3.0 from git history. All v1.0 work gets
logged as it lands.

**Estimate:** 2h

---

## Phasing

### Phase A — Foundation (WS1 + WS4-01)

**What:** Define the project profile schema, centralise path references, wire I13.
Everything else depends on this.

| Issue | Estimate | Dependencies |
|---|---|---|
| WS1-01: Profile schema | 4–6h | None |
| WS1-02: Centralise paths | 6–8h | WS1-01 |
| WS1-03: Profile validation | 2–3h | WS1-01 |
| WS4-01: Wire I13 | 3–4h | None |

**Total:** 15–21h
**Milestone:** qual-gate has a profile schema, instruments reference it, and all
13 instruments are registered.

---

### Phase B — Generalisation (WS2 + WS3 + WS4-02/03)

**What:** Auto-discovery, instrument generalisation, orchestrator profile consumption.
Can start WS3 items in parallel.

| Issue | Estimate | Dependencies |
|---|---|---|
| WS2-01: Phase 0 methodology | 4–6h | WS1-01 |
| WS2-02: Integrate Phase 0 | 2–3h | WS2-01 |
| WS3-01: Generalise XC rules | 2h | WS1-01 |
| WS3-02: Generalise architecture checklist | 3–4h | WS1-01 |
| WS3-03: Configurable glossary linter | 3–4h | WS1-01 |
| WS3-04: Conditional AC scanning | 3–4h | WS1-01 |
| WS3-05: Platform-specific security | 2–3h | WS1-01 |
| WS4-02: Orchestrator profile consumption | 3–4h | WS1-02 |
| WS4-03: DR section mapping review | 2–3h | WS4-01 |

**Total:** 24–35h
**Milestone:** qual-gate runs on any project with auto-discovery. No project-specific
logic remains.

---

### Phase C — Remediation & Docs (WS5 + WS6)

**What:** Populate fixes, write documentation. Can start in parallel with Phase B.

| Issue | Estimate | Dependencies |
|---|---|---|
| WS5-01: Fixes content standard | 2–3h | None |
| WS5-02: Security fixes | 6–8h | WS5-01 |
| WS5-03: Code fixes | 4–6h | WS5-01 |
| WS5-04: Compliance fixes | 4–6h | WS5-01 |
| WS5-05: Test fixes | 3–4h | WS5-01 |
| WS5-06: Remaining fixes | 16–24h | WS5-01 |
| WS6-01: Getting Started | 4–6h | WS1-01, WS2-01 |
| WS6-02: Profile reference | 3–4h | WS1-01 |
| WS6-03: Instrument authoring guide | 4–6h | WS3-02 |
| WS6-04: Update README | 2–3h | WS4-01 |
| WS6-05: CHANGELOG | 2h | None |

**Total:** 50–74h
**Milestone:** Every finding has remediation guidance. New users can onboard without
reading source. qual-gate is ready for v1.0.0 release.

---

## Summary

| Phase | Workstreams | Effort | Unlocks |
|---|---|---|---|
| A — Foundation | WS1, WS4-01 | 15–21h | Profile schema, all 13 instruments registered |
| B — Generalisation | WS2, WS3, WS4-02/03 | 24–35h | Any-project scanning, auto-discovery |
| C — Remediation & Docs | WS5, WS6 | 50–74h | Actionable findings, onboarding path |
| **Total** | | **89–130h** | **v1.0.0 release** |

Phase C is the largest block but is highly parallelisable — each instrument's fixes
are independent. The critical path runs through Phase A → Phase B → WS6-01 (Getting
Started guide, which needs both the profile and auto-discovery to be done).

---

## Version Milestones

| Version | What ships | Status |
|---|---|---|
| v0.3.0 | Initial open-source release — 13 instruments, orchestrator | Shipped |
| v0.4.0 | Project profile schema + path centralisation (Phase A, WS1) | Shipped |
| v0.5.0 | Auto-discovery, instrument generalisation, orchestrator completeness (Phase B, WS2 + WS3 + WS4) | Shipped |
| v0.6.0 | Remediation library + documentation + onboarding (Phase C, WS5 + WS6) | In progress |
| v1.0.0 | Release — all workstreams complete, tested against 3+ diverse projects | Planned |

---

## Open Questions (Resolved)

1. ~~**AI-ML as S14?**~~ **Resolved: S14.** I12 maps to DR section S14, conditional on
   `toggles.ai_ml_components`. When false, S14 is omitted from DR reports. The "Overall
   Summary" previously occupying S14 is now an unnumbered aggregation produced by Phase 5.

2. ~~**Glossary linter scope.**~~ **Resolved: absorbed into documentation-tomographe.**
   Script moved to `instruments/documentation-tomographe/accelerators/glossary-linter.sh`.
   Profile field `glossary_script` deprecated but retained for backward compatibility with
   custom glossary scripts.

3. ~~**Profile inheritance.**~~ **Deferred to Horizon 2.** Current schema is flat. An
   `extends:` field will be designed when multi-project demand materialises. Documented in
   VISION.md Horizon 2 scope.

4. ~~**Validation target for v1.0.**~~ **Selected:** OpenClaw (TypeScript/Python, AI agent),
   Boost (C++, scoped to single library), qual-gate (self-scan, methodology repo), + one
   additional TBD. Validation runs are separate sessions producing scan reports.
