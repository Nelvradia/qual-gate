---
title: "Fix: Architectural Drift"
status: current
last-updated: 2026-03-19
instrument: architecture-tomographe
severity-range: "Minor–Major"
---

# Fix: Architectural Drift

## What this means

The implemented code no longer matches the documented architecture. Decisions recorded in ADRs,
architecture diagrams, or design documents describe one structure, but the codebase has diverged
through incremental changes, shortcuts, or undocumented redesigns. Drift is dangerous because it
erodes trust in documentation — developers stop reading architecture docs because they know the
docs are wrong, which accelerates further drift. It also makes onboarding harder, introduces
accidental complexity, and can cause teams to build on assumptions that no longer hold.

## How to fix

### Python

**Create architecture fitness functions as tests:**

```python
# tests/architecture/test_layer_compliance.py
"""Architecture fitness functions — fail if the code drifts from the design."""
from __future__ import annotations

import ast
import importlib
import pkgutil
from pathlib import Path

import pytest

DOMAIN_PACKAGE = "mypackage.domain"
FORBIDDEN_IN_DOMAIN = {
    "sqlalchemy", "requests", "fastapi", "httpx", "boto3", "redis",
}


def _get_imports(module_path: Path) -> set[str]:
    """Extract all import names from a Python module."""
    tree = ast.parse(module_path.read_text())
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return imports


def test_domain_has_no_infrastructure_imports():
    """Domain layer must not import infrastructure packages."""
    domain_dir = Path("src/mypackage/domain")
    violations = []
    for py_file in domain_dir.rglob("*.py"):
        imports = _get_imports(py_file)
        bad = imports & FORBIDDEN_IN_DOMAIN
        if bad:
            violations.append(f"{py_file}: imports {bad}")

    assert not violations, (
        "Domain layer imports infrastructure packages:\n"
        + "\n".join(violations)
    )


def test_public_api_matches_documented_exports():
    """All documented public API symbols must exist in the package."""
    documented_exports = {"OrderService", "UserService", "validate_email"}
    import mypackage
    actual_exports = set(dir(mypackage))
    missing = documented_exports - actual_exports
    assert not missing, f"Documented symbols missing from package: {missing}"
```

**Reconcile ADRs with current state:**

```python
# Script to list all ADRs and their status
# tools/check_adrs.py
from pathlib import Path
import re

ADR_DIR = Path("docs/decisions")

for adr in sorted(ADR_DIR.glob("*.md")):
    content = adr.read_text()
    status_match = re.search(r"status:\s*(\w+)", content, re.IGNORECASE)
    status = status_match.group(1) if status_match else "UNKNOWN"
    print(f"{adr.name}: {status}")
    if status.lower() == "accepted":
        # Flag for review — is this decision still reflected in the code?
        print(f"  -> Review: is this ADR still accurate?")
```

### Rust

**Architecture tests using module visibility and compile-time checks:**

```rust
// tests/architecture.rs
//! Architecture fitness tests — verify the crate structure matches the design.

#[test]
fn domain_types_are_send_and_sync() {
    // If domain types are meant to be thread-safe, assert it at compile time.
    fn assert_send_sync<T: Send + Sync>() {}
    assert_send_sync::<myapp::domain::Order>();
    assert_send_sync::<myapp::domain::User>();
}

#[test]
fn public_api_surface_matches_documentation() {
    // Verify that documented public types actually exist and are public.
    // This is a compile-time check — if the type is removed, this fails to compile.
    let _: myapp::OrderService;
    let _: myapp::UserService;
    let _: fn(&str) -> bool = myapp::validate_email;
}
```

**Use cargo-public-api to detect unintended API changes:**

```bash
cargo install cargo-public-api

# Generate current public API
cargo public-api > api-current.txt

# Diff against the documented/expected API
diff api-expected.txt api-current.txt
```

### TypeScript

**ArchUnit-style tests with ts-arch:**

