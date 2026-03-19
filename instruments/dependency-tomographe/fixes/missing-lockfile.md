---
title: "Fix: Missing Lockfile"
status: current
last-updated: 2026-03-19
instrument: dependency-tomographe
severity-range: "Major"
---

# Fix: Missing Lockfile

## What this means

The project has a dependency manifest (Cargo.toml, package.json, pyproject.toml, go.mod) but no
corresponding lockfile (Cargo.lock, package-lock.json, poetry.lock, go.sum). Without a lockfile,
dependency resolution is non-deterministic — different machines, CI runners, or build times may
resolve different dependency versions, leading to "works on my machine" failures, subtle behaviour
differences between environments, and inability to reproduce builds. This is a Major finding
because it undermines build reproducibility and makes security auditing unreliable.

## How to fix

### Rust

```bash
# Cargo.lock is generated automatically on first build
cargo build

# For libraries: Cargo.lock is conventionally gitignored.
# For applications/binaries: Cargo.lock MUST be committed.
# Check: is this a library or application?
grep -q '[[bin]]' Cargo.toml && echo "Application — commit Cargo.lock" \
  || echo "Library — Cargo.lock optional (but recommended for workspace roots)"
```

**Decision rule:** If the project produces a binary or deployable artifact, commit `Cargo.lock`.
If it is a library consumed by other projects, committing `Cargo.lock` is optional but
recommended for reproducible CI.

### Python

```bash
# Using Poetry
poetry lock

# Using pip-tools (for requirements.txt workflows)
pip-compile requirements.in -o requirements.txt
# requirements.txt with pinned versions acts as the lockfile

# Using PDM
pdm lock

# Using uv
uv lock
```

Commit the generated lockfile (`poetry.lock`, `requirements.txt`, `pdm.lock`, `uv.lock`).

### TypeScript / JavaScript

```bash
# npm
npm install   # generates package-lock.json

# yarn
yarn install  # generates yarn.lock

# pnpm
pnpm install  # generates pnpm-lock.yaml
```

Commit the generated lockfile. Never gitignore lockfiles for applications.

### Go

```bash
# go.sum is generated automatically
go mod tidy

# Verify
go mod verify
```

Commit both `go.mod` and `go.sum`.

### General

1. Generate the lockfile using the ecosystem's standard command.
2. Verify the project builds and tests pass with the locked versions.
3. Add the lockfile to version control.
4. Ensure `.gitignore` does not exclude the lockfile.
5. Update CI to install from the lockfile (see Prevention).

## Prevention

- **CI enforcement:** Configure CI to fail if the lockfile is missing or out of sync with the
  manifest.

  ```bash
  # Rust — verify lockfile is up to date
  cargo update --locked   # fails if Cargo.lock would change

  # Python (Poetry) — verify lockfile matches pyproject.toml
  poetry check --lock

  # Node (npm) — use ci install which requires lockfile
  npm ci                  # fails if package-lock.json is missing or outdated

  # Go — verify go.sum is complete
  go mod verify
  ```

- **Use `npm ci` / `yarn install --frozen-lockfile` / `pnpm install --frozen-lockfile`** in CI
  instead of `npm install`. The frozen variants fail if the lockfile is missing or outdated,
  preventing silent dependency drift.

- **Pre-commit hook:** Add a check that the lockfile exists and is committed. Flag new manifests
  without corresponding lockfiles.

- **Document the policy** in your contributing guide: "All dependency manifest changes must
  include an updated lockfile in the same commit."
