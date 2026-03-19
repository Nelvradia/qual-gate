---
title: "qual-gate — Roadmap to v2.0.0"
status: current
last-updated: 2026-03-19
---

# qual-gate — Roadmap to v2.0.0

> From universal quality gate to extensible platform.

**Goal:** Transform qual-gate from a static methodology repository into an extensible
platform where instruments are discoverable, composable, and community-contributed — while
adding a programmatic execution layer that enables CI integration and automation.

**Scope:** This roadmap covers Horizon 2 (v1.0 → v2.0). See `VISION.md` for Horizons 3–4.
The v1.0 roadmap is preserved in `ROADMAP.md` for reference.

---

## Where We Are (v1.0.0)

qual-gate v1.0.0 shipped 2026-03-19. It provides:

- 13 domain scanning instruments covering architecture, code, testing, security,
  compliance, data, deployment, documentation, observability, performance, UX,
  AI/ML, and dependencies
- Qualitoscope orchestrator with 9-phase pipeline (Phase 0–8)
- Project profile schema with auto-discovery
- Remediation library (68 fix guides)
- Validated against 3 diverse projects: Boost.JSON (C++), OpenClaw (TypeScript/Node),
  qual-gate (self-scan)

### What v1.0 Proved

1. **The methodology-as-program model works.** An AI reading structured markdown can
   execute a quality scan on any codebase, any language. No compilation, no plugins,
   no language-specific tooling required.
2. **Accelerators are essential for precision.** LLM-only scans are universal but
   slow and approximate. Ecosystem-specific commands (cargo clippy, npm audit, cppcheck)
   dramatically improve speed and accuracy.
3. **Every new ecosystem requires manual work.** Adding C++ and TypeScript parity in
   Phase E required touching 8 files across 4 instruments. This doesn't scale.
4. **No programmatic interface limits adoption.** Scanning is fully manual — a user
   must open an AI assistant, paste the right prompt, and manage output files. No CI
   integration, no automation, no machine-readable output.

### Current Limitations (What v2.0 Fixes)

| Limitation | Impact | v2.0 Solution |
|------------|--------|---------------|
| Adding an instrument is a manual process | Community can't contribute | Instrument specification + scaffold command |
| No way to select instrument subsets | Always full scan or manual phase selection | Composable scan profiles |
| Accelerators scattered across README prose | Hard to maintain, inconsistent coverage | Language packs (bundled per ecosystem) |
| Flat profile schema, no inheritance | Multi-project orgs repeat config | Profile inheritance (`extends:`) |
| No CLI or programmatic API | Can't integrate with CI, can't automate | CLI wrapper (bridges to Horizon 3) |
| Implicitly coupled to Claude Code | Limits adoption to one AI provider | Provider-agnostic methodology spec |

---

## Strategic Decisions (Resolved)

All strategic decisions resolved 2026-03-19. Full rationale in
`.claude/decisions/002-v2-strategic-decisions.md`.

| # | Decision | Resolution |
|---|----------|------------|
| **SD-01** | Packaging model | **CLI wrapper.** Python CLI orchestrates scanning, delegates to Claude Code. Methodology markdown stays the source of truth. |
| **SD-02** | AI provider strategy | **Claude-specific for v2.0.** Tight integration with Claude Code (sub-agents, tool use, MCP). Provider-agnostic abstraction is out of scope — can be revisited in Horizon 3. |
| **SD-03** | Community model | **Two-tier.** Core instruments (13, maintainer-reviewed) + community instruments (spec-validated, labelled). Community instruments must pass `validate-instrument`. |
| **SD-04** | Target audience | **Engineering teams.** CI integration, scan profiles, multi-repo config. Enterprise (audit trails, SSO) deferred to Horizon 3+. |

**CLI deliverable:** `qual-gate` CLI (Python 3.13+) with subcommands:
```
qual-gate scan --profile=full --target=./my-project
qual-gate scan --instruments=security,compliance
qual-gate new-instrument <name>
qual-gate list [--installed]
qual-gate validate-profile ./project-profile.yaml
```

