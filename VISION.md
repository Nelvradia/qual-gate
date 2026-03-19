---
title: "qual-gate — Long-Term Vision"
status: current
last-updated: 2026-03-19
---

# qual-gate — Long-Term Vision

> Universal design review and quality gate for every programming language.

---

## Where We Are Today (v0.3.0)

qual-gate is a suite of 13 AI-executed quality instruments that scan any codebase through
structured methodology documents. The core insight: **the README is the program** — no
compilation, no runtime, no language-specific tooling required. An AI assistant reads the
methodology and executes it against whatever project it is pointed at.

### Current Strengths

- **Language-agnostic by design.** LLM steps work on any codebase, any tech stack.
- **13 domains of coverage.** Architecture, testing, code quality, documentation, compliance,
  data, deployment, observability, security, performance, UX, AI/ML, and dependencies.
- **Unified severity scale.** All instruments use the same 5-level scale
  (Critical / Major / Minor / Observation / OK), enabling meaningful aggregation.
- **Design Review mode.** Findings map directly to a formal DR template (S1–S14, K1–K4).
- **Delta tracking.** Trend analysis across runs — quality trajectory over time.
- **Dual-method execution.** Every phase has pure LLM steps (universal) and optional accelerator
  commands (faster when the toolchain is available).

### Current Limitations

- Some instruments contain project-specific logic (cross-correlation rules, glossary linter,
  OWASP checklists) that needs generalisation.
- No programmatic extension mechanism — adding an instrument is a manual process.
- The `fixes/` remediation layer is mostly empty.
- `dependency-tomographe` is not wired into the orchestrator registry.
- No packaging or distribution story — it is a repository you clone.
- Implicitly coupled to Claude Code as the execution engine.

---

## The Differentiator

qual-gate occupies a space that traditional static analysis tools cannot reach.

| Traditional tools (SonarQube, Semgrep, CodeClimate) | qual-gate |
|------------------------------------------------------|-----------|
| Parse AST, run fixed rules | Understand intent, context, architecture |
| Language-specific engines | Language-agnostic reasoning + optional accelerators |
| Binary pass/fail per rule | Contextual severity with cross-domain correlation |
| Fixed rule sets | Methodology that adapts to what it reads |
| Code analysis only | Architecture, docs, deployment, UX, compliance, data |

No traditional tool can look at code and say "this module violates the architectural boundary
described in your design doc." qual-gate can, because the AI reads both the code and the docs.

---

## Horizons

### Horizon 1 — Generalise & Harden (v1.0)

**Goal:** Make qual-gate work reliably on any project without manual customisation.

#### Project Profile

Extract all target-specific references (path patterns, domain concepts, architectural
assumptions) into a `project-profile.yaml` that users fill in once. Instruments read the
profile — not hardcoded paths.

```yaml
# project-profile.yaml (example)
name: my-project
stack:
  languages: [rust, typescript]
  build: [cargo, vite]
  ci: gitlab-ci
architecture:
  style: modular-monolith
  boundary_marker: crate       # or "package", "module", "namespace"
  entry_points: [src/main.rs, apps/web/src/main.tsx]
conventions:
  permission_config: config/access-control.yaml   # or null
  glossary: docs/glossary.md                       # or null
```

#### Auto-Discovery (Phase 0)

The orchestrator detects the project's tech stack, directory layout, and build system
automatically. It populates `source_dirs` and suggests a draft `project-profile.yaml`
for the user to confirm.

#### Orchestrator Completeness

- Wire `dependency-tomographe` as I13.
- Generalise cross-correlation rules (XC-01 through XC-08) to be parameterised by
  the project profile rather than assuming specific architectural patterns.

#### Remediation Library

Populate `fixes/` directories with actionable guidance per finding type, per language.
This is the difference between "you have a problem" and "here is how to fix it."

---

### Horizon 2 — Plugin Architecture & Community (v2.0)

**Goal:** Let anyone create, share, and compose instruments.

#### Instrument Specification

Formalise the instrument contract into a machine-readable manifest:

```yaml
# instrument.yaml
id: I14
name: accessibility-tomographe
version: 1.0.0
report_prefix: AX
domains: [accessibility, wcag, aria]
supported_stacks: [web, mobile]
phases: 6
accelerators:
  - tool: axe-core
    languages: [html, jsx, tsx]
  - tool: lighthouse
    languages: [html]
dependencies: []
```

Required files, config schema, severity mapping, and output schema — all declared.

#### Instrument Registry

A central index where community instruments can be discovered and installed:

```
qual-gate add accessibility-tomographe
qual-gate add api-contract-tomographe
qual-gate list --installed
```

#### Composable Scan Profiles

Named profiles that select instrument subsets with tuned thresholds:

```yaml
profiles:
  quick:        [code, test, security]
  full:         [all]
  pre-release:  [all, thresholds: strict]
  security:     [security, compliance, dependency]
```

Teams define their own quality gate profiles to match their workflow.

#### Language Packs

Bundled accelerator commands and language-specific heuristics for each ecosystem:

- **Python pack:** `ruff`, `mypy`, `bandit`, `safety`, `pytest --cov`
- **Rust pack:** `cargo clippy`, `cargo audit`, `cargo deny`, `cargo llvm-cov`
- **Go pack:** `golangci-lint`, `govulncheck`, `go test -cover`
- **TypeScript pack:** `eslint`, `tsc --noEmit`, `vitest --coverage`

LLM steps stay universal. Accelerators get smarter per ecosystem.

#### Scaffold Command

```
qual-gate new-instrument my-domain-check
```

Generates the directory structure, templates, config, and wires it into the orchestrator.

---

### Horizon 3 — CI Integration & Programmatic API (v3.0)

