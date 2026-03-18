---
title: Licence Risk Checklist
status: current
last-updated: 2026-03-17
---

# Licence Risk Checklist

Used in Phase 3 — Licence Risk Matrix.

## Copyleft Contamination

- [ ] No AGPL-3.0 dependency anywhere in a networked service (SaaS is not exempt)
- [ ] No GPL-2.0 or GPL-3.0 dependency statically linked into a distributed binary
- [ ] No SSPL-1.0 dependency in any service exposed via an API
- [ ] No Commons Clause or BUSL-1.1 dependency used in commercial production
- [ ] No unknown / no-licence dependency in any form

## Weak Copyleft Strategy

- [ ] Every LGPL dependency has a documented linking strategy (dynamic linking or source offer)
- [ ] Every MPL-2.0 dependency that has been modified has a disclosure plan for those file modifications
- [ ] EUPL / CDDL dependencies reviewed and linking strategy documented

## Compatibility

- [ ] No Apache-2.0 + GPL-2.0 combination in the same binary (incompatible — patent clause conflicts)
- [ ] All licence pairs in the same binary are legally compatible

## Attribution

- [ ] An attribution file exists (NOTICE, NOTICE.md, or ATTRIBUTION.md)
- [ ] Every permissive dependency (MIT, Apache-2.0, BSD) is listed in the attribution file
- [ ] Every vendored dependency has its original LICENSE file present

## Commercial / Financial Obligations

- [ ] All BUSL-1.1 deps checked for Change Date — current date before Change Date means commercial licence required
- [ ] Dual-licensed deps confirm permissive tier is in use (or commercial licence purchased)
- [ ] Font / asset licences checked — OFL permits embedding; CC-NC does not permit commercial use
- [ ] No SIL OFL font licences violated (permitted to embed, not to sell the font standalone)
