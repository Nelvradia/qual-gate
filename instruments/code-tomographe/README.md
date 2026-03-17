# code-tomographe

**Code quality and maintainability scanner for the target project.** Audits linting, formatting, complexity, dead code, duplication, and technical debt. Complements the architecture-tomographe (which focuses on architecture/patterns) by focusing on code-level health.

**Covers DR Sections:** S3 (Code), S13 (Maintainability & Technical Debt)

---

## Quick Start

```bash
"Read instruments/code-tomographe/README.md and execute a full code quality scan."
"Read instruments/code-tomographe/README.md and execute Phase 2 (Complexity) only."
```

---

## Scan Phases

| Phase | Name | What It Does | Tools |
|-------|------|-------------|-------|
| **1** | Formatting & Linting | Verify code style compliance and catch warnings | `cargo fmt`, `cargo clippy`, `eslint`, `ktlint` |
| **2** | Complexity | Measure cyclomatic/cognitive complexity, identify hot functions | Custom grep, LLM analysis |
| **3** | Dead Code | Detect unused functions, unreachable paths, stale imports | `cargo clippy`, `grep`, LLM analysis |
| **4** | Duplication | Find copy-pasted code blocks across modules | Structural comparison, grep |
| **5** | Technical Debt | Inventory TODOs/FIXMEs/HACKs, instrument violations, ADR backlogs | `grep`, instrument output |
| **6** | Dependency Health | Audit dependency freshness, size, and necessity | `cargo tree`, `cargo bloat`, `npm ls` |
| **7** | Report | Compile findings with debt quantification | Template filling |

---

## Phase 1 — Formatting & Linting

**Goal:** Verify all code passes style gates.

### Rust

```bash
# Format check (should match CI gate)
cargo fmt --all --check 2>&1 | tee instruments/code-tomographe/output/fmt-check.txt
FMT_VIOLATIONS=$(cargo fmt --all --check 2>&1 | grep 'Diff in' | wc -l)

# Clippy (all targets, deny warnings for strictness check)
cargo clippy --workspace --all-targets 2>&1 | tee instruments/code-tomographe/output/clippy.txt
CLIPPY_WARNINGS=$(grep -c 'warning\[' instruments/code-tomographe/output/clippy.txt 2>/dev/null || echo 0)
CLIPPY_ERRORS=$(grep -c 'error\[' instruments/code-tomographe/output/clippy.txt 2>/dev/null || echo 0)

# Unsafe code audit
grep -rn 'unsafe' src/ --include='*.rs' | grep -v '// SAFETY:' | wc -l
# Every unsafe block should have a // SAFETY: justification comment
```

### TypeScript

```bash
cd apps/desktop
npx eslint src/ --format json 2>/dev/null > ../../instruments/code-tomographe/output/eslint.json
npx tsc --noEmit 2>&1 | tee ../../instruments/code-tomographe/output/tsc-check.txt
cd ../..
```

### Kotlin

```bash
# If ktlint available
cd apps/android
./gradlew ktlintCheck 2>&1 | tee ../../instruments/code-tomographe/output/ktlint.txt 2>/dev/null
cd ../..
# Fallback: check for obvious style issues
grep -rn 'var ' apps/android/ --include='*.kt' | grep -v 'val\|override\|private var' | wc -l
# Mutable state should be minimized in Compose
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| `cargo fmt` failures (CI should catch) | **Major** (if CI not blocking) / **OK** (if CI blocks) |
| Clippy errors | **Major** |
| Clippy warnings >20 | **Minor** |
| Clippy warnings >50 | **Major** |
| Unsafe block without SAFETY comment | **Minor** |
| TypeScript type errors | **Major** |
| ESLint errors | **Minor** |

---

## Phase 2 — Complexity

**Goal:** Identify overly complex functions that are hard to test, review, and maintain.

### Steps

```bash
# Function length analysis (Rust)
# Find functions longer than 50 lines
grep -n 'pub fn \|pub async fn \|fn ' src/ -r --include='*.rs' | while read line; do
  file=$(echo "$line" | cut -d: -f1)
  linenum=$(echo "$line" | cut -d: -f2)
  funcname=$(echo "$line" | sed 's/.*fn \([a-z_]*\).*/\1/')
  # Count lines until next fn or closing brace at column 0
  # (heuristic — exact requires AST parsing)
  echo "$file:$linenum:$funcname"