**Goal:** qual-gate becomes a first-class CI/CD quality gate.

#### CLI Wrapper

A thin CLI that orchestrates AI execution:

```bash
qual-gate scan --profile=full --target=./my-project
qual-gate scan --instruments=security,compliance --format=sarif
qual-gate diff --baseline=output/2026-03-01 --current=output/2026-03-18
```

Handles config resolution, output management, and delta tracking.

#### CI Mode

- Machine-readable output (JSON / SARIF) alongside Markdown reports.
- Exit codes: `0` = PASS, `1` = PASS-WITH-CONDITIONS, `2` = FAIL.
- Direct integration templates for GitLab CI, GitHub Actions, Azure Pipelines.

```yaml
# .gitlab-ci.yml example
quality-gate:
  stage: test
  script:
    - qual-gate scan --profile=pre-release --format=json
  artifacts:
    reports:
      codequality: output/latest/findings.json
```

#### SARIF Export

Findings in SARIF format for IDE integration — VS Code problem panel, IntelliJ inspections,
GitLab code quality widgets.

#### MR/PR Annotations

Automatically post findings as review comments on merge requests. Inline annotations on the
diff, not just a wall of text in a comment.

#### Quality Dashboard

A lightweight web UI (or static site via GitLab Pages) that visualises:

- Quality trends over time per instrument.
- Instrument-by-instrument health breakdown.
- Cross-project comparisons within an organisation.

---

### Horizon 4 — Intelligence Layer (v4.0+)

**Goal:** Move from static methodology to adaptive quality intelligence.

#### Learning from Findings

Track which findings get accepted vs. dismissed across runs. Instruments learn
project-specific noise and adjust severity or suppress known-accepted patterns.

#### Cross-Project Benchmarking

Anonymous aggregation across opt-in projects:

> "Your test coverage is in the 30th percentile for Rust projects of this size."

Gives teams context for their quality posture — not just absolute numbers, but relative
standing.

#### Architecture Fitness Functions

Define executable quality constraints that are continuously evaluated:

```yaml
fitness_functions:
  - name: module-coupling
    rule: "no module may have > 5 direct dependencies"
    instrument: architecture
    severity: major

  - name: latency-budget
    rule: "p99 latency must stay below 50ms"
    instrument: performance
    severity: critical
```

qual-gate enforces these as living contracts, not one-off checks.

#### Multi-Repo Coherence

For organisations with many repositories, scan across repos and detect systemic patterns:

> "8 of your 12 services have the same logging anti-pattern."
> "3 repos have diverged from the shared API contract schema."

---

## Strategic Decision Points

These are open questions that will shape the project's direction. They do not need to be
answered now, but they need to be answered before Horizon 2.

### 1. Packaging Model

Stay as a methodology repo that users clone and point their AI at? Or build a CLI that wraps
the AI execution and manages the workflow?

- **Methodology-only** — simpler, lower maintenance, but harder to adopt and impossible to
  integrate into CI.
- **CLI wrapper** — opens CI integration, discoverability, and automation, but adds a
  software engineering burden.

### 2. AI Provider Coupling

Currently implicitly tied to Claude Code. Should instruments be provider-agnostic?

- **Provider-agnostic** — instruments work with any sufficiently capable LLM agent. Broader
  adoption, but harder to optimise and test.
- **Claude-optimised** — leverage Claude-specific capabilities (sub-agents, tool use, large
  context). Better experience, smaller audience.
- **Recommended path:** Provider-agnostic methodology with a Claude Code reference
  implementation. Other providers can implement their own runners.

### 3. Open-Source Community Model

If the project wants community-contributed instruments, it needs: a specification, a registry,
quality standards, and governance.

- How open should instrument contribution be?
- Who reviews and approves community instruments?
- Is there a "verified" tier vs. community tier?

### 4. Revenue Model (If Any)

Options, not mutually exclusive:

- **Fully open-source.** Community-driven, no revenue. Sustainability through sponsorship.
- **Open core.** Free instruments + paid orchestrator or enterprise features (SSO, audit
  trails, compliance reports).
- **Marketplace.** Free core + paid specialised instruments (industry-specific compliance,
  regulated domains).
- **Consulting / services.** Open-source tool, paid implementation and customisation.

### 5. Target Audience

- **Individual developers** — lightweight, fast, low ceremony.
- **Engineering teams** — CI integration, shared profiles, MR annotations.
- **Enterprises with formal DR processes** — full DR mode, compliance instruments, audit
  trails.

The DR mode suggests enterprise. The AI-native execution model suggests a technically
sophisticated audience. The language-agnostic promise suggests broad appeal. These audiences
have different needs — the project must decide which to serve first.

---

## Principles

These principles should guide decisions across all horizons.

1. **The methodology is the product.** The structured, domain-expert knowledge encoded in
   each instrument is what makes qual-gate valuable. Everything else — CLI, CI, dashboards —
   is distribution.

2. **Language-agnostic first, language-optimised second.** Every instrument must work on any
   codebase through LLM steps alone. Accelerators enhance speed and precision but are never
   required.

3. **Opinionated defaults, full configurability.** Ship with sensible thresholds and profiles
   that work for most projects. Let teams override everything.

4. **Findings must be actionable.** A finding without remediation guidance is just noise.
   Every finding type should eventually have a corresponding entry in `fixes/`.

5. **Quality is multi-dimensional.** Code quality is one of thirteen dimensions. Architecture,
   documentation, security, deployment, observability — they all matter. qual-gate's value is
   the integrated view.

6. **Trend over snapshot.** A single scan is useful. A quality trajectory over time is
   transformative. Delta tracking and trend analysis are core, not optional.
