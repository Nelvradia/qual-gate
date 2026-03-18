---
title: Dependency Health Checklist
status: current
last-updated: 2026-03-17
---

# Dependency Health Checklist

Used in Phase 4 — Dependency Health and Phase 5 — Version & Pinning Discipline.

## Maintenance Status

- [ ] No direct dependency flagged as `unmaintained` or `deprecated` in its registry or advisory database
- [ ] No direct dependency with no release activity in >2 years
- [ ] No direct dependency version that has been yanked or retracted from its registry
- [ ] No direct dependency sourced from a git commit reference instead of a registry version

## Lockfile & Pinning

- [ ] Every application manifest has a committed lockfile
- [ ] Lockfile is up to date with the manifest (no drift between declared and resolved versions)
- [ ] No wildcard (`*`) version constraints in any manifest
- [ ] No unbounded upward ranges (`>=1.0` with no ceiling) in application manifests
- [ ] No direct dependency more than 2 major versions behind the current release

## Provenance

- [ ] All dependencies sourced from a public registry with known, auditable releases
- [ ] No packages with a history of ownership transfers (check for flag in advisory databases)
- [ ] Build-time code-executing dependencies (code generators, preprocessors, annotation processors) are pinned to an exact version
