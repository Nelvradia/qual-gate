---
title: "Fix: Licence Risk"
status: current
last-updated: 2026-03-19
instrument: dependency-tomographe
severity-range: "Major–Critical"
---

# Fix: Licence Risk

## What this means

One or more dependencies use a licence that is incompatible with the project's distribution model
or creates legal obligations the team may not intend to meet. This ranges from Major (weak copyleft
like LGPL requiring dynamic linking) to Critical (strong copyleft like AGPL/GPL requiring full
source disclosure, or non-OSI licences like SSPL/BUSL that restrict commercial use).

### Licence Risk Tiers

| Tier | Licences | Risk | Obligation |
|------|----------|------|------------|
| **Permissive** | MIT, Apache-2.0, BSD-2/3, ISC, Zlib | Low | Attribution only |
| **Weak copyleft** | LGPL-2.1, LGPL-3.0, MPL-2.0 | Medium | Modifications to the library must be shared; your code stays proprietary if dynamically linked |
| **Strong copyleft** | GPL-2.0, GPL-3.0, AGPL-3.0 | High | Entire derivative work must be distributed under the same licence |
| **Source-available** | SSPL, BUSL, Elastic-2.0 | Critical | Commercial use restricted or prohibited |
| **No licence** | Unlicenced / custom | Critical | No legal permission to use — treat as all rights reserved |

## How to fix

### Step 1: Identify the problematic dependencies

Use ecosystem-specific tools to generate a full licence inventory:

#### Rust

```bash
# Install cargo-deny (one-time)
cargo install cargo-deny

# Initialize config
cargo deny init

# Audit licences
cargo deny check licenses

# Generate full licence list
cargo deny list
```

Configure allowed and denied licences in `deny.toml`:

```toml
[licenses]
allow = ["MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Zlib"]
deny = ["AGPL-3.0", "GPL-3.0", "SSPL-1.0", "BUSL-1.1"]
```

#### Python

```bash
# Using pip-licenses
pip install pip-licenses
pip-licenses --format=table --with-authors

# Using liccheck for policy enforcement
pip install liccheck
liccheck -s setup.cfg  # or liccheck -s pyproject.toml
```

#### TypeScript / JavaScript

```bash
# Using license-checker
npx license-checker --summary
npx license-checker --failOn "GPL-3.0;AGPL-3.0;SSPL-1.0"

# Using license-compliance
npx license-compliance --production --deny "GPL-3.0"
```

#### Go

```bash
# Using go-licenses
go install github.com/google/go-licenses@latest
go-licenses check ./...
go-licenses report ./...
```

### Step 2: Evaluate and resolve

For each flagged dependency:

1. **Verify the licence.** Check the dependency's repository directly — automated tools
   sometimes misidentify licences from partial SPDX expressions.
2. **Assess compatibility.** Compare the dependency's licence against your project's licence
   and distribution model.
3. **Decide: keep, replace, or isolate.**
   - **Keep** if the licence is compatible with your distribution model (document the decision).
   - **Replace** with a permissively-licensed alternative if one exists with comparable quality.
   - **Isolate** behind a process boundary (separate service, CLI subprocess) if the copyleft
     dependency cannot be replaced and must not infect the main codebase.
4. **Document** the decision and rationale for audit traceability.

### Step 3: Update attribution

Ensure all retained dependencies have proper attribution in NOTICE, THIRD-PARTY-LICENCES, or
equivalent files per their licence requirements.

## Prevention

- Add licence auditing to CI: `cargo deny check licenses`, `npx license-checker --failOn`,
  `liccheck`, or `go-licenses check` as a lint-stage job.
- Maintain an explicit allowlist of approved licences in the repository.
- Review dependency licence as part of every MR that adds a new dependency.
- Audit the full licence inventory quarterly.
