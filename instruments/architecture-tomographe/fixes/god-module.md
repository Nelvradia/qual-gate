---
title: "Fix: God Module"
status: current
last-updated: 2026-03-19
instrument: architecture-tomographe
severity-range: "Major"
---

# Fix: God Module

## What this means

A single module has accumulated too many responsibilities, too many lines of code, and too many
dependents. It has become the central hub that everything imports and every change touches. God
modules resist refactoring because any modification risks breaking unrelated functionality. They
are hard to test in isolation, slow to compile, and create merge conflicts constantly. The root
cause is usually incremental growth without periodic restructuring — each new feature finds it
easier to add to the existing module than to create a proper new one.

## How to fix

### Python

**Identify the god module — look for high fan-in and large file size:**

```bash
# Count lines per module
find src/ -name "*.py" -exec wc -l {} + | sort -rn | head -20

# Count how many other files import this module
grep -rn "from mypackage.utils import\|import mypackage.utils" src/ | wc -l
```

**Split by responsibility using the extract-module pattern:**

```python
# BEFORE: utils.py with 2000 lines covering validation, formatting, and IO

# AFTER: Split into focused modules

# validation.py — input validation only
from __future__ import annotations

def validate_email(email: str) -> bool:
    """Validate email format against RFC 5322 simplified pattern."""
    import re
    return bool(re.match(r"^[^@]+@[^@]+\.[^@]+$", email))

def validate_date_range(start: date, end: date) -> None:
    """Raise ValueError if start is after end."""
    if start > end:
        raise ValueError(f"Start date {start} must be before end date {end}")

# formatting.py — output formatting only
from __future__ import annotations

def format_currency(amount: Decimal, currency: str = "EUR") -> str:
    """Format a decimal amount as a currency string."""
    return f"{amount:,.2f} {currency}"

# file_io.py — file operations only
from __future__ import annotations
from pathlib import Path

def read_config(path: Path) -> dict:
    """Read and parse a TOML configuration file."""
    import tomllib
    with open(path, "rb") as f:
        return tomllib.load(f)
```

**Preserve backward compatibility with a facade:** Keep the original module as a thin
re-export layer with a `DeprecationWarning`, then migrate callers incrementally.

### Rust

**Identify god modules:**

```bash
# Count lines per source file
find src/ -name "*.rs" -exec wc -l {} + | sort -rn | head -20

# Count items (functions, structs, enums) in a module
grep -c "^pub\s\+fn\|^pub\s\+struct\|^pub\s\+enum" src/lib.rs
```

**Split a god module into submodules:**

```rust
// BEFORE: lib.rs with 3000 lines

// AFTER: lib.rs becomes a module root that re-exports

// src/lib.rs
pub mod validation;
pub mod formatting;
pub mod file_io;

// Re-export key types for convenience (but users can import directly)
pub use validation::{validate_email, validate_date_range};
pub use formatting::format_currency;
pub use file_io::read_config;

// src/validation.rs — focused module
pub fn validate_email(email: &str) -> bool {
    email.contains('@') && email.contains('.')
}

pub fn validate_date_range(
    start: chrono::NaiveDate,
    end: chrono::NaiveDate,
) -> Result<(), ValidationError> {
    if start > end {
        return Err(ValidationError::InvalidRange { start, end });
    }
    Ok(())
}

// src/formatting.rs — focused module
use rust_decimal::Decimal;

pub fn format_currency(amount: Decimal, currency: &str) -> String {
    format!("{:.2} {}", amount, currency)
}
```

**Split a god crate into workspace members:**

```toml
# For very large modules, promote submodules to their own crates
[workspace]
members = [
    "crates/core-types",   # shared types, no logic
    "crates/validation",   # validation logic
    "crates/formatting",   # formatting utilities
]
```

### TypeScript

**Identify god modules:**

```bash
# Lines per file
find src/ -name "*.ts" -exec wc -l {} + | sort -rn | head -20

# Count exports from a module
grep -c "^export" src/utils.ts
```

**Split and re-export:**

