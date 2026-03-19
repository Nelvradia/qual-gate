---
title: "Fix: Copyleft Licence Contamination"
status: current
last-updated: 2026-03-19
instrument: compliance-tomographe
severity-range: "Critical–Major"
---

# Fix: Copyleft Licence Contamination

## What this means

Your project depends on one or more libraries distributed under a copyleft licence (GPL, AGPL,
LGPL, MPL with file-level copyleft, or similar). Copyleft licences require that derivative works
be distributed under the same licence terms. If your project uses a permissive licence (MIT,
Apache-2.0, BSD) or is proprietary, including copyleft dependencies can create a legal obligation
to relicense your entire codebase -- or remove the dependency. AGPL extends this obligation to
software accessed over a network, making it particularly risky for SaaS and API-serving projects.

## How to fix

### Step 1: Audit your dependency tree

Identify every copyleft dependency, including transitive ones.

### Python

```python
# Install licence checker
pip install pip-licenses

# List all dependency licences
pip-licenses --format=table --with-system --order=license

# Filter for copyleft licences specifically
pip-licenses --format=csv | grep -iE "GPL|AGPL|LGPL|MPL|EUPL|OSL|CPAL|SSPL"

# Generate a machine-readable report
pip-licenses --format=json --output-file=licence-report.json
```

For deeper analysis with transitive dependencies:

```python
# pipdeptree shows the full dependency graph
pip install pipdeptree
pipdeptree --warn silence | head -100

# Combine with licence info
pip-licenses --with-authors --with-urls --format=markdown > LICENCE_AUDIT.md
```

### Rust

```bash
# Install cargo-deny (recommended) or cargo-license
cargo install cargo-deny

# Audit licences against a policy
cargo deny check licenses

# List all dependency licences
cargo install cargo-license
cargo license --json | jq '.[] | select(.license | test("GPL|AGPL|LGPL|MPL"))'
```

Configure `deny.toml` to enforce licence policy:

```toml
[licenses]
unlicensed = "deny"
allow = [
    "MIT",
    "Apache-2.0",
    "BSD-2-Clause",
    "BSD-3-Clause",
    "ISC",
    "Zlib",
    "Unicode-DFS-2016",
]
deny = [
    "GPL-2.0",
    "GPL-3.0",
    "AGPL-3.0-only",
    "AGPL-3.0-or-later",
    "SSPL-1.0",
]
copyleft = "deny"
```

### TypeScript

```bash
# Install license-checker
npm install -g license-checker

# Audit all dependencies
license-checker --summary
license-checker --failOn "GPL-2.0;GPL-3.0;AGPL-3.0"

# JSON output for processing
license-checker --json --out licence-report.json

# Check production dependencies only (skip devDependencies)
license-checker --production --failOn "GPL-2.0;GPL-3.0;AGPL-3.0"
```

### Go

```bash
# Install go-licenses (Google's tool)
go install github.com/google/go-licenses@latest

# List all dependency licences
go-licenses csv ./...

# Check for disallowed licences
go-licenses check ./... --disallowed_types=restricted

# Save full licence texts
go-licenses save ./... --save_path=third_party/licences
```

### General

**Licence compatibility matrix (simplified):**

| Your Project Licence | MIT dep | Apache-2.0 dep | LGPL dep | GPL dep | AGPL dep |
|---|---|---|---|---|---|
| MIT                  | OK      | OK             | Caution  | NO      | NO       |
| Apache-2.0           | OK      | OK             | Caution  | NO      | NO       |
| LGPL-2.1+            | OK      | OK             | OK       | NO      | NO       |
| GPL-3.0              | OK      | OK             | OK       | OK      | NO       |
| AGPL-3.0             | OK      | OK             | OK       | OK      | OK       |
| Proprietary          | OK      | OK             | Caution  | NO      | NO       |

**Key distinctions:**

- **GPL**: Derivative works must be GPL. Linking (static or dynamic) generally triggers this.
- **AGPL**: Like GPL, but also triggered by network interaction. SaaS using AGPL code must
  offer source to users.
- **LGPL**: Permits use in proprietary software if linked dynamically and the user can re-link
  against a modified version of the LGPL library.
- **MPL-2.0**: File-level copyleft. Modified MPL files must stay MPL, but other files in your
  project are unaffected.

### Step 2: Replace or isolate copyleft dependencies

**Option A -- Replace with a permissively-licensed alternative:**

Search for drop-in replacements on the same package registry. Many popular GPL libraries have
MIT/Apache-2.0 equivalents.

**Option B -- Isolate behind a process boundary:**

If replacement is not feasible, run the copyleft component as a separate process (microservice,
CLI tool, subprocess) communicating via IPC, REST, or gRPC. This avoids creating a derivative
work in most legal interpretations. Document the boundary clearly.

**Option C -- Negotiate a commercial licence:**

Many GPL projects offer dual licensing. Contact the maintainer or vendor for a commercial
licence that permits proprietary use.

**Option D -- Relicense your project:**

If your project can adopt a compatible copyleft licence, this resolves the conflict but changes
your distribution terms permanently.

## Prevention

**CI-enforceable checks:**

```yaml
# GitLab CI example
licence-audit:
  stage: lint
  script:
    - pip-licenses --fail-on "GNU General Public License v3 (GPLv3)"
    # or for Rust:
    - cargo deny check licenses
    # or for Node:
    - npx license-checker --failOn "GPL-2.0;GPL-3.0;AGPL-3.0"
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      changes:
        - "**/requirements*.txt"
        - "**/Cargo.toml"
        - "**/Cargo.lock"
        - "**/package.json"
        - "**/package-lock.json"
        - "**/go.sum"
```

**Process:**

- Maintain an approved-licence allow-list in your repository (e.g., `deny.toml`, `.licencerc`).
- Require licence review as part of every MR that adds or updates dependencies.
- Run licence audits on every dependency change, not just periodically.
- Document any copyleft exceptions with a written justification and legal review reference.
