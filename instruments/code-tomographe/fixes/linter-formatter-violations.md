---
title: "Fix: Linter & Formatter Violations"
status: current
last-updated: 2026-03-19
instrument: code-tomographe
severity-range: "Minor--Major"
---

# Fix: Linter & Formatter Violations

## What this means

Your codebase has style or lint violations that automated tools would catch. Formatter violations
indicate inconsistent whitespace, line length, import ordering, or brace placement. Linter
violations indicate potential bugs, anti-patterns, or deviations from language idioms. When CI
does not enforce these checks, violations accumulate and make code reviews noisy, diffs harder
to read, and onboarding slower. The severity depends on volume: a handful of warnings is Minor,
but widespread violations or linter errors that mask real bugs are Major.

## How to fix

### Python

**Tooling:** `ruff` (formatter + linter in one binary).

**Setup:**

```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP", "B", "SIM", "RUF"]
ignore = []

[tool.ruff.format]
quote-style = "double"
```

**Fix all auto-fixable issues in one pass:**

```bash
ruff check --fix src/ tests/
ruff format src/ tests/
```

**Common violations and fixes:**

```python
# BAD: unused import (F401)
import os
import sys  # unused

# GOOD: remove unused imports
import os

# BAD: bare except (E722)
try:
    process()
except:
    pass

# GOOD: catch specific exceptions
try:
    process()
except ValueError as exc:
    logger.warning("Invalid input: %s", exc)

# BAD: mutable default argument (B006)
def append_item(item, items=[]):
    items.append(item)
    return items

# GOOD: use None sentinel
def append_item(item, items: list | None = None) -> list:
    if items is None:
        items = []
    items.append(item)
    return items
```

### Rust

**Tooling:** `rustfmt` (formatter) + `clippy` (linter).

**Setup:**

```toml
# rustfmt.toml
max_width = 100
edition = "2024"
```

```toml
# clippy.toml
cognitive-complexity-threshold = 15
```

**Fix all auto-fixable issues:**

```bash
cargo fmt --all
cargo clippy --fix --allow-dirty --workspace --all-targets
```

**Common violations and fixes:**

```rust
// BAD: clippy::needless_return
fn square(x: i32) -> i32 {
    return x * x;
}

// GOOD: implicit return
fn square(x: i32) -> i32 {
    x * x
}

// BAD: clippy::manual_map
let result = match maybe_val {
    Some(v) => Some(v * 2),
    None => None,
};

// GOOD: use map
let result = maybe_val.map(|v| v * 2);

// BAD: clippy::clone_on_ref_ptr
let arc2 = arc1.clone();

// GOOD: explicit Arc::clone
let arc2 = Arc::clone(&arc1);
```

### TypeScript

**Tooling:** `eslint` (linter) + `prettier` (formatter).

**Setup:**

```json
// .prettierrc
{
  "printWidth": 100,
  "singleQuote": true,
  "trailingComma": "all",
  "semi": true
}
```

```js
// eslint.config.js (flat config, ESLint 9+)
import eslint from "@eslint/js";
import tseslint from "typescript-eslint";
import prettier from "eslint-config-prettier";

export default tseslint.config(
  eslint.configs.recommended,
  ...tseslint.configs.recommended,
  prettier,
  {
    rules: {
      "@typescript-eslint/no-unused-vars": "error",
      "@typescript-eslint/no-explicit-any": "warn",
      "no-console": "warn",
    },
  },
);
```

**Fix all auto-fixable issues:**

```bash
npx prettier --write "src/**/*.{ts,tsx}"
npx eslint --fix "src/**/*.{ts,tsx}"
```

### Go

**Tooling:** `gofmt` (formatter, built-in) + `golangci-lint` (meta-linter).

**Setup:**

```yaml
# .golangci.yml
linters:
  enable:
    - errcheck
    - govet
    - staticcheck
    - unused
    - gosimple
    - ineffassign
    - revive
    - misspell
    - gocyclo

linters-settings:
  gocyclo:
    min-complexity: 15
  revive:
    rules:
      - name: exported
```

**Fix all auto-fixable issues:**

```bash
gofmt -w .
golangci-lint run --fix ./...
```

**Common violations and fixes:**

```go
// BAD: errcheck — ignoring returned error
file, _ := os.Open("config.yaml")

// GOOD: handle the error
file, err := os.Open("config.yaml")
if err != nil {
    return fmt.Errorf("open config: %w", err)
}
defer file.Close()
```

### General

- Run the formatter first, then the linter. Formatting fixes often resolve lint warnings.
- If a lint rule produces false positives, suppress it inline with a comment explaining why,
  not globally in config.
- Treat linter errors the same as compiler errors: they block merge.
- Linter warnings above the project threshold (default: 20) are Minor; above 50 are Major.

## Prevention

**Pre-commit hooks** (using [pre-commit](https://pre-commit.com)):

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
```

**CI enforcement:**

```yaml
# GitLab CI example
lint:
  stage: lint
  script:
    - ruff check --output-format=gitlab src/ tests/
    - ruff format --check src/ tests/
  allow_failure: false
```

**Editor integration:** Configure your editor to format on save. All major editors support
`ruff`, `rustfmt`, `prettier`, and `gofmt` as format-on-save providers. This eliminates
violations before they reach version control.
