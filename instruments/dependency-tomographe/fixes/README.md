---
title: Auto-fixable Dependency Findings
status: current
last-updated: 2026-03-17
---

# Auto-fixable Findings

Some findings from the dependency-tomographe can be resolved automatically. These should only be run after human review of the proposed changes.

## Remove unused dependencies

```bash
# Rust — cargo-machete can remove unused deps automatically
cargo machete --fix 2>/dev/null
# Always review the diff before committing

# Node — no standard auto-remove; depcheck suggests removals, apply manually
npx depcheck 2>/dev/null
# then: npm uninstall <package>

# Python — pip-autoremove can remove unused packages (interactive)
pip-autoremove 2>/dev/null
```

## Update outdated dependencies

```bash
# Rust — update all within semver constraints
cargo update 2>/dev/null
# Or update a specific package to latest compatible:
cargo update -p <package>

# Node
npm update 2>/dev/null
# Upgrade beyond semver constraints (review carefully):
npx npm-check-updates -u 2>/dev/null && npm install

# Python (with pip-tools)
pip-compile --upgrade 2>/dev/null

# Go
go get -u ./... 2>/dev/null && go mod tidy
```

## Regenerate lockfile

```bash
# Rust
cargo update 2>/dev/null   # regenerates Cargo.lock

# Node
rm package-lock.json && npm install

# Python (poetry)
poetry update 2>/dev/null

# Go
go mod tidy 2>/dev/null
```

## Add missing attribution entries

After establishing which permissive deps are missing from the attribution file, append entries manually — there is no safe automated tool for this. Each entry must accurately reflect the package name, version, licence, and copyright holder.
