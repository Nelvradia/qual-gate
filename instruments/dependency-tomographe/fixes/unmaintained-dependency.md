---
title: "Fix: Unmaintained Dependency"
status: current
last-updated: 2026-03-19
instrument: dependency-tomographe
severity-range: "Major"
---

# Fix: Unmaintained Dependency

## What this means

A dependency has not received updates, bug fixes, or security patches for an extended period,
indicating that its maintainers have abandoned it or deprioritised it. Unmaintained dependencies
accumulate unpatched vulnerabilities, drift from ecosystem conventions, and eventually break
compatibility with newer compiler/runtime versions. This is a Major finding because you cannot
rely on upstream to fix security issues or bugs — the burden shifts entirely to your team.

### Staleness Criteria

| Signal | Threshold | Weight |
|--------|-----------|--------|
| Last commit | > 12 months | High |
| Last release | > 18 months | High |
| Open issues without maintainer response | > 50 unanswered | Medium |
| Deprecated flag on registry | Any | Critical |
| Archived repository | Any | Critical |
| Known unfixed CVE | Any | Critical |

A dependency meeting 2+ signals should be flagged for review.

## How to fix

### Step 1: Assess the dependency's actual status

Before replacing, confirm the dependency is truly unmaintained — some stable libraries receive
infrequent updates because they are feature-complete, not abandoned.

Check:
- Repository activity (commits, issue responses, PR reviews).
- Registry status (crates.io, PyPI, npm — look for deprecation notices).
- Security advisory databases (RustSec, GitHub Advisories, Snyk).
- Community activity (forks, downstream users, discussion forums).

### Step 2: Decision tree

```
Is the dependency deprecated or archived?
├─ Yes → Replace immediately (Step 3a)
└─ No
   ├─ Does it have unpatched CVEs?
   │  ├─ Yes → Replace or fork (Step 3a or 3b)
   │  └─ No
   │     ├─ Is it stable and feature-complete?
   │     │  ├─ Yes → Document acceptance, pin version, monitor (Step 3c)
   │     │  └─ No
   │     │     └─ Last commit > 18 months?
   │     │        ├─ Yes → Replace or fork (Step 3a or 3b)
   │     │        └─ No → Monitor, reassess in 6 months (Step 3c)
```

### Step 3a: Replace with an actively maintained alternative

Search the ecosystem registry for alternatives:

```bash
# Rust — search crates.io or lib.rs
# Check download trends and last-updated on lib.rs/crates/{name}

# Python — search PyPI
pip install <alternative>

# TypeScript/JavaScript — search npm
npm info <alternative>

# Go — search pkg.go.dev
```

When replacing:
1. Add the new dependency.
2. Update all import/use sites.
3. Run the full test suite.
4. Remove the old dependency from the manifest and lockfile.

### Step 3b: Fork and maintain internally

When no suitable alternative exists:

1. Fork the repository into your organisation's namespace.
2. Apply any pending security patches.
3. Update the manifest to point to your fork.
4. Assign an internal owner responsible for monitoring the original repo and applying patches.
5. Document the fork in your project's dependency decisions log.

#### Rust

```toml
# Cargo.toml — use a git dependency or path dependency for the fork
[dependencies]
unmaintained-crate = { git = "https://gitlab.example.com/forks/unmaintained-crate", branch = "main" }
```

#### Python

```toml
# pyproject.toml — use a git dependency
[tool.poetry.dependencies]
unmaintained-pkg = { git = "https://gitlab.example.com/forks/unmaintained-pkg.git", branch = "main" }
```

### Step 3c: Accept and monitor

If the dependency is stable and low-risk:

1. Pin to the exact current version in your lockfile.
2. Document the acceptance decision and review date.
3. Set a calendar reminder to reassess in 6 months.
4. Subscribe to security advisories for the dependency.

## Prevention

- Run dependency health checks in CI (see ecosystem tools below).
- Review dependency health as part of every MR that adds a new dependency.
- Schedule quarterly dependency audits — check maintenance status, not just CVEs.
- Subscribe to security advisory feeds: RustSec, GitHub Advisories, Snyk, OSV.
- Prefer dependencies with multiple maintainers and active contributor communities.

### Monitoring tools

| Ecosystem | Tool | What it checks |
|-----------|------|----------------|
| Rust | `cargo audit` | RustSec advisories |
| Rust | `cargo deny check advisories` | Advisories + unmaintained crate warnings |
| Python | `pip-audit` | PyPI advisories (OSV) |
| Node | `npm audit` | npm advisories |
| Go | `govulncheck` | Go vulnerability database |
| All | Dependabot / Renovate | Automated update PRs + vulnerability alerts |
