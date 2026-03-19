---
title: "Changelog"
status: current
last-updated: 2026-03-19
---

# Changelog

All notable changes to qual-gate are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased] — v1.1.0-dev

### Added

- **instrument.yaml manifest schema** (`instrument.schema.yaml`) — machine-readable
  spec for instrument metadata, phases, dependencies, and profile field consumption.
- **instrument.yaml manifests for all 13 core instruments** — each instrument now has
  a manifest declaring its identity, phases, accelerators, required files, and profile
  fields consumed.
- **`validate-instrument` CLI tool** (`cli/validate_instrument.py`) — validates
  instrument directories against the manifest schema with 10 automated checks.
- **Profile inheritance** (`extends:` field in `project-profile.schema.yaml`) — child
  profiles inherit from parent profiles with scalar override, list replacement, object
  deep-merge, and toggle safety semantics.
- **Profile resolution chain** (`cli/resolve_profile.py`) — resolves `extends:` chains
  up to 3 levels with circular reference detection and toggle safety enforcement.
- Annotated example manifest (`instrument.example.yaml`) for hypothetical I14
  accessibility-tomographe.
- Unit tests for validation tool (20 tests) and profile resolution (20 tests).
- Integration test validating all 13 core instruments against the manifest spec.
- Test fixtures for valid/invalid instruments and profile inheritance scenarios.

### Changed

- `docs/instrument-authoring-guide.md` — added "Instrument Manifest" section, updated
  directory structure and readiness checklist to require `instrument.yaml`.
- `docs/project-profile-reference.md` — added "Inheritance" section documenting merge
  semantics, toggle safety, depth limit, and examples.
- `project-profile.example.yaml` — added commented `extends:` example at top.

---

## [1.0.0] — 2026-03-19

### Added
- Remediation library: fix guides for all 13 instruments with per-language code examples
- Dependency-tomographe fix guides (5 guides: unused deps, licence risk, unmaintained deps,
  missing lockfile, excessive transitive deps)
- DR section S14 for AI/ML quality dimension
- `.claudeignore` for Claude Code file discovery
- Fixes content standard (`instruments/fixes-content-standard.md`)
- Getting-started guide (`docs/getting-started.md`)
- Project profile field reference (`docs/project-profile-reference.md`)
- Instrument authoring guide (`docs/instrument-authoring-guide.md`)
- This CHANGELOG
- Phase 0 heuristics expanded: b2 build system, include/ dirs, monorepo
  workspaces, PaaS platforms, colocated tests, documentation-only projects
- Explicit "phase skipped" prerequisite blocks on all conditional phases
- C++ accelerator commands across code, test, security, documentation instruments
- AsciiDoc and Doxygen support in documentation-tomographe
- TypeScript/Node accelerator parity improvements
- AI/ML project-type classification (gateway, agent, training, RAG)

### Changed
- Glossary linter absorbed into documentation-tomographe as accelerator command
  (`instruments/documentation-tomographe/accelerators/glossary-linter.sh`)
- ROADMAP open questions resolved (AI-ML → S14, glossary absorbed, inheritance deferred,
  validation targets selected)
- VISION.md now tracked in version control
- Root README updated with "How to Run" section and documentation links
- ROADMAP version milestones reconciled with actual delivery
- All instrument accelerator commands now reference profile paths instead
  of hardcoded src/

### Fixed
- Removed stale `instruments/dependency-tomographe/output/` directory
- Frontmatter version inconsistencies in VISION.md and ROADMAP.md

---

## [0.5.0] — 2026-03-18

### Added
- Phase 0 auto-discovery methodology (`qualitoscope/methods/00-auto-discovery.md`)
- Phase 0 integration into qualitoscope orchestration (Phase 0–8 numbering)
- Conditional toggle support — instrument phases skip cleanly when toggles are false
- Glossary linter accepts `--terms-file`, `--allowlist`, `--type`, `--glossary-doc` flags
- `glossary-terms.example.yaml` for customisable terminology
- Platform-specific security checks conditioned on `profile.platforms.targets`

### Changed
- Cross-correlation rules generalised: XC-02 → `component_without_auth_entry`,
  XC-05 → `ai_config_change_without_eval`
- Architecture checklist split into universal and profile-driven sections
- Access control scanning conditional on `profile.toggles.permission_system`
- dependency-tomographe wired as I13 in orchestrator
- Orchestrator consumes `project-profile.yaml` for project name and path resolution
- DR section mapping updated: I13 contributes to S12 and S5

---

## [0.4.0] — 2026-03-17

### Added
- `project-profile.schema.yaml` — single source of project-specific configuration
- `project-profile.example.yaml` — fully annotated example profile
- Profile validation in qualitoscope Phase 1

### Changed
- All 13 instrument configs centralised — project paths removed from individual
  `config.yaml` files, now read from `project-profile.yaml`
- Instruments reference profile values instead of hardcoded paths

---

## [0.3.0] — 2026-03-16

### Added
- Initial open-source release of qual-gate
- 13 domain scanning instruments (tomographes):
  ai-ml, architecture, code, compliance, data, dependency, deployment,
  documentation, observability, performance, security, test, ux
- Qualitoscope orchestrator with 8-phase scanning pipeline
- Unified severity scale (Critical, Major, Minor, Observation, OK)
- Output report templates for all instruments
- Apache 2.0 licence