```typescript
// tests/architecture.test.ts
import { filesOfProject } from "ts-arch";

describe("Architecture rules", () => {
  it("domain should not depend on infrastructure", async () => {
    const rule = filesOfProject()
      .inFolder("domain")
      .shouldNot()
      .dependOnFiles()
      .inFolder("infrastructure");

    await expect(rule).toPassAsync();
  });

  it("API layer should not depend on database directly", async () => {
    const rule = filesOfProject()
      .inFolder("api")
      .shouldNot()
      .dependOnFiles()
      .matchingPattern(".*repository.*");

    await expect(rule).toPassAsync();
  });
});
```

**API surface validation with api-extractor:**

```bash
npx @microsoft/api-extractor run --local

# Generates an API report file. Diff it against the committed version
# to detect unintended public API changes.
```

### Go

**Architecture tests using build constraints and package analysis:**

```go
// tests/architecture_test.go
package architecture_test

import (
    "go/parser"
    "go/token"
    "os"
    "path/filepath"
    "strings"
    "testing"
)

func TestDomainHasNoInfraImports(t *testing.T) {
    forbidden := map[string]bool{
        "database/sql": true,
        "net/http":     true,
    }

    fset := token.NewFileSet()
    domainDir := filepath.Join("pkg", "domain")

    err := filepath.Walk(domainDir, func(path string, info os.FileInfo, err error) error {
        if err != nil || !strings.HasSuffix(path, ".go") {
            return err
        }
        f, parseErr := parser.ParseFile(fset, path, nil, parser.ImportsOnly)
        if parseErr != nil {
            return parseErr
        }
        for _, imp := range f.Imports {
            pkg := strings.Trim(imp.Path.Value, `"`)
            if forbidden[pkg] {
                t.Errorf("%s imports forbidden package %s", path, pkg)
            }
        }
        return nil
    })
    if err != nil {
        t.Fatal(err)
    }
}
```

### General

**Drift detection strategies:**

1. **Architecture fitness functions.** Executable tests that assert architectural properties.
   They run in CI and fail if the code drifts from the design. Examples: import direction
   checks, public API surface validation, module size limits, dependency counts.

2. **ADR lifecycle management.** Every ADR has a status: `proposed`, `accepted`, `superseded`,
   `deprecated`. When code changes make an ADR inaccurate, the ADR must be updated in the
   same MR. Stale ADRs are worse than no ADRs.

3. **Architecture diagrams as code.** Use Mermaid, PlantUML, or Structurizr DSL to define
   diagrams in version-controlled files next to the code. Diagrams in Confluence or Google
   Docs will always drift — diagrams in the repo can be validated.

4. **Periodic architecture review.** Schedule a quarterly review where the team walks through
   the documented architecture and compares it with the actual dependency graph. Update docs
   and create refactoring issues for any drift found.

5. **C4 model snapshots.** Generate a C4 context/container/component diagram from the code
   (tools like Structurizr can auto-generate from annotations). Compare against the intended
   architecture.

**ADR reconciliation checklist:**

- List all ADRs with status `accepted`.
- For each, verify the decision is still reflected in the code.
- If the code has changed, either update the code to match or supersede the ADR with a new one
  explaining why the decision changed.
- Mark obsolete ADRs as `deprecated` with a pointer to the replacement.

## Prevention

- **Fitness functions in CI (every MR):**
  ```yaml
  architecture-check:
    stage: test
    script:
      - pytest tests/architecture/ -v       # Python
      - cargo test --test architecture       # Rust
      - npx jest tests/architecture.test.ts  # TypeScript
      - go test ./tests/architecture/...     # Go
    allow_failure: false
  ```

- **ADR-code coupling.** Require that any MR touching architecture-relevant code also updates
  the corresponding ADR. Enforce via a CI check that flags ADR staleness (e.g., ADR last
  modified >6 months ago while the referenced modules were modified recently).

- **Dependency graph generation in CI.** Generate and commit a dependency graph image on each
  release. Visual diffs make drift immediately obvious.

- **Architecture review as a merge gate.** For MRs that add new modules, new external
  dependencies, or new inter-service communication, require architecture review sign-off
  in addition to normal code review.

- **Living documentation.** Keep architecture docs in the same repo as the code, ideally as
  Mermaid or PlantUML files that render in GitLab/GitHub. Review them alongside code changes.
  Dead docs in a wiki will always drift.