---

## Workstreams

Eight workstreams, ordered by dependency:

```
SD (Strategic Decisions) ──────────────────────────────────┐
                                                            │
WS7: Instrument Specification ─────────────────────────────┤
                                                            ├─→ WS12: CLI Wrapper
WS8: Composable Scan Profiles ────────────────────────────┤
                                                            │
WS9: Language Packs ──────────────────────────────────────┘
                                                            │
WS10: Profile Inheritance ────────────────────────── independent
                                                            │
WS11: Scaffold Command ──────────────────────────── after WS7
                                                            │
WS13: Instrument Registry ──────────────────────── after WS7 + WS12
                                                            │
WS14: Documentation & Migration ────────────────── last
```

WS7 (specification) is the foundation — everything else depends on it.

---

## WS7 — Instrument Specification

**Why:** The current instrument contract is implicit — a README with phases, a config.yaml,
a fixes/ directory. There is no machine-readable manifest. Without one, you can't build
a registry, scaffold, CLI, or validation.

### WS7-01: Design instrument.yaml manifest schema

Define the machine-readable contract that every instrument must declare:

```yaml
# instrument.yaml
spec_version: "2.0"
id: I14
name: accessibility-tomographe
version: 1.0.0
description: "Web accessibility scanner — WCAG 2.1 compliance, ARIA patterns, keyboard navigation"
report_prefix: AX
domains: [accessibility, wcag, aria]

# What stack this instrument is relevant to
applicability:
  languages: [html, jsx, tsx, vue, svelte]    # empty = all languages
  platforms: [web, mobile]                     # empty = all platforms
  toggles: []                                 # profile toggles that gate this instrument

# Phase declarations
phases:
  - id: 1
    name: "Component Inventory"
    requires_llm: true
    prerequisites: []
  - id: 2
    name: "WCAG Audit"
    requires_llm: true
    prerequisites: ["phase:1"]
  - id: 3
    name: "Keyboard Navigation"
    requires_llm: false
    prerequisites: []
  - id: 4
    name: "Screen Reader Compatibility"
    requires_llm: true
    prerequisites: ["phase:1"]
  - id: 5
    name: "Report"
    requires_llm: false
    prerequisites: ["phase:1", "phase:2", "phase:3", "phase:4"]

# Accelerator tool declarations
accelerators:
  - tool: axe-core
    command: "npx axe-core --reporter=json"
    languages: [html, jsx, tsx]
    phases: [2]
  - tool: lighthouse
    command: "lighthouse --output=json --only-categories=accessibility"
    languages: [html]
    phases: [2, 3]

# DR section mapping
dr_sections: [S11]

# Dependencies on other instruments
dependencies: []

# Files that must exist in the instrument directory
required_files:
  - README.md
  - config.yaml
  - instrument.yaml
  - fixes/README.md
```

**Key design decisions:**

1. **`applicability` block** — instruments declare which stacks they're relevant to.
   The orchestrator uses this to skip instruments that don't apply (e.g., no point
   running accessibility-tomographe on a CLI tool).

2. **Phase prerequisites** — explicit dependency graph between phases, enabling
   the orchestrator to parallelise independent phases.

3. **Accelerator declarations** — structured metadata about external tools. The CLI
   can check tool availability before running, and language packs can provide them.

4. **`spec_version`** — enables forward compatibility. v2.0 manifests can coexist
   with future v3.0 manifests.

**Estimate:** 6–8h

---

### WS7-02: Write instrument.yaml for all 13 core instruments

Create manifests for the existing 13 instruments based on their current READMEs.
This is mostly extraction — the information exists, it just needs to be structured.

