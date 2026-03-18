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
| **1** | Formatting & Linting | Verify code style compliance and catch warnings | LLM analysis + optional tooling |
| **2** | Complexity | Measure cyclomatic/cognitive complexity, identify hot functions | LLM analysis + optional tooling |
| **3** | Dead Code | Detect unused functions, unreachable paths, stale imports | LLM analysis + optional tooling |
| **4** | Duplication | Find copy-pasted code blocks across modules | LLM analysis + optional tooling |
| **5** | Technical Debt | Inventory TODOs/FIXMEs/HACKs, instrument violations, ADR backlogs | LLM analysis + optional tooling |
| **6** | Dependency Health | See dependency-tomographe | — |
| **7** | Report | Compile findings with debt quantification | Template filling |

---

## Phase 1 — Formatting & Linting

**Goal:** Verify all code passes style gates.

### LLM steps

1. Discover what formatters and linters are configured in the project by reading relevant config files. Look for: `.rustfmt.toml`, `.clippy.toml`, `pyproject.toml` (sections `[tool.ruff]` or `[tool.flake8]`), `.eslintrc*`, `.eslintignore`, `tsconfig.json`, `.clang-format`, `.clang-tidy`, `.golangci.yml`, `ktlint.yml`, `.prettierrc`, `.stylelintrc`, or equivalent. Note the configured line length limit and any rules that deviate from defaults.
2. For each formatter or linter found, read the source files in scope and assess whether they would pass. Look for obvious style violations: inconsistent indentation, trailing whitespace, lines exceeding the project's configured length limit, missing or misplaced blank lines, and import ordering that violates the project's rules.
3. Identify any unsafe or high-risk patterns without justification comments. This is language-specific: `unsafe` blocks in Rust must have a `// SAFETY:` comment; raw pointer arithmetic and manual memory management in C/C++ must be annotated; `eval()`, `exec()`, and dynamic code execution in Python or JavaScript must have a clear comment explaining why it is necessary.

### Accelerator tools (optional)

```bash
# Rust (if cargo is available)
cargo fmt --all --check 2>&1 | tee output/YYYY-MM-DD_{project_name}/scratch/code-tomographe/fmt-check.txt
FMT_VIOLATIONS=$(cargo fmt --all --check 2>&1 | grep 'Diff in' | wc -l)
cargo clippy --workspace --all-targets 2>&1 | tee output/YYYY-MM-DD_{project_name}/scratch/code-tomographe/clippy.txt
LINTER_WARNINGS=$(grep -c 'warning\[' output/YYYY-MM-DD_{project_name}/scratch/code-tomographe/clippy.txt 2>/dev/null || echo 0)
LINTER_ERRORS=$(grep -c 'error\[' output/YYYY-MM-DD_{project_name}/scratch/code-tomographe/clippy.txt 2>/dev/null || echo 0)
# Unsafe blocks without SAFETY justification
grep -rn 'unsafe' src/ --include='*.rs' | grep -v '// SAFETY:' | wc -l

# TypeScript/JavaScript (if Node is available)
npx eslint src/ --format json 2>/dev/null > output/YYYY-MM-DD_{project_name}/scratch/code-tomographe/eslint.json
npx tsc --noEmit 2>&1 | tee output/YYYY-MM-DD_{project_name}/scratch/code-tomographe/tsc-check.txt

# Kotlin (if ktlint is available)
./gradlew ktlintCheck 2>&1 | tee output/YYYY-MM-DD_{project_name}/scratch/code-tomographe/ktlint.txt
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Formatter violations (CI should catch) | **Major** (if CI not blocking) / **OK** (if CI blocks) |
| Linter errors | **Major** |
| Linter warnings >20 | **Minor** |
| Linter warnings >50 | **Major** |
| Unsafe/high-risk block without justification comment | **Minor** |

---

## Phase 2 — Complexity

**Goal:** Identify overly complex functions that are hard to test, review, and maintain.

### LLM steps

1. Read all source files in scope.
2. For each function or method, estimate its length in lines and its nesting depth by reading the code directly. Count indentation levels: each nested block (conditional, loop, match arm, callback, try/catch) adds one level.
3. Flag functions that appear to do too many things — multiple unrelated responsibilities in a single body, deeply nested control flow (more than 4 levels), or excessive length. These are universal complexity indicators regardless of language.

### Accelerator tools (optional)

```bash
# Rust (if cargo is available)
# Long functions — heuristic via brace counting
awk '/^[[:space:]]*pub (async )?fn / { start=NR; name=$0 }
     /^}$/ && start { len=NR-start; if(len>50) print FILENAME":"start":"name" ("len" lines)"; start=0 }
    ' src/**/*.rs 2>/dev/null

