---
title: "v2.0 Strategic Decisions"
status: accepted
last-updated: 2026-03-19
---

# ADR-002: v2.0 Strategic Decisions

Decisions that shape the v2.0 architecture. Resolved 2026-03-19.

---

## SD-01: Packaging Model — CLI Wrapper

**Decision:** Build a Python CLI (`qual-gate`) that orchestrates scanning.

**Context:** v1.0 is a methodology repo with no programmatic interface. Users must
manually open an AI assistant, paste prompts, and manage output. This blocks CI
integration and limits adoption to users comfortable with manual AI interaction.

**Rationale:**
- A CLI bridges the gap between methodology and automation
- The methodology markdown stays the source of truth — the CLI reads it, doesn't
  interpret it
- Enables CI integration (Horizon 3) without rewriting the methodology
- Lowers adoption friction for engineering teams

**Rejected alternative:** Methodology-only (no CLI). Simpler but can't integrate
with CI and requires too much manual ceremony per scan.

---

## SD-02: AI Provider — Claude-Specific for v2.0

**Decision:** v2.0 targets Claude Code exclusively. No provider abstraction layer.

**Context:** VISION.md recommended a provider-agnostic spec with a Claude Code
reference implementation. After review, the abstraction layer adds engineering
complexity without delivering value — there is currently no second provider that
can execute qual-gate's methodology with equivalent quality.

**Rationale:**
- Claude Code is the only execution engine that supports the full workflow:
  file reading, command execution, sub-agents, structured output, large context
- Building an abstraction layer for hypothetical future providers is speculative
  engineering — it adds code without adding users
- Tight Claude Code integration (sub-agents for parallel phases, MCP for output)
  delivers a better experience than a lowest-common-denominator interface
- Provider-agnostic abstraction can be introduced in Horizon 3 when demand and
  competing capabilities materialise

**What this means:**
- The `qual-gate` CLI invokes `claude` directly via subprocess
- Instrument specs may reference Claude Code capabilities (sub-agents, tool use)
- The CLI requires Claude Code installed on the host machine
- No API keys in the CLI itself — Claude Code manages authentication

**Scope for future change:** If a second capable AI agent emerges, introduce a
`Runner` protocol in v3.0. The v2.0 `ClaudeRunner` becomes the first implementation.
This is a deliberate deferral, not a permanent lock-in.

---

## SD-03: Community Model — Two-Tier

**Decision:** Core instruments (13, maintainer-reviewed) + community instruments
(spec-validated, clearly labelled).

**Context:** qual-gate needs a path for community-contributed instruments (e.g.,
accessibility, API contracts, mobile-specific checks) without diluting the quality
of the core set.

**Rationale:**
- Core instruments ship with every release and receive the same review rigour as
  the methodology itself
- Community instruments must pass `validate-instrument` (spec compliance) but are
  not reviewed for domain correctness
- Clear labelling (tier: core | community | experimental) sets user expectations
- Low barrier to contribute, high barrier to promote to core

**Governance:** Community instruments require:
- Valid `instrument.yaml` manifest (passes validation)
- README with all declared phases
- `config.yaml` with defaults
- At least one fix guide per finding category
- Apache 2.0 or compatible licence

---

## SD-04: Target Audience — Engineering Teams

**Decision:** v2.0 targets engineering teams, not individual devs or enterprises.

**Context:** v1.0 already serves individual devs (clone and scan). Enterprise features
(audit trails, SSO, compliance reports) are heavyweight and premature. Engineering
teams are the natural next audience — they need CI integration, shared scan profiles,
and multi-repo configuration.

**Rationale:**
- Teams are the bridge between individual adoption and org-wide rollout
- The features teams need (profiles, inheritance, CLI) are the foundation for
  enterprise features later
- Serving teams first builds the user base that justifies enterprise investment

---

## OQ-01: CLI Language — Python 3.13+

**Decision:** Python, latest stable version (3.13+ at time of writing).

**Rationale:** Fastest iteration cycle, first-class Anthropic SDK, universally
available on developer machines. Evaluate Rust for v3.0 if CLI performance becomes
a bottleneck (unlikely — the AI execution dominates wall time).

---

## OQ-02: Registry Hosting — Git Repo

**Decision:** A public Git repo with `registry/index.yaml` as the instrument index.

**Rationale:** Zero infrastructure, works today, easy to contribute to (PR to add
an entry). Migrate to a dedicated service when community grows past ~50 instruments.

---

## OQ-03: Language Pack Granularity — One Per Language

**Decision:** One pack per language (`rust.yaml`, `python.yaml`, `cpp.yaml`, etc.).

**Rationale:** Simple, predictable, easy to maintain. Ecosystem-specific packs
(e.g., `react.yaml` extending `typescript.yaml`) can be added when demand emerges.
Don't over-architect before there's signal.

---

## OQ-04: Backward Compatibility — One Minor Release

**Decision:** v1.1.0 supports instruments with or without `instrument.yaml`
(deprecation warning). v1.2.0 requires manifests.

**Rationale:** One minor release gives users a clear migration window without
carrying compatibility code indefinitely. The warning-then-error pattern is
standard and well-understood.

---

## OQ-05: CLI Testing — No Real Credentials in CI

**Decision:** Mock Claude runner for CI. Real integration tests are local-only.

**Context:** This is a public repo. No API keys or credentials in CI pipelines.

**Rationale:**
- Unit tests use a `MockClaudeRunner` that returns canned instrument reports
- Integration tests run locally by developers with their own Claude Code install
- CI validates: profile parsing, instrument spec validation, output management,
  scaffold generation — everything that doesn't require an AI provider
- This covers ~80% of the CLI surface without any credentials