| Instrument | Phases | Accelerators to declare | Applicability |
|------------|--------|------------------------|---------------|
| architecture-tomographe | 7 | none (pure LLM) | all languages |
| code-tomographe | 7 | cargo, ruff, eslint, clang-format, clang-tidy, cppcheck | all languages |
| test-tomographe | 8 | cargo test, pytest, go test, jest, vitest, ctest, b2 | all languages |
| compliance-tomographe | 6 | yq | all languages |
| data-tomographe | 6 | psql, sqlite3 | languages with DB access |
| dependency-tomographe | 7 | cargo audit/deny/license, npm audit, pip audit, go-licenses | all languages |
| deployment-tomographe | 6 | docker, yq | all languages |
| documentation-tomographe | 6 | glossary-linter.sh | all languages |
| observability-tomographe | 6 | promtool, curl | all languages |
| performance-tomographe | 8 | docker stats, ab, wrk | all languages |
| security-tomographe | 8 | cargo audit, pip audit, npm audit, trivy, gitleaks, cppcheck | all languages |
| ai-ml-tomographe | 7 | python3, jq, curl | toggles: [ai_ml_components] |
| ux-tomographe | 8 | none (pure LLM) | platforms: [web, mobile, desktop] |

**Estimate:** 8–10h (13 instruments × ~45min each)

---

### WS7-03: Instrument validation tool

A script or CLI subcommand that validates an instrument directory against the spec:

```bash
qual-gate validate-instrument instruments/accessibility-tomographe/

✓ instrument.yaml exists and parses
✓ spec_version is 2.0
✓ All required_files present
✓ README.md has all declared phases
✓ config.yaml has thresholds section
✓ fixes/README.md exists
✓ Accelerator tools declared with commands
✗ Phase 3 declared in manifest but not found in README.md
```

This becomes the contribution gate — community instruments must pass validation.

**Estimate:** 4–6h

---

## WS8 — Composable Scan Profiles

**Why:** Teams don't always want a full 13-instrument scan. A security-focused team
wants security + compliance + dependency. A pre-release gate wants everything at strict
thresholds. Currently there's no way to express this without manual instrument selection.

### WS8-01: Design scan profile schema

```yaml
# profiles/quick.yaml
name: quick
description: "Fast feedback loop — code quality, tests, and security only"
instruments: [code-tomographe, test-tomographe, security-tomographe]
thresholds:
  override:
    code-tomographe:
      function_length_hard: 150    # relax for quick checks
    security-tomographe:
      max_medium_cves: 10          # focus on critical/high only
skip_phases:
  test-tomographe: [7]             # skip AI quality phase in quick mode
```

**Built-in profiles to ship with v2.0:**

| Profile | Instruments | Use Case |
|---------|-------------|----------|
| `quick` | code, test, security | Fast CI feedback on every push |
| `full` | all 13 | Comprehensive scan, nightly or weekly |
| `pre-release` | all 13, strict thresholds | Release gate — zero tolerance |
| `security` | security, compliance, dependency | Security-focused audit |
| `docs` | documentation, architecture | Documentation health check |
| `ai` | ai-ml, security (Phase 6), test (Phase 7) | AI/ML-specific quality |

**Estimate:** 4–6h

---

### WS8-02: Implement profile resolution in orchestrator

Update qualitoscope Phase 2 (Delegation) to:

1. Accept a `--profile` argument (or `profile:` field in scan config)
2. Load the profile definition
3. Filter instrument list to only those in the profile
4. Apply threshold overrides
5. Skip phases listed in `skip_phases`

This requires updates to:
- `qualitoscope/README.md` Phase 2 methodology
- `qualitoscope/config.yaml` (add profiles section or reference external files)
- `qualitoscope/methods/02-delegation.md`

**Estimate:** 4–6h

---

## WS9 — Language Packs

**Why:** Every Phase E-style "add C++ support" or "add TypeScript parity" pass requires
manually editing 4–8 instrument READMEs. Language packs bundle ecosystem-specific
accelerators into a single, maintainable unit.

### WS9-01: Design language pack schema