# Nesting depth — lines with >4 levels of indentation (adjust spaces per project style)
grep -rn '                    ' src/ --include='*.rs' | grep -v '^\s*//' | grep -v '^\s*\*' | head -20

# Python (if radon is available)
radon cc -s src/

# Go (if gocyclo is available)
gocyclo ./...

# JavaScript/TypeScript (if Node is available)
npx complexity-report src/
```

### Complexity Checklist

- [ ] No function exceeds 80 lines (soft limit: 50)
- [ ] No function has >4 levels of nesting
- [ ] No file exceeds 500 lines (soft limit: 300)
- [ ] Handler/controller functions are thin (delegate to service layer)

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

### LLM steps

1. Read all source files and build a list of declared public functions, methods, classes, and modules.
2. Search for references to each symbol across the entire codebase. If a public symbol is defined but never referenced outside its own file or test files, flag it as potentially dead.
3. Look for commented-out code blocks — these are a language-agnostic indicator of dead code that has not been formally removed.
4. Look for conditional branches that are always true or always false due to hardcoded values or constants (e.g., `if DEBUG_MODE:` where `DEBUG_MODE = False` is never overridden, feature flags that are always disabled).

### Accelerator tools (optional)

```bash
# Rust (if cargo is available)
cargo clippy --workspace -- -W dead_code 2>&1 | grep 'dead_code' | head -20
cargo clippy --workspace -- -W unused_imports 2>&1 | grep 'unused_import' | head -20

# Python (if vulture is available)
vulture src/

# TypeScript (if ts-prune is available)
npx ts-prune
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

### LLM steps

1. Read source files and identify structurally similar functions: same parameter shapes, same logic patterns, similar SQL queries, similar error handling boilerplate. Duplication is a structural problem — this analysis applies to any language.
2. Flag blocks of more than 10 lines that appear copy-pasted with only variable name changes. These are extraction candidates regardless of language.

### Accelerator tools (optional)

```bash
# Cross-language (if jscpd is available — works across most languages)
jscpd --min-lines 10 .

# Rust — similar function signatures across modules
grep -rn 'pub fn \|pub async fn ' src/ --include='*.rs' | \
  sed 's/.*fn \([a-z_]*\)(\(.*\)).*$/\1|\2/' | sort | uniq -d

# Rust — repeated SQL patterns
grep -rn 'SELECT\|INSERT\|UPDATE\|DELETE' src/ --include='*.rs' | \
  sed 's/.*"\(.*\)".*/\1/' | sort | uniq -c | sort -rn | head -10
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

### LLM steps

1. Search all source files for debt marker comments: `TODO`, `FIXME`, `HACK`, `XXX`, `TEMP`, `WORKAROUND`. For each occurrence, note the file, a summary of what it says, and whether a date or issue reference is present.
2. Cross-reference with the output of other instrument phases — unresolved findings from previous scans are also debt and should be included in the inventory.
3. Assess whether the ADR backlog in `.claude/decisions/` contains any items with `Status: Pending` or `Status: Revisit`. These represent deferred architectural decisions that carry ongoing risk.

### Accelerator tools (optional)

```bash
# Debt marker inventory
echo "=== TODOs ==="
grep -rn 'TODO\|FIXME\|HACK\|XXX\|TEMP\|WORKAROUND' src/ | wc -l

# Per-category breakdown
for tag in TODO FIXME HACK XXX TEMP WORKAROUND; do
  count=$(grep -rn "$tag" src/ 2>/dev/null | wc -l)
  echo "$tag: $count"
done

# ADR backlog
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

This phase is handled by the `dependency-tomographe`. Run `instruments/dependency-tomographe/README.md` Phase 4 (Dependency Health) and Phase 5 (Version & Pinning Discipline) for full dependency analysis. The code-tomographe does not duplicate that work.

---

## Phase 7 — Report

Compile into `output/YYYY-MM-DD_{project_name}/CQ{n}-code.md` (see `qualitoscope/config.yaml` for `project_name`).

---

## Configuration

```yaml
thresholds:
  fmt_violations: 0
  linter_errors_max: 0
  linter_warnings_max: 20
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
  source_dirs: []              # fill in per project, e.g. [src/, lib/]
  exclude: [vendor/, target/, node_modules/, build/]
```

---

## Run History

| Run | Date | Trigger | Report |
|-----|------|---------|--------|
| CQ1 | _pending_ | Initial baseline | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
