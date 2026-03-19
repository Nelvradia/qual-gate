---
title: "Fix: Broken Cross-References"
status: current
last-updated: 2026-03-19
instrument: documentation-tomographe
severity-range: "Minor"
---

# Fix: Broken Cross-References

## What this means

Links within your documentation point to pages, sections, or resources that no longer exist or
have moved. Broken cross-references frustrate readers, erode trust in the documentation, and
create dead ends during troubleshooting or onboarding. They typically accumulate after file
renames, section restructuring, URL changes in external resources, or deleted documentation
pages that are still referenced elsewhere.

## How to fix

### Python

**Check internal doc links with Sphinx linkcheck:**

```bash
# If using Sphinx for documentation
sphinx-build -b linkcheck docs/ docs/_build/linkcheck

# Review the output file for broken links
cat docs/_build/linkcheck/output.txt
```

**Check links in docstrings with pydocstyle and manual review:**

```python
# Common broken reference patterns in Python docstrings:

# BAD: referencing a renamed class
"""See :class:`mypackage.OldClassName` for details."""

# GOOD: updated reference
"""See :class:`mypackage.NewClassName` for details."""

# BAD: referencing a deleted module
"""Defined in :mod:`mypackage.deprecated_module`."""

# GOOD: updated reference
"""Defined in :mod:`mypackage.current_module`."""
```

**Fix intersphinx references:**

```python
# docs/conf.py — configure intersphinx for cross-project references
extensions = ["sphinx.ext.intersphinx"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "requests": ("https://requests.readthedocs.io/en/latest/", None),
}
```

**For mkdocs, use the linkcheck plugin:**

```yaml
# mkdocs.yml
plugins:
  - search
  - htmlproofer:  # or mkdocs-linkcheck
      raise_on_warnings: true
```

### Rust

**Check doc links at compile time (enabled by default since Rust 1.56):**

```rust
// Rust's rustdoc checks intra-doc links at build time.
// Broken links produce warnings (or errors with -D warnings).

/// Creates an order using the [`OrderRepository`] trait.
///
/// See [`crate::domain::Order`] for the order model.
///
/// # Errors
///
/// Returns [`CreateOrderError`] if validation fails.
pub fn create_order(repo: &dyn OrderRepository) -> Result<Order, CreateOrderError> {
    todo!()
}

// If OrderRepository was renamed or moved, rustdoc will flag the broken link.
```

```bash
# Fail CI on any broken intra-doc links
RUSTDOCFLAGS="-D warnings" cargo doc --no-deps
```

**Fix common broken link patterns:**

```rust
// BAD: linking to a moved type
/// See [`old_module::OldType`] for details.

// GOOD: updated path
/// See [`new_module::NewType`] for details.

// BAD: linking to a removed function
/// Similar to [`deprecated_function`].

// GOOD: link removed or updated
/// Similar to [`replacement_function`].
```

### TypeScript

**Check links in TypeDoc output:**

```bash
# Generate docs and check for broken references
npx typedoc --entryPoints src/index.ts --out docs/api

# Use html-proofer or linkinator to scan the generated HTML
npx linkinator docs/api --recurse --skip "^(?!file://)"
```

**Fix TSDoc cross-references:**

```typescript
// BAD: referencing a renamed type
/** See {@link OldClassName} for details. */

// GOOD: updated reference
/** See {@link NewClassName} for details. */

// BAD: referencing a moved module
/** Defined in {@link ./old-module | old module}. */

// GOOD: updated reference
/** Defined in {@link ./new-module | new module}. */
```

### Go

**Check doc links with godoc and manual review:**

```bash
# Go doc comments don't have a formal cross-reference syntax
# beyond package-qualified names. Check manually or use:

# linkinator for generated doc sites
npx linkinator http://localhost:6060/pkg/myapp/ --recurse
```

**Fix common patterns:**

```go
// BAD: referencing a renamed function
// See the OldFunctionName function for details.

// GOOD: updated reference
// See the NewFunctionName function for details.

// For Go 1.19+ doc links:
// BAD: broken doc link
// See [OldType] for the data model.

// GOOD: updated doc link
// See [NewType] for the data model.
```

