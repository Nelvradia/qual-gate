---
title: "Fix: Excessive Transitive Dependencies"
status: current
last-updated: 2026-03-19
instrument: dependency-tomographe
severity-range: "Minor–Major"
---

# Fix: Excessive Transitive Dependencies

## What this means

The project's dependency tree is significantly larger than expected for its direct dependency count.
A small number of direct dependencies pulling in hundreds of transitive dependencies increases
build times, expands the supply chain attack surface, complicates licence auditing, and makes
security scanning slower and noisier. Severity ranges from Minor (moderately inflated tree) to
Major (dependency tree >10x the direct count, or transitive deps with known vulnerabilities).

## How to fix

### Step 1: Visualise the dependency tree

#### Rust

```bash
# Full tree
cargo tree

# Count total unique crates
cargo tree --depth 999 --prefix none | sort -u | wc -l

# Find which direct deps bring the most transitive deps
cargo tree --depth 1 --edges normal | while read -r line; do
  dep=$(echo "$line" | sed 's/ .*//')
  count=$(cargo tree -p "$dep" --prefix none 2>/dev/null | sort -u | wc -l)
  echo "$count $dep"
done | sort -rn | head -10

# Find duplicate crate versions
cargo tree --duplicates
```

#### Python

```bash
# Using pipdeptree
pip install pipdeptree
pipdeptree --warn silence

# Count total packages
pip list --format=columns | tail -n +3 | wc -l
```

#### TypeScript / JavaScript

```bash
# Full tree
npm ls --all

# Count total packages
npm ls --all --parseable | wc -l

# Find heaviest direct deps
npx howfat <package-name>
```

#### Go

```bash
# Full module graph
go mod graph

# Count unique modules
go mod graph | awk '{print $2}' | sort -u | wc -l
```

### Step 2: Identify reduction opportunities

1. **Duplicate versions:** Multiple versions of the same crate/package in the tree. Resolve by
   aligning version constraints across direct dependencies.
2. **Feature bloat (Rust):** Dependencies pulled in with default features that include
   unnecessary sub-dependencies. Disable with `default-features = false`.
3. **Heavy alternatives:** A direct dependency that pulls in 50+ transitive deps may have a
   lighter alternative that covers your actual use case.
4. **Unused transitive features:** Some ecosystems allow pruning features you don't use.

### Step 3: Reduce the tree

#### Rust — disable default features

```toml
# Before: pulls in tokio, hyper, tower, etc.
[dependencies]
reqwest = "0.12"

# After: only what you need
[dependencies]
reqwest = { version = "0.12", default-features = false, features = ["rustls-tls", "json"] }
```

#### Rust — resolve duplicates

```bash
# Find duplicates
cargo tree --duplicates

# Update constraints to align versions
cargo update -p <crate-name>
```

#### Node — replace heavy packages

```bash
# Example: replace moment.js (large) with dayjs (small, compatible API)
npm uninstall moment
npm install dayjs

# Example: replace lodash (full) with individual lodash functions
npm uninstall lodash
npm install lodash.get lodash.set  # only what you use
```

#### Python — use minimal extras

```toml
# pyproject.toml — only install needed extras
[tool.poetry.dependencies]
sqlalchemy = { version = "^2.0", extras = [] }  # no optional drivers
```

#### General — consider vendoring

For critical dependencies where you need full control over the supply chain:

```bash
# Rust
cargo vendor

# Go (vendoring is built-in)
go mod vendor
```

Vendoring trades disk space for supply chain control — the vendored code is auditable,
reproducible, and immune to registry outages or package removal.

## Prevention

- **Set a dependency budget:** Define a maximum transitive dependency count for the project.
  Track it in CI and fail if the count increases beyond the budget without explicit approval.
- **Review dependency trees in MRs:** When adding a new dependency, run `cargo tree -p <dep>` /
  `npm ls <dep>` and include the transitive count in the MR description.
- **Prefer minimal dependencies:** Choose libraries that minimise their own dependency trees.
  Check transitive counts before adopting.
- **Periodically audit:** Run dependency tree analysis quarterly. Remove or replace deps whose
  transitive trees have grown significantly.
- **Use feature flags:** In Rust, always evaluate `default-features = false` for new
  dependencies. Enable only the features you actually use.
