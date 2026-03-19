---
title: "Fix: Missing API Documentation"
status: current
last-updated: 2026-03-19
instrument: documentation-tomographe
severity-range: "Major"
---

# Fix: Missing API Documentation

## What this means

Public functions, classes, methods, or endpoints lack documentation. Consumers of the API — whether
other developers, other teams, or your future self — cannot determine correct usage without reading
the implementation. This slows onboarding, increases support burden, and leads to incorrect usage
that causes bugs. Missing API docs also prevent automated documentation generation, making it
impossible to produce reference sites, SDK docs, or client libraries from the source.

## How to fix

### Python

**Configure ruff to enforce docstrings on public APIs:**

```toml
# pyproject.toml
[tool.ruff.lint]
select = [
    "D",     # pydocstyle
]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D"]  # don't require docstrings in tests
```

**Write Google-style docstrings:**

```python
from __future__ import annotations

from decimal import Decimal


def calculate_discount(
    subtotal: Decimal,
    discount_percent: Decimal,
    max_discount: Decimal | None = None,
) -> Decimal:
    """Calculate the discounted price for an order.

    Applies the given percentage discount to the subtotal. If a maximum
    discount cap is specified, the discount will not exceed that amount.

    Args:
        subtotal: The pre-discount order total. Must be non-negative.
        discount_percent: Discount as a percentage (e.g., 15 for 15%).
            Must be between 0 and 100 inclusive.
        max_discount: Optional absolute cap on the discount amount.

    Returns:
        The final price after applying the discount.

    Raises:
        ValueError: If subtotal is negative or discount_percent is
            outside [0, 100].

    Examples:
        >>> calculate_discount(Decimal("100.00"), Decimal("10"))
        Decimal('90.00')
    """
    ...
```

**Generate documentation with Sphinx:**

```bash
pip install sphinx sphinx-autodoc-typehints furo

# Initialise Sphinx in docs/
sphinx-quickstart docs/ --sep --project "MyPackage" --author "Team"

# Configure autodoc in docs/conf.py
# extensions = ["sphinx.ext.autodoc", "sphinx_autodoc_typehints"]

# Generate API reference stubs
sphinx-apidoc -o docs/api/ src/mypackage/

# Build HTML docs
sphinx-build -b html docs/ docs/_build/html
```

**Alternative:** Use mkdocs with `mkdocstrings[python]` and `mkdocs-material` for a
modern documentation site with automatic API reference generation.

### Rust

**Enable rustdoc lints to enforce documentation:**

```rust
// lib.rs — require docs on all public items
#![warn(missing_docs)]
#![warn(rustdoc::missing_doc_code_examples)]

//! MyApp — order processing library.
//!
//! This crate provides order creation, validation, and persistence.

/// Calculates the discounted price for an order.
///
/// Applies the given percentage discount to the subtotal. If a maximum
/// discount cap is specified, the discount will not exceed that amount.
///
/// # Arguments
///
/// * `subtotal` - The pre-discount order total. Must be non-negative.
/// * `discount_percent` - Discount as a percentage (e.g., 15.0 for 15%).
/// * `max_discount` - Optional absolute cap on the discount amount.
///
/// # Returns
///
/// The final price after applying the discount.
///
/// # Errors
///
/// Returns [`CalculationError::InvalidInput`] if the subtotal is negative
/// or the discount percentage is outside `[0, 100]`.
///
/// # Examples
///
/// ```
/// let price = myapp::calculate_discount(100.0, 10.0, None).unwrap();
/// assert!((price - 90.0).abs() < f64::EPSILON);
/// ```
pub fn calculate_discount(
    subtotal: f64, discount_percent: f64, max_discount: Option<f64>,
) -> Result<f64, CalculationError> {
    todo!()
}
```

**Check for broken doc links and missing docs in CI:**

```bash
RUSTDOCFLAGS="-D warnings" cargo doc --no-deps
```

### TypeScript

**Enable TSDoc linting with eslint-plugin-tsdoc:**

```bash
npm install --save-dev eslint-plugin-tsdoc
```

```jsonc
// .eslintrc.json
{
  "plugins": ["tsdoc"],
  "rules": {
    "tsdoc/syntax": "error"
  }
}
```

**Write TSDoc-compliant documentation:**

```typescript
/**
 * Calculates the discounted price for an order.
 *
 * @remarks
 * Applies the given percentage discount to the subtotal. If a maximum
 * discount cap is specified, the discount will not exceed that amount.
 *
 * @param subtotal - The pre-discount order total. Must be non-negative.
 * @param discountPercent - Discount as a percentage (e.g., 15 for 15%).
 * @param maxDiscount - Optional absolute cap on the discount amount.
 * @returns The final price after applying the discount.
 * @throws {@link RangeError} If subtotal is negative or discountPercent is
 *   outside [0, 100].
 *
 * @example
 * ```typescript
 * const price = calculateDiscount(100, 10);
 * // price === 90
 *
 * const capped = calculateDiscount(100, 50, 20);
 * // capped === 80
 * ```
 */