```yaml
# language-packs/cpp.yaml
name: cpp
display_name: "C/C++"
version: 1.0.0
file_extensions: [.cpp, .hpp, .h, .ipp, .cc, .hh, .cxx, .hxx]
test_file_patterns:
  - "test/*.cpp"
  - "test_*.cpp"
  - "*_test.cpp"
  - "*_test.cc"
test_frameworks:
  - name: "Google Test"
    assertion_patterns: ['EXPECT_', 'ASSERT_', 'TEST_F', 'TEST(']
  - name: "Boost.Test"
    assertion_patterns: ['BOOST_TEST', 'BOOST_CHECK', 'BOOST_REQUIRE']
  - name: "Catch2"
    assertion_patterns: ['REQUIRE', 'CHECK', 'TEST_CASE', 'SECTION']

# Accelerator commands per instrument phase
accelerators:
  code-tomographe:
    phase_1:  # Formatting & Linting
      - tool: clang-format
        check: "which clang-format"
        command: |
          find ${SOURCE_DIRS} -name '*.cpp' -o -name '*.hpp' -o -name '*.h' | \
            xargs clang-format --dry-run --Werror 2>&1 | head -20
      - tool: clang-tidy
        check: "which clang-tidy"
        command: |
          find ${SOURCE_DIRS} -name '*.cpp' | head -10 | \
            xargs clang-tidy 2>&1 | grep -c 'warning:\|error:'
      - tool: cppcheck
        check: "which cppcheck"
        command: "cppcheck --enable=all --quiet ${SOURCE_DIRS} 2>&1 | head -30"
    phase_2:  # Complexity
      - tool: grep
        command: |
          grep -rn '^[a-zA-Z].*(' ${SOURCE_DIRS} --include='*.cpp' --include='*.hpp' | \
            grep -v '^\s*//' | wc -l
    phase_3:  # Dead Code
      - tool: cppcheck
        check: "which cppcheck"
        command: "cppcheck --enable=unusedFunction ${SOURCE_DIRS} 2>&1"

  test-tomographe:
    phase_1:  # Inventory
      - tool: find
        command: "find ${TEST_DIRS} -name '*.cpp' | wc -l"
      - tool: ctest
        check: "which ctest"
        command: "ctest --test-dir build/ --show-only 2>/dev/null"
    phase_3:  # Quality (assertion patterns)
      - tool: grep
        command: |
          grep -rn 'BOOST_TEST\|BOOST_CHECK\|BOOST_REQUIRE' ${TEST_DIRS} --include='*.cpp' | wc -l
          grep -rn 'EXPECT_\|ASSERT_\|TEST_F\|TEST(' ${TEST_DIRS} --include='*.cpp' | wc -l
          grep -rn 'REQUIRE\|CHECK\|TEST_CASE\|SECTION' ${TEST_DIRS} --include='*.cpp' | wc -l
    phase_5:  # Health (run tests)
      - tool: ctest
        check: "which cmake"
        command: "cmake --build build/ && ctest --test-dir build/ --output-on-failure"
      - tool: b2
        check: "which b2"
        command: "b2 test"

  security-tomographe:
    phase_1:  # Supply Chain
      - tool: cppcheck
        check: "which cppcheck"
        command: |
          cppcheck --enable=all --suppress=missingInclude ${SOURCE_DIRS} 2>&1 | \
            grep -i 'security\|overflow\|injection'

  documentation-tomographe:
    phase_1:  # Inventory (Doxygen comments)
      - tool: grep
        command: |
          grep -rn '///\|//!\|/\*\*' ${SOURCE_DIRS} \
            --include='*.cpp' --include='*.hpp' --include='*.h' | wc -l

# Build system detection signals (fed to Phase 0)
build_signals:
  - file: "CMakeLists.txt"
    system: cmake
    confidence: strict
  - file: "build.jam"
    system: "b2 (Boost.Build)"
    confidence: strict
  - file: "Jamfile"
    system: "b2 (Boost.Build)"
    confidence: strict
  - file: "Makefile"
    system: make
    confidence: heuristic

# Documentation format signals
doc_formats:
  - extension: .adoc
    type: asciidoc
    frontmatter_fields: [":revdate:", ":author:", ":version:"]
    link_patterns: ["xref:", "<<.*>>", "include::"]
```

