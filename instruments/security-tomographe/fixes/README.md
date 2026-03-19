---
title: "Security Tomographe — Fix Guide Index"
status: current
last-updated: 2026-03-19
---

# Security Tomographe — Fix Guide Index

Actionable fix guides for findings raised by the `security-tomographe` instrument. Each guide
includes language-specific code examples (Python, Rust, TypeScript, Go) and CI-enforceable
prevention measures.

Sorted by severity (Critical first).

## Critical

| Finding Category | File | Severity |
|---|---|---|
| Hardcoded Secrets | [hardcoded-secrets.md](hardcoded-secrets.md) | Critical |
| Known CVE in Dependency | [known-cve-in-dependency.md](known-cve-in-dependency.md) | Critical |

## Critical–Major

| Finding Category | File | Severity Range |
|---|---|---|
| Missing Input Validation | [missing-input-validation.md](missing-input-validation.md) | Critical–Major |
| Unauthenticated Endpoint | [unauthenticated-endpoint.md](unauthenticated-endpoint.md) | Critical–Major |

## Major–Critical

| Finding Category | File | Severity Range |
|---|---|---|
| Insecure Key Storage | [insecure-key-storage.md](insecure-key-storage.md) | Major–Critical |
| Missing TLS | [missing-tls.md](missing-tls.md) | Major–Critical |

## Major

| Finding Category | File | Severity Range |
|---|---|---|
| Container Running as Root | [container-running-as-root.md](container-running-as-root.md) | Major |
| Missing Rate Limiting | [missing-rate-limiting.md](missing-rate-limiting.md) | Major |