export function calculateDiscount(
  subtotal: number,
  discountPercent: number,
  maxDiscount?: number,
): number {
  // ...
}
```

**Generate docs with TypeDoc:**

```bash
npx typedoc --entryPoints src/index.ts --out docs/api

# Or in tsconfig for project-level config:
# "typedocOptions": {
#   "entryPoints": ["src/index.ts"],
#   "out": "docs/api"
# }
```

### Go

**Enable golint or revive to flag missing doc comments:**

```bash
# revive is a drop-in replacement for golint with more rules
go install github.com/mgechev/revive@latest

# Flag unexported and exported functions missing comments
revive -formatter friendly ./...
```

```toml
# revive.toml
[rule.exported]
  severity = "error"
  arguments = [
    "checkPrivateReceivers",
    "sayRepetitiveInsteadOfStutters",
  ]
```

**Write idiomatic Go doc comments:**

```go
// CalculateDiscount computes the discounted price for an order.
//
// It applies the given percentage discount to the subtotal. If maxDiscount
// is non-nil, the discount will not exceed that amount.
//
// CalculateDiscount returns an error if subtotal is negative or
// discountPercent is outside [0, 100].
func CalculateDiscount(
    subtotal, discountPercent float64, maxDiscount *float64,
) (float64, error) {
    // ...
}
```

**Generate docs with pkgsite:**

```bash
go install golang.org/x/pkgsite/cmd/pkgsite@latest
pkgsite -http=:8080
```

### General

**What every public API doc should include:**

1. **Summary.** One sentence describing what the function/method/endpoint does.
2. **Parameters.** Name, type, constraints, and purpose for each parameter.
3. **Return value.** What is returned and under what conditions.
4. **Errors.** What errors can occur and when. Include error types or status codes.
5. **Examples.** At least one usage example, ideally executable (doctest, example test).
6. **Side effects.** If the function modifies state, performs IO, or has other side effects,
   document them explicitly.

**For REST/gRPC APIs, also include:** HTTP method and path, request/response schemas,
authentication requirements, rate limits, and status codes. Use OpenAPI/Swagger specs to
define these contracts and generate interactive documentation automatically.

## Prevention

- **Linter enforcement in CI (every MR):**
  ```yaml
  doc-lint:
    stage: lint
    script:
      - ruff check --select D src/                          # Python
      - RUSTDOCFLAGS="-D warnings" cargo doc --no-deps      # Rust
      - npx eslint --rule 'tsdoc/syntax: error' 'src/**/*'  # TypeScript
      - revive -formatter friendly ./...                     # Go
    allow_failure: false
  ```

- **Coverage for docs.** Track doc coverage with `interrogate` (Python), `#![warn(missing_docs)]`
  (Rust), or equivalent. Set a minimum threshold in CI.

- **Doc generation in CI.** Build docs on every MR to catch broken references and rendering
  errors before merge.

- **MR template checklist.** Include `[ ] All new/changed public APIs are documented`.

- **Review standards.** Code reviewers must verify that new public APIs include complete
  documentation. An undocumented public function is an incomplete implementation.