### General

**Link checking tools (language-agnostic):**

```bash
# linkinator — checks HTML files and live URLs
npx linkinator ./docs/ --recurse

# markdown-link-check — checks links in Markdown files directly
npx markdown-link-check docs/**/*.md --config .markdown-link-check.json

# lychee — fast, written in Rust, supports Markdown and HTML
# https://github.com/lycheeverse/lychee
lychee docs/ --format detailed
lychee "**/*.md" --exclude "localhost"
```

**Configuration for markdown-link-check:**

```json
{
  "ignorePatterns": [
    { "pattern": "^https://internal\\.company\\.com" }
  ],
  "replacementPatterns": [
    {
      "pattern": "^/docs/",
      "replacement": "{{BASEURL}}/docs/"
    }
  ],
  "aliveStatusCodes": [200, 206, 301, 302],
  "retryCount": 2,
  "timeout": "10s"
}
```

**Best practices for maintainable cross-references:**

1. **Use relative paths for internal links.** Relative paths survive directory moves better
   than absolute paths. `../api/orders.md` is more resilient than `/docs/api/orders.md`.

2. **Prefer anchor-based links over line numbers.** `#create-order` survives edits;
   `#L42` breaks when lines shift.

3. **Use named references in Markdown.** Define link targets once and reference them
   by name. This makes bulk updates easier:
   ```markdown
   See the [Order API][order-api] for details.

   [order-api]: ./api/orders.md#create-order
   ```

4. **Avoid deep links to external docs.** External URLs change without notice. Link to
   stable pages (versioned docs, permalinks) rather than transient pages.

5. **Keep a link inventory.** For large documentation sets, maintain a list of all
   cross-references. Automated tools generate this, but even a simple grep helps:
   ```bash
   grep -rn "\[.*\](.*)" docs/ | grep -v node_modules
   ```

**Fixing broken links in bulk:**

1. Run a link checker to get the full list of broken links.
2. Categorise: renamed (fix the path), deleted (remove the link or redirect), external
   (update the URL or remove if the resource is gone).
3. For renamed files, use search-and-replace across all Markdown files.
4. For deleted content, decide whether to restore it, redirect to a replacement, or
   remove the reference entirely.
5. Commit link fixes separately from content changes for clean git history.

## Prevention

- **CI link check (every MR that touches docs):**
  ```yaml
  link-check:
    stage: lint
    script:
      - npx markdown-link-check docs/**/*.md --config .markdown-link-check.json
      # Or for generated doc sites:
      - sphinx-build -b linkcheck docs/ docs/_build/linkcheck
      # Or for Rust:
      - RUSTDOCFLAGS="-D warnings" cargo doc --no-deps
    rules:
      - if: $CI_PIPELINE_SOURCE == "merge_request_event"
        changes:
          - "docs/**/*"
          - "**/*.md"
          - "src/**/*.rs"  # Rust intra-doc links
    allow_failure: false
  ```

- **Scheduled full-site check.** External URLs can break at any time. Run a weekly
  scheduled pipeline that checks all links, including external ones:
  ```yaml
  full-link-check:
    stage: test
    script:
      - lychee "**/*.md" --format detailed --max-concurrency 4
    rules:
      - if: $CI_PIPELINE_SOURCE == "schedule"
    allow_failure: true  # external failures shouldn't block; triage manually
  ```

- **Pre-commit hook for local feedback:**
  ```yaml
  # .pre-commit-config.yaml
  repos:
    - repo: https://github.com/tcort/markdown-link-check
      rev: v3.11.2
      hooks:
        - id: markdown-link-check
          args: ["--config", ".markdown-link-check.json"]
  ```

- **Redirect maps.** When renaming or moving documentation files, add a redirect entry
  so old links continue to work. Sphinx supports `redirects`, mkdocs has the
  `mkdocs-redirects` plugin, and static site generators support `_redirects` files.

- **File rename detection in MR reviews.** If a reviewer sees a renamed file in the
  diff, they should check for references to the old name across the codebase.
