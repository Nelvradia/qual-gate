---
title: "Fix: Unused Dependencies"
status: current
last-updated: 2026-03-19
instrument: dependency-tomographe
severity-range: "Minor–Major"
---

# Fix: Unused Dependencies

## What this means

The project declares dependencies in its manifest (Cargo.toml, package.json, pyproject.toml,
go.mod) that are never imported or used in the source code. Unused dependencies increase build
times, expand the attack surface (each dependency is a potential supply chain vector), bloat
container images, and make auditing harder. Severity escalates from Minor (one or two unused
dev-dependencies) to Major (multiple unused runtime dependencies, especially those with known
CVE history or large transitive trees).

## How to fix

### Rust

```bash
# Install cargo-machete (one-time)
cargo install cargo-machete

# Detect unused dependencies
cargo machete

# Auto-remove detected unused deps (review the diff before committing)
cargo machete --fix

# Verify the project still builds and tests pass
cargo test --workspace
```

If `cargo-machete` flags a dependency that is used only via a proc macro or `build.rs`, add it
to `.cargo-machete.toml`:

```toml
# .cargo-machete.toml
ignored = ["proc-macro-crate"]
```

### Python

```bash
# Using pip-autoremove (for pip-managed projects)
pip install pip-autoremove
pip-autoremove --list     # preview what would be removed

# Using deptry (recommended for pyproject.toml projects)
pip install deptry
deptry .                  # reports unused and missing deps
# Then manually remove flagged packages from pyproject.toml

# Verify
pytest tests/ -v
```

### TypeScript / JavaScript

```bash
# Using depcheck
npx depcheck

# Review output, then remove unused packages
npm uninstall <package-name>
# or
yarn remove <package-name>

# Verify
npm test
```

### Go

```bash
# Go modules handle this natively
go mod tidy

# Verify nothing broke
go test ./...
```

### General

For any ecosystem:

1. Run the ecosystem's unused-dependency detection tool.
2. Review each flagged dependency — some may be used only at build time, in optional features,
   or through dynamic dispatch that static analysis cannot see.
3. Remove confirmed unused dependencies from the manifest.
4. Run the full test suite to verify nothing breaks.
5. Commit the manifest and lockfile changes together.

## Prevention

- Add unused-dependency detection to CI. Run `cargo machete` / `depcheck` / `deptry` / `go mod
  tidy -diff` as a lint-stage job that fails on findings.
- Review dependency additions in MRs — every new dependency should justify its inclusion.
- Periodically audit the dependency list (quarterly at minimum).