**Estimate:** 6–8h

---

### WS9-02: Create language packs for validated ecosystems

Create packs for ecosystems already validated in v1.0, extracting accelerators
from the current instrument READMEs into structured pack files.

| Pack | Source | Complexity |
|------|--------|------------|
| `rust.yaml` | Existing cargo commands in instruments | Low — well-documented |
| `python.yaml` | Existing pytest/pip commands | Low |
| `typescript.yaml` | Phase E additions (vitest, jest, eslint) | Medium |
| `cpp.yaml` | Phase E additions (clang, cppcheck, b2) | Medium |
| `go.yaml` | Existing go commands | Low |
| `java-kotlin.yaml` | Existing gradle/maven commands | Low |

**Estimate:** 12–16h (6 packs × 2–3h each)

---

### WS9-03: Language pack resolution in orchestrator

Update orchestrator to:

1. Detect languages from project profile (or Phase 0)
2. Load matching language packs
3. Inject pack accelerators into instrument execution context
4. Fall back to LLM-only steps when no pack or tool is available

This replaces the current pattern of hardcoding multi-language command blocks
in each instrument README. Instrument READMEs become language-agnostic, and
packs supply the ecosystem-specific commands.

**Migration path:** Instruments retain inline accelerators for v2.0 backward
compatibility. Packs are additive — they supplement, not replace. In v2.1+,
inline accelerators may be deprecated in favour of pack-only delivery.

**Estimate:** 6–8h

---

## WS10 — Profile Inheritance

**Why:** Organisations with multiple repos want shared quality standards.
Currently each repo needs its own complete `project-profile.yaml`. With
inheritance, a base profile defines org-wide standards and per-repo profiles
override only what differs.

