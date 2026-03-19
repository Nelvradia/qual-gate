---
title: "Fix: Technical Debt Management"
status: current
last-updated: 2026-03-19
instrument: code-tomographe
severity-range: "Minor--Major"
---

# Fix: Technical Debt Management

## What this means

Technical debt is the accumulated cost of shortcuts, deferred decisions, and known imperfections
in a codebase. It manifests as TODO/FIXME comments, unresolved architecture decision records
(ADRs), suppressed lint warnings, missing tests, and outdated patterns. A small amount of
tracked debt is normal and healthy -- it means the team is making conscious trade-offs. Untracked
or growing debt is the problem: it slows feature delivery, increases defect rates, and makes
onboarding harder. The severity depends on volume and age: a handful of recent TODOs with issue
references is Minor; dozens of undated, unreferenced FIXMEs or stale ADRs is Major.

## How to fix

### Python

**Inventory all debt markers:**

```bash
# Count by category
for tag in TODO FIXME HACK XXX TEMP WORKAROUND; do
  count=$(grep -rn "$tag" src/ tests/ 2>/dev/null | wc -l)
  echo "$tag: $count"
done
```

**Enforce structured TODO format:**

```python
# BAD: undated, no owner, no issue reference
# TODO: fix this later

# GOOD: traceable, actionable
# TODO(alice, #142): Replace naive search with indexed lookup.
#   Context: Current O(n^2) scan is acceptable for <100 items but
#   will degrade at projected scale. Blocked on schema migration.
```

**Automated enforcement with todo-or-die:**

```python
# pip install todo-or-die
from todo_or_die import todo_or_die

# This will raise an error after the specified date,
# forcing the debt to be addressed.
todo_or_die("Migrate to v2 API", by=datetime(2026, 6, 1))
```

**Ruff rules for debt markers:**

```toml
# pyproject.toml
[tool.ruff.lint]
select = ["FIX", "TD"]
# FIX001: Line contains FIXME
# FIX002: Line contains TODO
# TD002: Missing author in TODO
# TD003: Missing issue link in TODO
```

### Rust

**Inventory:**

```bash
grep -rn 'TODO\|FIXME\|HACK\|XXX' src/ --include='*.rs' | \
  sed 's/:.*//' | sort | uniq -c | sort -rn
```

**Structured TODO format:**

```rust
// BAD
// TODO fix error handling

// GOOD
// TODO(#87): Replace unwrap() with proper error propagation.
//   This path is only hit during startup; panicking is acceptable
//   for now but should return Result once the config module is refactored.
```

**Clippy lint for TODOs:**

```toml
# clippy.toml -- warn on TODO comments so they show up in CI output
# (clippy does not have a built-in TODO lint, but you can use
# a custom deny list or a separate tool)
```

```bash
# cargo-todo: list and count TODO/FIXME markers
cargo install cargo-todo
cargo todo
```

**Audit suppressed warnings:**

```bash
# Every #[allow(...)] is potential debt. List them all.
grep -rn '#\[allow(' src/ --include='*.rs'
# Each should have a comment explaining why the suppression exists
# and under what conditions it can be removed.
```

### TypeScript

**Inventory:**

```bash
npx leasot 'src/**/*.ts'          # lists all TODO/FIXME/HACK markers
npx leasot 'src/**/*.ts' --table  # formatted table output
```

**ESLint enforcement:**

```js
// eslint.config.js
{
  rules: {
    "no-warning-comments": ["warn", {
      terms: ["todo", "fixme", "hack"],
      location: "start",
    }],
  },
}
```

**Structured format:**

```typescript
// BAD
// TODO fix this

// GOOD
// TODO(#203): Extract validation into shared schema.
//   Currently duplicated in createUser and updateUser handlers.
//   Estimate: 2h. Blocked on: nothing.
```

### Go

**Inventory:**

```bash
grep -rn 'TODO\|FIXME\|HACK\|XXX' . --include='*.go' | \
  grep -v vendor/ | grep -v _test.go
```

**golangci-lint enforcement:**

```yaml
# .golangci.yml
linters:
  enable:
    - godox      # reports TODO/FIXME/BUG comments

linters-settings:
  godox:
    keywords:
      - TODO
      - FIXME
      - HACK
      - BUG
```

**Structured format:**

```go
// BAD
// TODO: handle error

// GOOD
// TODO(#45): Return typed error instead of logging and continuing.
//   Current behaviour swallows the error, which masks upstream failures
//   in the retry loop. Estimate: 1h.
```

### General

**TODO triage workflow:**

1. **Collect:** Run the debt marker inventory across the entire codebase.
2. **Classify:** For each marker, determine:
   - Does it reference an issue? If not, create one or delete the TODO.
   - Is it still relevant? If the surrounding code has changed, the TODO may be stale.
   - What is the effort estimate? (0.5h for a simple cleanup, 2-8h for a refactor)
3. **Prioritise:** Use a simple framework:
   - **P1 (next sprint):** Debt that blocks current work or causes recurring incidents.
   - **P2 (this quarter):** Debt that slows development measurably (repeated confusion,
     workarounds in multiple MRs).
   - **P3 (backlog):** Debt that is cosmetic or low-impact. Track but do not schedule.
4. **Budget:** Allocate 10-20% of each sprint to debt reduction. Do not let it accumulate
   indefinitely -- compound interest works against you.

**Debt register:**

Maintain a lightweight register (a table in a markdown file or a label in your issue tracker)
that tracks the total debt inventory:

| ID | Description | Location | Est. Hours | Priority | Created | Issue |
|---|---|---|---|---|---|---|
| D-001 | Replace naive O(n^2) search | `src/search.py:42` | 4h | P2 | 2026-01 | #142 |
| D-002 | Remove deprecated v1 API | `src/api/v1/` | 8h | P3 | 2025-11 | #98 |
| D-003 | Add retry logic to HTTP client | `src/client.rs:88` | 2h | P1 | 2026-03 | #201 |

**ADR backlog review:**

- Quarterly: review all ADRs with status `Pending` or `Revisit`.
- If the revisit condition has been met, schedule the decision.
- If the ADR is older than 6 months and the condition has not been met, re-evaluate whether
  the decision is still relevant.

**Prioritisation framework -- cost of delay:**

Ask two questions for each debt item:
1. **What does it cost us every week this stays unfixed?** (developer hours lost, incidents
   caused, onboarding friction)
2. **What does it cost to fix it now?** (hours of work, risk of regression)

If weekly cost x expected remaining weeks > fix cost, schedule it now.

## Prevention

- **CI enforcement:** Fail the pipeline if a TODO/FIXME does not include an issue reference.
  Use `ruff` (Python), `godox` (Go), `leasot` (TypeScript), or a custom grep-based check.
- **todo-or-die pattern:** For time-sensitive debt, use a mechanism that fails the build after
  a deadline. This forces the conversation before the debt becomes permanent.
- **MR template:** Include a "Technical debt" section. Authors declare any new debt introduced
  and link to the tracking issue.
- **Sprint retrospective:** Review the debt register. If debt count is growing, allocate more
  capacity. If it is shrinking, the process is working.
- **Definition of Done:** "No new untracked debt" is part of the DoD for every MR. A TODO
  without an issue reference is not tracked.
