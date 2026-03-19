---
title: "Fix: Dead Code"
status: current
last-updated: 2026-03-19
instrument: code-tomographe
severity-range: "Minor"
---

# Fix: Dead Code

## What this means

Dead code is any code that exists in the repository but is never executed at runtime: unused
functions, unreachable branches, stale imports, commented-out blocks, and disabled feature flags.
Dead code increases cognitive load during reading and review, inflates compilation and test times,
and creates false confidence in test coverage metrics. It is typically Minor severity because it
does not cause runtime failures, but large accumulations signal neglected maintenance and should
be addressed before they obscure the code that actually matters.

## How to fix

### Python

**Detection:**

```bash
pip install vulture
vulture src/ --min-confidence 80
```

Vulture reports unused functions, classes, variables, and imports with a confidence score. Start
with `--min-confidence 80` to avoid false positives, then lower the threshold as you clean up.

**Handling false positives:**

```python
# vulture_whitelist.py -- list symbols that appear unused but are used dynamically
from mypackage.plugins import register_handler  # noqa: vulture
```

```bash
vulture src/ vulture_whitelist.py --min-confidence 80
```

**Safe removal workflow:**

```python
# Step 1: Confirm the function has no callers
# Search the entire codebase, including tests and scripts
# rg 'function_name' --type py

# Step 2: If unused, remove the function and its imports
# Step 3: Run the full test suite to confirm nothing breaks
# pytest tests/ -v

# Step 4: If the function was part of a public API, check for
# external consumers before removing. Deprecate first if needed.
```

**Stale imports (caught by ruff):**

```bash
ruff check --select F401 src/    # F401 = unused import
ruff check --select F401 --fix src/
```

### Rust

**Detection:**

The compiler itself warns on dead code. Ensure warnings are not suppressed:

```bash
# Find suppressed dead_code warnings that may be hiding unused code
grep -rn '#\[allow(dead_code)\]' src/
```

Audit every `#[allow(dead_code)]` annotation. Each one should have a comment explaining why
the code must exist despite having no current callers (e.g., "used by FFI", "reserved for
upcoming feature in issue #123").

**Unused dependencies:**

```bash
cargo install cargo-udeps
cargo +nightly udeps --workspace
```

**Safe removal workflow:**

```rust
// Step 1: Remove #[allow(dead_code)] and rebuild
// The compiler will tell you exactly what is unused.

// Step 2: For public items in a library crate, check if downstream
// crates depend on them before removing.

// Step 3: Remove the dead code and run:
// cargo test --workspace
// cargo clippy --workspace --all-targets
```

**Unused feature flags in Cargo.toml:**

```bash
# List all defined features
grep -A 20 '^\[features\]' Cargo.toml

# Search for cfg(feature = "...") usage
grep -rn 'cfg(feature' src/
```

If a feature is defined but never referenced in `cfg()` attributes, it is dead.

### TypeScript

**Detection:**

```bash
npx ts-prune
```

`ts-prune` lists exported symbols that are not imported anywhere in the project.

**Alternative with eslint:**

```json
{
  "rules": {
    "@typescript-eslint/no-unused-vars": "error",
    "no-unreachable": "error"
  }
}
```

**Safe removal workflow:**

```typescript
// Step 1: ts-prune output shows unused exports
// "src/utils/legacy.ts:5 - unusedHelper"

// Step 2: Verify the symbol is not used dynamically
// Search for string references: dynamic imports, reflection, tests
// rg 'unusedHelper' --type ts

// Step 3: Remove the export. If the entire file becomes empty,
// delete the file and remove it from any barrel exports (index.ts).

// Step 4: Run the build and tests
// npx tsc --noEmit && npm test
```

### Go

**Detection:**

```bash
go install honnef.co/go/tools/cmd/staticcheck@latest
staticcheck -checks U1000 ./...    # U1000 = unused code
```

The Go compiler already rejects unused imports and variables, but `staticcheck` catches unused
functions, methods, types, and struct fields.

**Safe removal workflow:**

```go
// Step 1: staticcheck reports unused symbols
// main.go:42:6: func legacyHandler is unused (U1000)

// Step 2: Search for dynamic usage (reflection, interface satisfaction)
// rg 'legacyHandler' --type go

// Step 3: Remove and verify
// go build ./... && go test ./...
```

### General

**Commented-out code:** Delete it. Version control preserves history. If you need it later,
`git log` will find it. Commented-out code is not a backup strategy -- it is clutter.

**Feature flag cleanup process:**

1. List all feature flags and their current state (enabled/disabled).
2. Any flag that has been permanently disabled for more than one release cycle is dead code.
3. Remove the flag, the conditional branch, and the configuration entry.
4. If the flag guards a partial implementation, create an issue to either complete or remove it.

**Stale TODO/FIXME references:** If a TODO references a function that no longer exists or an
issue that has been closed, remove the comment.

## Prevention

- Enable dead code warnings in CI. Do not allow `#[allow(dead_code)]` or `# noqa: F401`
  without an accompanying justification comment.
- Run `vulture` / `ts-prune` / `staticcheck` as a CI job. New dead code fails the pipeline.
- Feature flag inventory review: quarterly audit of all flags. Remove any permanently disabled.
- Pre-merge check: when removing a function's last caller, remove the function in the same MR.
- Track dead code count over time. It should trend toward zero, not accumulate.