done > instruments/code-tomographe/output/function-list.txt

# Long functions (>50 lines — heuristic via brace counting)
# This is approximate; Claude Code can do better with LLM analysis
awk '/^[[:space:]]*pub (async )?fn / { start=NR; name=$0 }
     /^}$/ && start { len=NR-start; if(len>50) print FILENAME":"start":"name" ("len" lines)"; start=0 }
    ' src/**/*.rs 2>/dev/null

# Nesting depth analysis
# Find deeply nested code (>4 levels of indentation)
grep -rn '                    ' src/ --include='*.rs' | \
  grep -v '^\s*//' | grep -v '^\s*\*' | head -20

# Match arms count (complex match statements)
grep -c 'match ' src/**/*.rs 2>/dev/null | awk -F: '$2 > 5 {print}'
```

### Complexity Checklist

- [ ] No function exceeds 80 lines (soft limit: 50)
- [ ] No function has >4 levels of nesting
- [ ] Match statements have <15 arms (otherwise consider refactoring)
- [ ] No file exceeds 500 lines (soft limit: 300)
- [ ] Handler functions in `api/` are thin (delegate to service layer)

### Severity Rules

| Finding | Severity |
|---------|----------|
| Function >100 lines | **Major** |
| Function 50-100 lines | **Minor** |
| File >800 lines | **Major** |
| File 500-800 lines | **Minor** |
| Nesting >5 levels | **Minor** |

---

## Phase 3 — Dead Code

**Goal:** Detect code that exists but is never called.

### Steps

```bash
# Clippy dead code detection (requires nightly for some lints)
cargo clippy --workspace -- -W dead_code 2>&1 | grep 'dead_code' | head -20

# Unused imports
cargo clippy --workspace -- -W unused_imports 2>&1 | grep 'unused_import' | head -20

# Public functions not called from outside their module
# Heuristic: find pub fn definitions, search for their usage
grep -rn 'pub fn \|pub async fn ' src/ --include='*.rs' | \
  sed 's/.*pub \(async \)\?fn \([a-z_]*\).*/\2/' | sort -u | while read fn; do
  count=$(grep -rn "\b$fn\b" src/ --include='*.rs' | grep -v 'pub.*fn ' | wc -l)
  if [ "$count" -le 1 ]; then
    echo "POTENTIALLY_DEAD: $fn (used $count times outside definition)"
  fi
done 2>/dev/null | head -30

# Stale feature flags / cfg attributes
grep -rn '#\[cfg(' src/ --include='*.rs' | grep -v 'test\|target' | head -10

# Python dead code
grep -rn 'def ' src/ --include='*.py' | sed 's/.*def \([a-z_]*\).*/\1/' | sort -u | while read fn; do
  count=$(grep -rn "\b$fn\b" src/ tests/ --include='*.py' | grep -v 'def ' | wc -l)
  if [ "$count" -eq 0 ]; then
    echo "POTENTIALLY_DEAD: $fn"
  fi
done 2>/dev/null | head -20
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Confirmed dead public function | **Minor** |
| Entire unused module | **Minor** |
| Unused import (should be caught by CI) | **Observation** |
| Stale feature flag | **Observation** |

---

## Phase 4 — Duplication

**Goal:** Find copy-pasted code that should be extracted into shared functions.

### Steps

