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

## [Unreleased] — v0.6.0-dev

### Added
- Remediation library: fix guides for all 13 instruments with per-language code examples
- Fixes content standard (`instruments/fixes-content-standard.md`)
- Getting-started guide (`docs/getting-started.md`)
- Project profile field reference (`docs/project-profile-reference.md`)
- Instrument authoring guide (`docs/instrument-authoring-guide.md`)
- This CHANGELOG

### Changed
- Root README updated with "How to Run" section and documentation links
- ROADMAP version milestones reconciled with actual delivery

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
