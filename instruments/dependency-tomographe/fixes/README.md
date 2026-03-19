---
title: "Dependency Tomographe — Fix Guide Index"
status: current
last-updated: 2026-03-19
---

# Dependency Tomographe — Fix Guide Index

Actionable fix guides for findings raised by the `dependency-tomographe` instrument. Each guide
includes language-specific remediation steps (Rust, Python, TypeScript, Go) and CI-enforceable
prevention measures.

Sorted by severity (Critical first).

## Major–Critical

| Finding Category | File | Severity Range |
|---|---|---|
| Licence Risk | [licence-risk.md](licence-risk.md) | Major–Critical |

## Major

| Finding Category | File | Severity Range |
|---|---|---|
| Unmaintained Dependency | [unmaintained-dependency.md](unmaintained-dependency.md) | Major |
| Missing Lockfile | [missing-lockfile.md](missing-lockfile.md) | Major |

## Minor–Major

| Finding Category | File | Severity Range |
|---|---|---|
| Unused Dependencies | [unused-dependencies.md](unused-dependencies.md) | Minor–Major |
| Excessive Transitive Dependencies | [excessive-transitive-deps.md](excessive-transitive-deps.md) | Minor–Major |
