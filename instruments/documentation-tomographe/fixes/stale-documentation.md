---
title: "Fix: Stale Documentation"
status: current
last-updated: 2026-03-19
instrument: documentation-tomographe
severity-range: "Minor–Major"
---

# Fix: Stale Documentation

## What this means

Documentation exists but no longer reflects the current state of the code, configuration, or
system behaviour. Stale docs are actively harmful — they are worse than no docs because developers
trust and follow them, then waste time debugging when reality does not match. Common causes include
API changes without doc updates, refactored module structures with outdated READMEs, deprecated
configuration options still documented as current, and removed features that still appear in
tutorials or guides.

## How to fix

### Python

**Add freshness markers to docstrings:**

```python
# Use a last-reviewed marker in module docstrings
"""Order processing module.

Last reviewed: 2026-03-19
Maintainer: platform-team

Handles order creation, validation, and persistence.
"""
from __future__ import annotations


def create_order(items: list[str], customer_id: str) -> str:
    """Create a new order for the given customer.

    Args:
        items: List of product SKUs to include in the order.
        customer_id: The customer's unique identifier.

    Returns:
        The newly created order ID.

    .. versionchanged:: 0.5.0
        Added customer_id parameter (previously inferred from session).
    """
    ...
```

**Detect stale docs with a script:**

```python
# tools/check_doc_freshness.py
"""Flag documentation files not updated in the last N days."""
from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

MAX_AGE_DAYS = 180  # 6 months
DOCS_DIR = Path("docs")
threshold = datetime.now() - timedelta(days=MAX_AGE_DAYS)
stale = []

for doc in DOCS_DIR.rglob("*.md"):
    result = subprocess.run(
        ["git", "log", "-1", "--format=%aI", str(doc)],
        capture_output=True, text=True, check=True,
    )
    last_modified = datetime.fromisoformat(result.stdout.strip())
    if last_modified < threshold:
        stale.append((doc, last_modified))

if stale:
    print("Stale documentation (not updated in 180+ days):")
    for path, date in stale:
        print(f"  {path} — last modified {date.date()}")
    sys.exit(1)
```

**Tie doc updates to code changes using CODEOWNERS:**

```
# .gitlab/CODEOWNERS or CODEOWNERS
# When source code changes, require docs review too

/src/api/         @api-team
/docs/api/        @api-team

/src/auth/        @security-team
/docs/auth/       @security-team
```

### Rust

**Use rustdoc's built-in staleness indicators:**

```rust
/// Creates a new order for the given customer.
///
/// # Arguments
///
/// * `items` - Slice of product SKUs to include in the order.
/// * `customer_id` - The customer's unique identifier.
///
/// # Returns
///
/// The newly created order ID.
///
/// # Panics
///
/// Panics if `items` is empty.
///
/// # Examples
///
/// ```
/// let order_id = myapp::create_order(&["SKU-001", "SKU-002"], "cust-42");
/// assert!(!order_id.is_empty());
/// ```
///
/// # Changelog
///
/// - v0.5.0: Added `customer_id` parameter.
pub fn create_order(items: &[&str], customer_id: &str) -> String {
    assert!(!items.is_empty(), "Order must contain at least one item");
    todo!()
}
```

**Run `cargo test --doc` to catch stale doc examples:**

```bash
# Doc tests run the code in /// examples — if the API changed
# but the example wasn't updated, this fails
cargo test --doc
```

### TypeScript

**Use TSDoc tags and api-extractor for doc drift detection:**

```typescript
/**
 * Creates a new order for the given customer.
 *
 * @param items - List of product SKUs to include in the order.
 * @param customerId - The customer's unique identifier.
 * @returns The newly created order ID.
 *
 * @remarks
 * Changed in v0.5.0: Added customerId parameter.
 *
 * @example
 * ```typescript
 * const orderId = createOrder(["SKU-001", "SKU-002"], "cust-42");
 * ```
 */
export function createOrder(items: string[], customerId: string): string {
  // ...
}
```

**Detect undocumented or outdated exports with api-extractor:**

```bash
# api-extractor compares the current public API against a committed snapshot
npx @microsoft/api-extractor run --local

# If the API changed but docs didn't, the report diff will show it
```

### Go

**Use godoc conventions and example tests for freshness:**

```go
// CreateOrder creates a new order for the given customer.
//
// Changed in v0.5.0: Added customerID parameter.
func CreateOrder(items []string, customerID string) (string, error) {
    if len(items) == 0 {
        return "", errors.New("order must contain at least one item")
    }
    // ...
}

// Example tests are compiled and run — stale examples fail.
func ExampleCreateOrder() {
    orderID, err := CreateOrder([]string{"SKU-001"}, "cust-42")
    if err != nil {
        log.Fatal(err)
    }
    fmt.Println(orderID)
    // Output: order-...
}
```

### General

**Staleness detection strategies:**

1. **Git-based age tracking.** Query `git log` for the last modification date of each doc
   file. Flag anything older than a threshold (90 or 180 days) for review.

2. **Code-doc co-change analysis.** When source files change, check whether their corresponding
   doc files also changed in the same MR. If not, flag the MR for doc review.

3. **Freshness frontmatter.** Add a `last-reviewed` date to every doc file's YAML frontmatter.
   A CI script compares this date against a threshold and fails if the doc is overdue.

4. **Doc ownership.** Assign every doc file to a team or individual in CODEOWNERS. When the
   doc is flagged as stale, the owner is responsible for reviewing and updating it.

5. **Version-tagged docs.** Include a version number in docs that reference specific API
   behaviour. When the code version advances past the doc version, flag it.

**When updating stale docs:**

- Read the current code before updating the doc — do not guess from memory.
- Update all code examples and verify they compile/run.
- Remove references to deleted features, deprecated flags, and old configuration options.
- Add a changelog entry or `versionchanged` marker noting what changed and when.
- If unsure whether a section is still accurate, ask the module owner rather than leaving it.

## Prevention

- **CI freshness check (weekly schedule or per MR):**
  ```yaml
  doc-freshness:
    stage: lint
    script:
      - python tools/check_doc_freshness.py
    rules:
      - if: $CI_PIPELINE_SOURCE == "schedule"
      - if: $CI_PIPELINE_SOURCE == "merge_request_event"
        changes:
          - docs/**/*
    allow_failure: false
  ```

- **Doc review triggers.** Configure CI to require doc review when source code in certain
  directories changes. Use CODEOWNERS to enforce that a docs-aware reviewer approves.

- **Executable documentation.** Wherever possible, make documentation executable: Python
  doctests, Rust doc tests, Go example tests, Jupyter notebooks in CI. Stale examples
  fail automatically.

- **Doc update as MR checklist item.** Add a checkbox to the MR template:
  `[ ] Documentation updated or confirmed still accurate`.

- **Quarterly doc audit.** Schedule a recurring task to review all docs over the age
  threshold. Assign each stale doc to an owner for update or deletion.

- **Prefer docs-as-code.** Keep documentation in the same repository as the source code.
  Docs in wikis, Confluence, or Google Docs will always drift because they are not part
  of the code review process.