**Deferred from v1.0** (ROADMAP.md, Open Question #3).

### WS10-01: Design `extends:` field

```yaml
# project-profile.yaml (per-repo)
extends: https://gitlab.example.com/quality/base-profile.yaml
# or: extends: ../shared/base-profile.yaml
# or: extends: @org/quality-standards  (registry reference, v2.1+)

name: my-service
stack:
  languages: [rust]         # override base
paths:
  source_dirs: [crates/]    # override base
# Everything else inherited from base profile
```

**Merge semantics:**
- Scalars: child overrides parent
- Lists: child replaces parent (no merge — explicit is better than implicit)
- Objects: deep merge (child keys override, parent keys preserved)
- `toggles`: child can only enable, never disable a parent toggle (safety)

**Estimate:** 4–6h

---

### WS10-02: Implement profile resolution chain

Update qualitoscope Phase 1 to:

1. Load the child profile
2. If `extends:` is present, fetch the parent (local path, URL, or registry ref)
3. Deep-merge parent → child
4. Validate the merged result against the schema
5. Cache resolved profiles to avoid re-fetching

Support at most 3 levels of inheritance (child → parent → grandparent) to prevent
complexity. Circular references are a validation error.

**Estimate:** 4–6h

---

## WS11 — Scaffold Command

**Why:** Creating a new instrument requires 8+ files with correct naming, structure,
and cross-references. A scaffold command generates the boilerplate and wires the
instrument into the orchestrator.

**Depends on:** WS7 (instrument specification).

### WS11-01: Implement scaffold generator

```bash
qual-gate new-instrument accessibility-tomographe \
  --phases=6 \
  --domains=accessibility,wcag \
  --dr-sections=S11 \
  --prefix=AX
```

Generates:
```
instruments/accessibility-tomographe/
├── instrument.yaml          # Pre-filled manifest
├── README.md                # Phase skeleton with LLM step placeholders
├── config.yaml              # Default thresholds
├── methods/
│   ├── 01-component-inventory.md
│   ├── 02-wcag-audit.md
│   ├── ...
│   └── 06-report.md
├── checklists/
│   └── accessibility-posture.md
├── templates/
│   └── report-template.md
└── fixes/
    └── README.md
```

Also updates:
- `qualitoscope/config.yaml` — adds instrument to registry
- Prints next steps: "Fill in LLM steps, add accelerators, run validation"

**Estimate:** 6–8h

---

## WS12 — CLI Wrapper

**Why:** The CLI is the bridge between methodology and automation. It handles
profile resolution, instrument selection, output management, and AI provider
delegation. It does NOT interpret methodology — it passes it to the AI.

**Depends on:** WS7 (spec), WS8 (profiles).

### WS12-01: Design CLI architecture

```
qual-gate/
├── cli/
│   ├── pyproject.toml           # or Cargo.toml if Rust
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py              # Entry point, arg parsing
│   │   ├── profile.py           # Profile loading, inheritance, validation
│   │   ├── instruments.py       # Instrument discovery, manifest parsing
│   │   ├── profiles.py          # Scan profile resolution
│   │   ├── packs.py             # Language pack loading
│   │   ├── runner.py            # AI provider abstraction
│   │   ├── output.py            # Report management, naming, delta tracking
│   │   └── scaffold.py          # new-instrument generator
│   └── tests/
```

**Language choice:** Python. Reasons:
- Fastest to iterate on for a v2.0 MVP
- AI provider SDKs (Anthropic, OpenAI) have first-class Python support
- Target audience (engineering teams) universally has Python available
- Can migrate to Rust in Horizon 3 if performance matters

**Subcommands:**

| Command | What it does |
|---------|--------------|
| `scan` | Run a quality scan (full or profile-based) |
| `validate-profile` | Check project-profile.yaml against schema |
| `validate-instrument` | Check instrument directory against spec |
| `new-instrument` | Scaffold a new instrument |
| `list` | List installed instruments and profiles |
| `diff` | Compare two scan outputs (delta analysis) |

**Estimate:** 8–10h (MVP — scan + validate subcommands only)

---

### WS12-02: Implement Claude Code runner

The runner module invokes Claude Code to execute instrument scans:

```python
class ClaudeRunner:
    """Invokes Claude Code CLI to execute instrument scans."""

    def execute_instrument(
        self,
        instrument_path: Path,
        profile: ProjectProfile,
        language_packs: list[LanguagePack],
        output_dir: Path,
    ) -> InstrumentReport:
        """Invoke claude CLI with instrument README as prompt."""
        ...
```

**Implementation:** Invoke `claude` CLI via subprocess, passing the instrument
README as the system prompt and the target project as the working directory.
Leverage Claude Code features: sub-agents for parallel phase execution, tool use
for file operations, MCP for structured output.

**No provider abstraction layer for v2.0.** Claude Code is the only supported
runner. A provider-agnostic interface can be added in Horizon 3 if demand emerges.

**Estimate:** 6–8h

---

### WS12-03: Output management and delta tracking

Currently output goes to `output/YYYY-MM-DD_{project_name}/`. The CLI formalises this:

- Automatic timestamped output directories
- `output/latest/` symlink to most recent run
- Machine-readable index (`output/index.json`) tracking all runs
- `qual-gate diff` command compares two runs
- Retention policy (configurable, default: keep 20 runs)

**Estimate:** 4–6h

---

## WS13 — Instrument Registry (Stretch)

**Why:** A registry enables discovery and installation of community instruments.
This is the v2.0 stretch goal — essential for the community model but not required
for the core platform to function.

**Depends on:** WS7 (spec), WS12 (CLI).

### WS13-01: Design registry format

Start simple — a Git repository with an index file:

```yaml
# registry/index.yaml
instruments:
  - name: accessibility-tomographe
    version: 1.0.0
    author: "qual-gate community"
    repo: https://github.com/qual-gate-community/accessibility-tomographe
    spec_version: "2.0"
    tier: community     # core | community | experimental
    domains: [accessibility, wcag]

  - name: api-contract-tomographe
    version: 0.1.0
    author: "contributor-name"
    repo: https://github.com/contributor/api-contract-tomographe
    spec_version: "2.0"
    tier: experimental
    domains: [api, openapi, contracts]
```

**Installation:**
```bash
qual-gate add accessibility-tomographe
# Clones repo into instruments/, validates against spec, registers in config
```

**Estimate:** 8–12h

---

## WS14 — Documentation & Migration

**Why:** v2.0 introduces breaking changes (instrument.yaml required, CLI workflow,
language packs). Existing users need a migration guide. New features need documentation.

### WS14-01: Migration guide (v1.0 → v2.0)

Document:
- How to add `instrument.yaml` to custom instruments
- How to adopt scan profiles
- How to install and use the CLI
- How language packs interact with existing inline accelerators
- Profile inheritance migration for multi-repo setups

**Estimate:** 4–6h

---

### WS14-02: Update all existing documentation

- `README.md` — add CLI quick-start, profiles, language packs
- `docs/getting-started.md` — rewrite for CLI-based workflow
- `docs/instrument-authoring-guide.md` — add instrument.yaml spec, scaffold workflow
- `docs/project-profile-reference.md` — add `extends:` field documentation
- `VISION.md` — update "Where We Are" section for v2.0

**Estimate:** 6–8h

---

### WS14-03: Update ROADMAP

Archive v1.0 roadmap, replace with v2.0 as current, update version milestones.

**Estimate:** 2h

---

## Phasing

### Phase F — Specification & Foundation (WS7 + WS10)

**What:** Define the instrument contract, create manifests for all 13 instruments,
and add profile inheritance. This is pure design + content work — no code.

| Issue | Estimate | Dependencies |
|-------|----------|--------------|
| WS7-01: instrument.yaml schema | 6–8h | SD decisions resolved |
| WS7-02: Manifests for 13 instruments | 8–10h | WS7-01 |
| WS7-03: Instrument validation tool | 4–6h | WS7-01 |
| WS10-01: Profile `extends:` design | 4–6h | None |
| WS10-02: Profile resolution chain | 4–6h | WS10-01 |

**Total:** 26–36h
**Milestone:** Every instrument has a machine-readable manifest. Profile inheritance
works. Instrument validation catches spec violations.

---

### Phase G — Profiles & Packs (WS8 + WS9)

**What:** Composable scan profiles and language packs. Can start WS9 in parallel
with Phase F.

| Issue | Estimate | Dependencies |
|-------|----------|--------------|
| WS8-01: Scan profile schema | 4–6h | WS7-01 |
| WS8-02: Profile resolution in orchestrator | 4–6h | WS8-01 |
| WS9-01: Language pack schema | 6–8h | WS7-01 |
| WS9-02: 6 language packs | 12–16h | WS9-01 |
| WS9-03: Pack resolution in orchestrator | 6–8h | WS9-01 |

**Total:** 32–44h
**Milestone:** Teams can run `--profile=quick` for fast CI feedback. Language packs
provide ecosystem-specific accelerators without manual README editing.

---

### Phase H — CLI & Tooling (WS11 + WS12)

**What:** The programmatic layer. Build the CLI, scaffold command, and output
management.

| Issue | Estimate | Dependencies |
|-------|----------|--------------|
| WS11-01: Scaffold generator | 6–8h | WS7-01 |
| WS12-01: CLI architecture | 8–10h | WS7-01, WS8-01 |
| WS12-02: AI provider abstraction | 6–8h | WS12-01 |
| WS12-03: Output management | 4–6h | WS12-01 |

**Total:** 24–32h
**Milestone:** `qual-gate scan` works end-to-end. New instruments can be scaffolded
with a single command.

---

### Phase I — Registry & Docs (WS13 + WS14)

**What:** Community instrument registry (stretch) and documentation for all v2.0
features.

| Issue | Estimate | Dependencies |
|-------|----------|--------------|
| WS13-01: Registry format + install | 8–12h | WS7-01, WS12-01 |
| WS14-01: Migration guide | 4–6h | All WS complete |
| WS14-02: Update docs | 6–8h | All WS complete |
| WS14-03: Update ROADMAP | 2h | All WS complete |

**Total:** 20–28h
**Milestone:** Community can contribute instruments. All v2.0 features documented.
Migration path from v1.0 is clear.

---

## Summary

| Phase | Workstreams | Effort | Unlocks |
|-------|-------------|--------|---------|
| F — Specification | WS7, WS10 | 26–36h | Machine-readable instrument contract, profile inheritance |
| G — Profiles & Packs | WS8, WS9 | 32–44h | Composable scans, ecosystem-specific accelerators |
| H — CLI & Tooling | WS11, WS12 | 24–32h | Programmatic interface, scaffold, output management |
| I — Registry & Docs | WS13, WS14 | 20–28h | Community instruments, migration, documentation |
| **Total** | | **102–140h** | **v2.0.0 release** |

**Critical path:** SD decisions → WS7-01 (spec) → WS12-01 (CLI) → WS14 (docs)

Phases F and G can overlap: WS9 (language packs) and WS10 (profile inheritance)
are independent of each other and can start as soon as WS7-01 delivers the spec.

Phase H can start as soon as WS7-01 and WS8-01 are done — it doesn't need all
manifests or all language packs to begin.

---

## Version Milestones

| Version | What ships | Status |
|---------|------------|--------|
| v1.0.0 | Universal quality gate — 13 instruments, validated on 3 ecosystems | Shipped |
| v1.1.0 | Instrument specification + manifests for all 13 (Phase F). Last release supporting instruments without `instrument.yaml`. | Planned |
| v1.2.0 | Profile inheritance + scan profiles + language packs (Phase F+G). `instrument.yaml` required. | Planned |
| v2.0.0 | CLI wrapper + scaffold + registry + full documentation (Phase H+I) | Planned |

**Note:** v1.1.0 and v1.2.0 are intermediate releases on the path to v2.0. They
ship value incrementally — the instrument spec is useful even without the CLI,
and language packs improve v1.x users' experience immediately.

**Compatibility:** v1.1.0 is the one-minor-release compatibility window. Instruments
without `instrument.yaml` work but emit a deprecation warning. v1.2.0+ requires it.

---

## Open Questions (Resolved)

1. ~~**CLI language: Python or Rust?**~~ **Resolved: Python 3.13+.** Fastest iteration,
   first-class Anthropic SDK support, universally available. Evaluate Rust for v3.0
   if performance becomes a bottleneck.

2. ~~**Registry hosting.**~~ **Resolved: Git repo.** A `registry/index.yaml` in a
   public repo. Zero infrastructure. Migrate to a service when community grows past
   ~50 instruments.

3. ~~**Language pack granularity.**~~ **Resolved: One pack per language.** `rust.yaml`,
   `python.yaml`, `cpp.yaml`, etc. Add ecosystem-specific packs (e.g., `react.yaml`)
   when demand emerges.

4. ~~**Backward compatibility.**~~ **Resolved: One minor release cycle.** v1.1.0
   supports instruments with or without `instrument.yaml` (warns on missing). v1.2.0
   requires manifests.

5. ~~**AI provider testing.**~~ **Resolved: No real credentials in CI.** This is a
   public repo. CLI unit tests use a mock Claude runner. Integration tests are
   local-only (developer runs manually with their own Claude Code install). No API
   keys in CI pipelines.