```typescript
// BEFORE: utils.ts with 50+ exported functions

// AFTER: split into focused modules

// validation.ts
export function validateEmail(email: string): boolean {
  return /^[^@]+@[^@]+\.[^@]+$/.test(email);
}

export function validateDateRange(start: Date, end: Date): void {
  if (start > end) {
    throw new RangeError(`Start ${start.toISOString()} must precede end`);
  }
}

// formatting.ts
export function formatCurrency(amount: number, currency = "EUR"): string {
  return new Intl.NumberFormat("en", {
    style: "currency",
    currency,
  }).format(amount);
}

// utils.ts — facade for backward compat (add deprecation notice in JSDoc)
/**
 * @deprecated Import from specific modules instead:
 * - validation: `import { validateEmail } from "./validation"`
 * - formatting: `import { formatCurrency } from "./formatting"`
 */
export { validateEmail, validateDateRange } from "./validation";
export { formatCurrency } from "./formatting";
```

### Go

**Identify god packages:**

```bash
# Lines per file
find pkg/ -name "*.go" -exec wc -l {} + | sort -rn | head -20

# Count exported functions in a package
grep -c "^func [A-Z]" pkg/utils/utils.go
```

**Split the package:**

```go
// BEFORE: pkg/utils/utils.go with 2000 lines

// AFTER: split into focused packages

// pkg/validation/email.go
package validation

func ValidateEmail(email string) bool {
    // ...
}

// pkg/formatting/currency.go
package formatting

import "fmt"

func FormatCurrency(amount float64, currency string) string {
    return fmt.Sprintf("%.2f %s", amount, currency)
}
```

Go does not support re-exports, so update import paths at all call sites. Use `goimports` or
`gopls` rename functionality to automate the migration.

### General

**How to identify a god module:**

- **Size:** More than 500 lines (varies by language, but any file over 500 warrants scrutiny).
- **High fan-in:** Many other modules import it. This makes it a single point of fragility.
- **Multiple responsibilities:** The module handles unrelated concerns (validation, formatting,
  IO, business rules) in one file.
- **Frequent merge conflicts:** If every feature branch touches this file, it is too central.
- **Vague naming:** Names like `utils`, `helpers`, `common`, `misc` are symptoms.

**Splitting strategies:**

1. **By responsibility.** Group related functions, classes, or types into modules with a clear
   single purpose. Each new module should have a name that describes what it does, not what
   it is (e.g., `validation` not `helpers`).

2. **By domain concept.** If the god module serves multiple domain areas, split along domain
   boundaries (e.g., `order_utils` and `user_utils` become `orders.validation` and
   `users.validation`).

3. **Facade extraction.** Keep the original module as a thin re-export layer during migration.
   This avoids a big-bang refactor — dependents migrate gradually while the facade provides
   backward compatibility.

4. **Strangler fig pattern.** For very large modules, create new focused modules alongside
   the old one. New code imports from the focused modules. Migrate old call sites
   incrementally. Delete the god module when no imports remain.

## Prevention

- **File size limits in CI:**
  ```yaml
  check-file-size:
    stage: lint
    script:
      - |
        MAX_LINES=500
        find src/ -name "*.py" -o -name "*.rs" -o -name "*.ts" -o -name "*.go" |
        while read f; do
          lines=$(wc -l < "$f")
          if [ "$lines" -gt "$MAX_LINES" ]; then
            echo "FAIL: $f has $lines lines (max $MAX_LINES)"
            exit 1
          fi
        done
    allow_failure: false
  ```

- **Linter rules:** Configure `pylint` (`max-module-lines`), `clippy`
  (`too_many_lines`), or ESLint (`max-lines`) to warn when a file grows too large.

- **Code review discipline:** Reject MRs that add functionality to an already-large module
  without splitting it first. The reviewer should ask: "Does this belong in a new module?"

- **Architecture documentation:** Maintain a module map (even a simple list) that describes
  each module's responsibility. When a new feature does not fit any existing module's stated
  purpose, it needs a new module — not a dump into `utils`.

- **Periodic audits:** Schedule a quarterly review of the top 10 largest files. If any have
  grown past the threshold, create a refactoring issue before adding more code to them.