```bash
# Find similar function signatures across modules
grep -rn 'pub fn \|pub async fn ' src/ --include='*.rs' | \
  sed 's/.*fn \([a-z_]*\)(\(.*\)).*$/\1|\2/' | sort | uniq -d

# Find repeated SQL patterns
grep -rn 'SELECT\|INSERT\|UPDATE\|DELETE' src/db/ --include='*.rs' | \
  sed 's/.*"\(.*\)".*/\1/' | sort | uniq -c | sort -rn | head -10

# Find repeated error handling patterns
grep -rn 'map_err\|unwrap_or\|expect(' src/ --include='*.rs' | \
  sed 's/.*\(map_err.*\|unwrap_or.*\|expect(.*\)/\1/' | sort | uniq -c | sort -rn | head -10

# Find similar struct definitions
grep -rn 'pub struct ' src/ --include='*.rs' | head -30
# Look for structs with very similar fields (manual/LLM review)
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| >3 identical code blocks (>10 lines each) | **Minor** |
| Duplicated SQL queries (should use shared query builder) | **Observation** |
| Duplicated error handling (should use error module) | **Observation** |

---

## Phase 5 — Technical Debt

**Goal:** Inventory and quantify known technical debt.

### Steps

```bash
# TODO/FIXME/HACK inventory
echo "=== TODOs ==="
grep -rn 'TODO\|FIXME\|HACK\|XXX\|TEMP\|WORKAROUND' \
  src/ --include='*.rs' --include='*.ts' --include='*.kt' --include='*.py' | wc -l

# Per-category breakdown
for tag in TODO FIXME HACK XXX TEMP WORKAROUND; do
  count=$(grep -rn "$tag" src/ \
    --include='*.rs' --include='*.ts' --include='*.kt' --include='*.py' 2>/dev/null | wc -l)
  echo "$tag: $count"
done

# Age of TODOs (how long have they existed?)
grep -rn 'TODO\|FIXME' src/ --include='*.rs' | while read line; do
  file=$(echo "$line" | cut -d: -f1)
  linenum=$(echo "$line" | cut -d: -f2)
  age=$(git log -1 --format="%ar" -L "$linenum,$linenum:$file" 2>/dev/null | head -1)
  echo "$line — age: ${age:-unknown}"
done 2>/dev/null | head -20

# Instrument violations (read from existing output)
cat output/*/AR*-architecture.md 2>/dev/null || echo "No architecture instrument output found"

# ADR backlog (decisions marked as pending/revisit)
grep -rn 'Status: Pending\|Status: Revisit\|revisit_condition' .claude/decisions/ 2>/dev/null | wc -l
```

### Debt Quantification

| Debt Category | Items | Estimated Hours | Priority |
|---|---|---|---|
| TODOs/FIXMEs | count | count x 0.5h avg | P2-P3 |
| Instrument violations | count | from Quick Wins section | P1-P3 |
| ADR revisit items | count | varies | P2 |
| Long functions needing refactor | count | count x 2h avg | P2 |
| Dead code to remove | count | count x 0.5h avg | P3 |

---

## Phase 6 — Dependency Health

**Goal:** Audit dependencies for freshness, bloat, and necessity.

### Steps

```bash
# Dependency count
echo "Rust direct deps: $(grep -c '^\[dependencies' Cargo.toml 2>/dev/null || cargo metadata --format-version 1 2>/dev/null | jq '.packages | length')"

# Outdated Rust dependencies
cargo outdated 2>/dev/null | head -20

# Dependency tree depth
cargo tree --depth 1 2>/dev/null | wc -l

# Binary size contributors (if cargo-bloat available)
cargo bloat --release --crates 2>/dev/null | head -15

# Node dependency count
cd apps/desktop && echo "Node deps: $(cat package.json | grep -c '\":')" && cd ../..

# Unused dependencies (heuristic)
cargo machete 2>/dev/null || echo "cargo-machete not available"
```

---

## Phase 7 — Report

Compile into `output/YYYY-MM-DD/CQ{n}-code.md`.

---

## Configuration

```yaml
thresholds:
  fmt_violations: 0
  clippy_warnings_max: 20
  clippy_errors_max: 0
  function_length_soft: 50
  function_length_hard: 100
  file_length_soft: 300
  file_length_hard: 800
  nesting_max: 5
  todo_count_warning: 20
  todo_count_major: 50
  fixme_count_warning: 5
  dead_functions_max: 10
  duplication_threshold: 3

scope:
  rust_dirs: [src/]
  ts_dirs: [apps/desktop/src/]
  kotlin_dirs: [apps/android/]
  exclude: [vendor/, target/, node_modules/, build/]
```

---

## Run History

| Run | Date | Trigger | Report |
|-----|------|---------|--------|
| CQ1 | _pending_ | Initial baseline | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
