---
title: Supply Chain & Transitive Risk Checklist
status: current
last-updated: 2026-03-17
---

# Supply Chain & Transitive Risk Checklist

Used in Phase 6 — Transitive Risk.

## Vendored Code

- [ ] All vendored / embedded third-party code is listed in the attribution file
- [ ] Every vendored directory contains an original LICENSE file
- [ ] Vendored code is tracked in the manifest/lockfile (not just copied in without a reference)
- [ ] A documented update strategy exists for each vendored dependency (how will CVEs be picked up?)

## Diamond Conflicts

- [ ] No diamond conflict on any security-relevant package (cryptography, TLS, authentication, serialisation)
- [ ] Diamond conflicts that do exist are documented and understood (which version wins, and why is that safe)

## Build-Time Execution Surface

- [ ] Every dependency that executes code at build time (build scripts, macros, code generators, annotation processors) is pinned to an exact version
- [ ] Build-time dependencies come from the same trusted registry as runtime dependencies
- [ ] Any new build-time dep was reviewed for unusual permissions, network access, or filesystem access

## SBOM

- [ ] A machine-readable SBOM exists (CycloneDX or SPDX format) or is generated on release
- [ ] The SBOM covers all ecosystems present in the project
- [ ] The SBOM is updated on every release or dependency change
