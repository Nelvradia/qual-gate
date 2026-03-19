---
title: dependency-tomographe
status: current
last-updated: 2026-03-17
---

# dependency-tomographe

**Dependency lifecycle scanner — ecosystem-agnostic.** Audits every declared dependency across all package managers found in the project: what is declared, what is actually used, what licences apply, what legal and financial obligations those licences trigger, how healthy each dependency is as a long-term choice, and how sound the version pinning strategy is.

Works by LLM analysis of manifest files, lockfiles, and source imports. Shell commands are optional accelerators — the instrument functions without any specific toolchain installed.

**Covers DR Sections:** S12 (Licensing & Legal), S5 (Security — Supply Chain)

---

## Quick Start

```
"Read instruments/dependency-tomographe/README.md and execute a full dependency scan."
"Read instruments/dependency-tomographe/README.md and execute Phase 3 (Licence Risk Matrix) only."
"Read instruments/dependency-tomographe/README.md and execute Phase 2 (Usage Analysis) only."
```

---

## Scan Phases

| Phase | Name | What It Does | Primary Method |
|-------|------|-------------|----------------|
| **1** | Ecosystem Discovery | Identify all package managers, manifests, and lockfiles present | File discovery + LLM analysis |
| **2** | Usage Analysis | Find declared-but-unused and used-but-undeclared deps | Source import scan + LLM analysis |
| **3** | Licence Risk Matrix | Classify every dependency by licence, flag legal and financial obligations | Manifest + registry metadata + LLM analysis |
| **4** | Dependency Health | Assess maintenance status, abandonment risk, provenance | Manifest metadata + optional registry query |
| **5** | Version & Pinning Discipline | Audit lockfile hygiene, semver drift, wildcard version specs | Manifest + lockfile analysis |
| **6** | Transitive Risk | Deep dependency tree, diamond conflicts, vendored code, proc-macro surface | Lockfile + optional tool output |
| **7** | Report | Compile `DT{n}-dependency.md` | Template filling |

---

## Path Resolution

Before running any phase, resolve these paths from the target project's
`project-profile.yaml`. Use defaults when profile fields are absent.

| Variable | Profile Field | Default |
|----------|--------------|---------|
| `SOURCE_DIRS` | `paths.source_dirs` | `src/` |
| `TEST_DIRS` | `paths.test_dirs` | `tests/` |
| `DOCS_DIR` | `paths.docs_dir` | `docs/` |

Replace all `src/` references in accelerator commands below with
`${SOURCE_DIRS}`.

---

## Phase 1 — Ecosystem Discovery

**Goal:** Build a complete inventory of every package manager present in the project before any other phase runs. Do not assume the stack — discover it.

### How to discover

Read the project root and subdirectories for the following manifest types. If any are found, that ecosystem is in scope for all subsequent phases.

| Ecosystem | Manifest files | Lockfiles |
|-----------|---------------|-----------|
| Rust | `Cargo.toml` (workspace + member crates) | `Cargo.lock` |
| Node / npm | `package.json` | `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml` |
| Python | `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements*.txt` | `poetry.lock`, `Pipfile.lock`, `uv.lock` |
| Go | `go.mod` | `go.sum` |
| Java / Kotlin | `pom.xml`, `build.gradle`, `build.gradle.kts` | `gradle.lockfile` |
| Ruby | `Gemfile` | `Gemfile.lock` |
| PHP | `composer.json` | `composer.lock` |
| Swift / ObjC | `Package.swift`, `Podfile` | `Package.resolved`, `Podfile.lock` |
| C / C++ | `conanfile.txt`, `conanfile.py`, `vcpkg.json` | `conan.lock` |
| Dart / Flutter | `pubspec.yaml` | `pubspec.lock` |
| .NET | `*.csproj`, `*.fsproj`, `packages.config` | `packages.lock.json` |

```bash
# Accelerator: find all manifest files from project root
find . \
  -name 'Cargo.toml' -o -name 'package.json' -o -name 'pyproject.toml' \
  -o -name 'requirements*.txt' -o -name 'go.mod' -o -name 'pom.xml' \
  -o -name 'build.gradle' -o -name 'build.gradle.kts' -o -name 'Gemfile' \
  -o -name 'composer.json' -o -name 'Package.swift' -o -name 'pubspec.yaml' \
  -o -name '*.csproj' -o -name 'conanfile.*' -o -name 'vcpkg.json' \
  2>/dev/null | grep -v '/node_modules/' | grep -v '/vendor/' | grep -v '/target/' \
  | sort
```

### LLM steps

1. Read every discovered manifest file
2. For each ecosystem, extract: direct dependencies (name, declared version), development-only dependencies (if the ecosystem distinguishes them), optional/conditional dependencies
3. Record the scope: Is this a library, an application binary, a build tool? This affects which licence obligations apply
4. Note whether a lockfile exists for each manifest — absence is a finding in Phase 5

### Deliverable

A dependency inventory table per ecosystem:

| Ecosystem | Manifest | Direct Deps | Dev-Only Deps | Lockfile Present |
|-----------|----------|------------|---------------|-----------------|
| Rust | Cargo.toml | N | N | Yes/No |
| Node | package.json | N | N | Yes/No |
| … | … | … | … | … |

---

## Phase 2 — Usage Analysis

> **Prerequisite:** This phase requires installed dependencies or importable
> source. When absent, emit `Observation: "dependency-tomographe Phase 2
> skipped — no importable source found"` and proceed to Phase 3.

**Goal:** Find the gap between what is declared in manifests and what is actually imported in source code. Unused dependencies carry licence obligations and supply chain risk with zero benefit.

### LLM steps

1. For each discovered ecosystem, identify the source directories (e.g. `src/`, `lib/`, `app/`)
2. Scan source files for import/use statements and collect the set of top-level package names actually referenced
3. Compare against the declared direct dependency list from Phase 1
4. Flag: declared but never imported, and imported but not declared (the latter implies an undeclared transitive dependency is being relied upon directly)

**Important nuances to reason about:**

- A dependency may be used only in tests — that is fine if it is declared as a dev dependency, but a finding if declared as a production dependency
- A dependency may be used only in build scripts or macros — note this separately, as it may affect licence analysis (build-time vs link-time use)
- Some dependencies are purely feature-flag gated — check if the feature is enabled in the manifest
- Re-exports: a crate/package may import and re-export another; the re-exported package still counts as used

### Accelerator tools (optional)

```bash
# Rust
cargo machete 2>/dev/null          # finds unused direct deps
cargo +nightly udeps --all-targets 2>/dev/null  # more thorough, requires nightly

# Node
npx depcheck 2>/dev/null

# Python
pip install pip-autoremove 2>/dev/null && pip-autoremove --leaves 2>/dev/null
# or: pipreqs --print 2>/dev/null (lists actually-imported packages)

# Go
go mod tidy --diff 2>/dev/null    # shows what would be added/removed

# Lightweight TS/JS import scan (when node_modules not installed)
# Extract import names from source
grep -rh 'import.*from\s' ${SOURCE_DIRS} --include='*.ts' --include='*.js' | \
  sed "s/.*from ['\"]\\([^'\"]*\\)['\"].*/\\1/" | sort -u > /tmp/imports.txt
# Compare with package.json dependencies
jq -r '.dependencies // {} | keys[]' package.json | sort > /tmp/declared.txt
# Declared but not imported (candidates for removal)
comm -23 /tmp/declared.txt /tmp/imports.txt
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Direct production dependency with no imports anywhere in source | **Minor** |
| Direct production dependency used only in test code | **Minor** (should be dev dep) |
| Package imported in source but not declared in manifest (relying on transitive) | **Major** |
| Dev dependency bundled into production artefact | **Major** |
| Build-time-only dependency declared as runtime dependency | **Observation** |

---

## Phase 3 — Licence Risk Matrix

**Goal:** Classify every dependency — direct and transitive — by its licence, identify the obligations it triggers, and flag any that constitute a legal or financial risk.

This phase operates on the full dependency set from Phase 1 (not just used ones — even unused declared deps carry obligations until removed).

### Licence classification tiers

| Tier | Licence examples | Obligations | Default severity if present |
|------|-----------------|-------------|----------------------------|
| **Public domain** | CC0, Unlicense, 0BSD | None | OK |
| **Permissive** | MIT, Apache-2.0, BSD-2-Clause, BSD-3-Clause, ISC | Attribution in NOTICE file | OK (if attributed) |
| **Permissive with patent grant** | Apache-2.0 | Attribution + no patent retaliation clause | OK — note: MIT lacks the patent grant, relevant for patent-sensitive products |
| **Weak copyleft** | LGPL-2.1, LGPL-3.0, MPL-2.0, CDDL, EUPL | Modifications to the licensed files must be published; dynamic linking may satisfy | **Minor** — needs documented linking strategy |
| **Strong copyleft** | GPL-2.0, GPL-3.0 | Entire binary must be GPL; source must be offered | **Critical** if statically linked into a distributed binary |
| **Network copyleft** | AGPL-3.0, EUPL-1.2 (some interpretations) | Network use counts as distribution — SaaS is not a loophole; source must be offered to all users | **Critical** — no commercial deployment escape hatch |
| **Commercial restriction** | BUSL-1.1, Commons Clause addendum, BSL, SSPL-1.0 | Production / commercial use prohibited or requires a paid licence | **Critical** if used in production |
| **Proprietary / No licence** | Closed source, no SPDX identifier, README-only licence | Cannot be redistributed; may require royalty; legal exposure | **Critical** |
| **Creative Commons (non-code)** | CC-BY, CC-BY-SA, CC-BY-NC | Usually fine for data/assets; NC restricts commercial use | Assess per asset — CC-NC in commercial product = **Major** |
| **Unknown** | No licence field, no LICENSE file | Legally: all rights reserved by default; cannot be used commercially without permission | **Critical** |

### Copyleft propagation rules to reason about

These are the common mistakes. Reason about each carefully:

1. **Static linking vs dynamic linking** — GPL in a statically linked binary contaminates the whole binary. GPL in a dynamically linked shared library may not (LGPL is designed for this). Determine the link type for each copyleft dep.
2. **Build-time only** — A GPL build tool (e.g. a code generator) used only at build time does not necessarily contaminate the output artefact. Reason about whether the dep's output is embedded in the binary.
3. **Test-only** — A GPL test framework linked only in test binaries does not contaminate the production binary. Confirm it is not in the production dependency closure.
4. **AGPL and internal services** — AGPL applies to network access, not just distribution. An internal microservice using AGPL is still obligated if users interact with it over a network.
5. **Licence compatibility** — Apache-2.0 and GPL-2.0 are incompatible (the patent clause conflicts). Apache-2.0 and GPL-3.0 are compatible. Flag any combinations that cannot legally coexist.

### Royalty and financial obligation checks

These are the cases most automated tools miss:

- **BUSL-1.1 (Business Source Licence):** Has a "Change Date" after which it converts to a permissive licence. Read the Change Date field — if it is in the future, commercial production use requires a commercial licence from the vendor.
- **Commons Clause addendum:** Bolt-on restriction that prohibits "selling" the software. This affects SaaS offerings — "selling a service" is broadly interpreted.
- **SSPL-1.0 (MongoDB, Elasticsearch):** Requires open-sourcing all software used to offer the licensed software as a service — includes your entire stack if you expose it via an API.
- **Dual-licensed packages:** Some packages are MIT _or_ GPL depending on how they are used. Read the licence carefully — the permissive option may require purchasing a commercial licence.
- **Font and asset licences:** Fonts embedded in desktop applications often have separate SIL OFL or commercial licence requirements. OFL is generally permissive but prohibits selling the font alone.

### LLM steps

1. For each dependency in the full list from Phase 1, determine its licence:
   - Read the `license` field in the manifest (Cargo.toml, package.json, pyproject.toml, etc.)
   - If the field is absent, check for a LICENSE or COPYING file in vendored or downloaded source
   - If still absent, record as **Unknown**
2. Classify against the tier table above
3. For each weak/strong/network copyleft dep: determine link type and propagation risk
4. For each commercial restriction dep: check whether the project's deployment model triggers the restriction
5. For each unknown licence dep: flag immediately as Critical
6. Check whether an attribution file exists (`NOTICE`, `NOTICE.md`, `ATTRIBUTION.md`, `CREDITS`) and whether it covers all permissive deps

### Accelerator tools (optional)

```bash
# Rust
cargo license 2>/dev/null                          # list all dep licences
cargo deny check licenses 2>/dev/null              # policy enforcement (requires deny.toml)

# Node
npx license-checker --summary 2>/dev/null
npx license-checker --json 2>/dev/null > /tmp/node-licences.json

# Python
pip-licenses 2>/dev/null                           # pip install pip-licenses
# or: python -m pip show <package> | grep License

# Go
go-licenses csv ./... 2>/dev/null                  # github.com/google/go-licenses

# Java / Kotlin (Gradle)
./gradlew dependencies 2>/dev/null | grep -E 'licen'
# or use license-gradle-plugin if configured
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| AGPL-3.0 dep reachable from any networked service | **Critical** |
| GPL-2.0 / GPL-3.0 dep statically linked into distributed binary | **Critical** |
| SSPL-1.0 dep in any service exposed via API | **Critical** |
| BUSL / Commons Clause dep in commercial deployment | **Critical** |
| Unknown / no-licence dep (any use) | **Critical** |
| Licence incompatibility (e.g. Apache-2.0 + GPL-2.0 in same binary) | **Critical** |
| LGPL dep with no documented linking strategy | **Major** |
| MPL-2.0 dep with modifications and no disclosure plan | **Major** |
| CC-NC asset in commercial product | **Major** |
| Permissive dep missing from attribution file | **Minor** |
| GPL dep used only in build tooling (not in output binary) | **Observation** — document explicitly |
| Apache-2.0 dep in patent-sensitive product (vs MIT) | **Observation** — note the patent grant advantage |

---

## Phase 4 — Dependency Health

**Goal:** Assess each direct dependency as a long-term choice. A dependency that is technically licence-clean today can become a liability if abandoned, transferred to a new owner, or relicensed.

### What to assess per dependency

For each direct dependency, reason about the following signals:

| Signal | What to look for | Finding threshold |
|--------|-----------------|-------------------|
| **Maintenance activity** | Release recency, open issue responsiveness, commit frequency | No release in >2 years = **Minor**; no activity in >3 years = **Major** |
| **Advisory database flags** | Is the dep flagged as `unmaintained` or `deprecated` in cargo-audit, npm audit, OSV, etc. | Any `unmaintained` advisory = **Major** |
| **Yanked / retracted versions** | Is the version in the lockfile yanked/retracted in the registry | **Major** |
| **Git-sourced deps** | Is the dep pinned to a git commit instead of a registry version | **Major** — no registry audit trail, no reproducible provenance |
| **Bus factor** | Single maintainer with no org backing, no co-maintainers | **Observation** — document, watch closely |
| **Ownership transfers** | Packages that have changed hands (common in npm) are a supply chain risk | **Observation** — flag for manual review |
| **Licence change history** | Has the dep changed licence in the past? (Commons Clause additions are a known pattern) | **Observation** — check current licence is still what was originally evaluated |

### Accelerator tools (optional)

```bash
# Rust — advisory database includes unmaintained flags
cargo audit 2>/dev/null | grep -i 'unmaintained\|warning'

# Node — npm audit flags deprecated packages
npm audit 2>/dev/null | grep -i 'deprecated\|no longer maintained'

# Python
pip audit 2>/dev/null

# Cross-ecosystem: OSV scanner (https://osv.dev)
# osv-scanner --lockfile Cargo.lock --lockfile package-lock.json 2>/dev/null
```

### LLM analysis when tools are unavailable

Read the lockfile and manifest. For each direct dependency:
1. Note the pinned version
2. Reason about whether this is a widely used, well-maintained package based on the name, ecosystem, and any available README/metadata in vendored or local source
3. Flag any deps that appear to be forks, personal projects without org backing, or packages with `_legacy`, `_deprecated`, or `_old` in the name

### Severity Rules

| Finding | Severity |
|---------|----------|
| Dep flagged `unmaintained` in advisory database | **Major** |
| Dep with yanked / retracted version in lockfile | **Major** |
| Dep sourced from git commit (not registry) | **Major** |
| Dep with no registry release in >2 years | **Minor** |
| Dep with single individual maintainer, no org | **Observation** |
| Dep that has transferred ownership in the past | **Observation** |

---

## Phase 5 — Version & Pinning Discipline

**Goal:** Ensure the project's dependency version strategy is reproducible, auditable, and doesn't allow silent version drift.

### What to check

**Lockfile discipline:**
- Does every manifest have a corresponding lockfile committed to version control?
- A missing lockfile means every fresh install can resolve to a different version — non-reproducible builds, silent security regressions
- Exception: libraries (not applications) conventionally do not commit lockfiles, because they need to test against the full range of declared constraints

**Version constraints in manifests:**
- Wildcard (`*`) or unbounded ranges (`>=1.0`) allow any future version to be resolved silently — this includes breaking changes and malicious releases
- In application manifests, prefer exact versions or tight caret/tilde ranges with a ceiling
- In library manifests, ranges are expected but should have a realistic ceiling

**Semver lag:**
- A dep many major versions behind its current release means the project is carrying unpatched CVEs and missing security fixes
- Minor/patch lag is lower priority but still worth flagging at scale

### LLM steps

1. Read each manifest and note every version constraint format
2. Identify: exact pins, caret (`^`), tilde (`~`), ranges (`>=`, `<=`), wildcards (`*`), path/git references
3. Compare manifest declared versions against lockfile pinned versions — large gaps indicate the manifest is underspecified
4. Flag: missing lockfiles, wildcard constraints, manifest-to-lockfile version gaps beyond one major version

### Accelerator tools (optional)

```bash
# Rust
cargo outdated 2>/dev/null             # shows current vs latest
cargo outdated --depth 1 2>/dev/null   # direct deps only

# Node
npm outdated 2>/dev/null

# Python
pip list --outdated 2>/dev/null

# Go
go list -u -m all 2>/dev/null

# Check lockfile is committed
git ls-files | grep -E 'Cargo\.lock|package-lock\.json|yarn\.lock|poetry\.lock|go\.sum|Gemfile\.lock|composer\.lock'
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Application manifest with no lockfile committed | **Critical** |
| Wildcard version constraint (`*`) in any manifest | **Minor** |
| Unbounded range constraint with no ceiling | **Minor** |
| Direct dep ≥2 major versions behind current release | **Minor** |
| Git or path reference instead of registry version | **Major** (see also Phase 4) |
| Library manifest with committed lockfile — not a finding, but note it | **Observation** |

---

## Phase 6 — Transitive Risk

**Goal:** Assess the shape and risk of the full transitive dependency tree — the dependencies of dependencies.

Direct dependencies are the visible surface; the real supply chain risk lives in the transitive closure.

### What to assess

**Tree size and depth:**
- Total transitive dependency count is a measure of supply chain attack surface
- Very deep chains (dep A → dep B → dep C → ... → dep N) mean a vulnerability anywhere in the chain affects you
- Very wide single deps (one package pulling in 50+ transitive deps) are high-leverage targets

**Diamond conflicts:**
- Two deps requiring incompatible versions of the same transitive dep
- In ecosystems with deduplication (Go, Node), this can cause one version to silently win
- In ecosystems without deduplication (Rust allows multiple versions in the same binary), this causes binary bloat and potentially inconsistent behaviour between codepaths

**Vendored dependencies:**
- Code checked into the repo under `vendor/`, `third_party/`, `external/`, or similar
- Must be attributed in the NOTICE/ATTRIBUTION file
- Must have their own LICENSE files present
- Must be tracked in the manifest/lockfile (not just copied in)
- Must have a documented update strategy (how will CVEs in vendored code be picked up?)

**Proc-macro and build-script surface (Rust-specific, but analogous patterns exist in other ecosystems):**
- Proc-macros execute arbitrary code at compile time
- Build scripts (`build.rs`) run arbitrary code at build time
- Any dep that includes these deserves elevated scrutiny — compromise of the dep = compromise of every project that builds with it

**Code-generation and metaprogramming deps (general):**
- Any dep that generates code during the build (Babel transforms, code generators, annotation processors) executes at build time with full filesystem access
- These should be pinned more strictly than runtime deps

### LLM steps

1. Read the lockfile(s) — the lockfile contains the full transitive closure with pinned versions
2. Count total unique packages in the lockfile vs unique packages in the manifest (the delta is the transitive surface)
3. Identify duplicate package names at different versions (diamond conflicts)
4. Search the repo for `vendor/`, `third_party/`, `external/`, `libs/` directories — assess attribution
5. Identify any dep with a build script, code generator, or macro capability

### Accelerator tools (optional)

```bash
# Rust
cargo tree --workspace 2>/dev/null | wc -l                    # total nodes
cargo tree --workspace --duplicates 2>/dev/null               # diamond conflicts
cargo tree --workspace --edges features 2>/dev/null           # feature-activated paths

# Node
npm ls --all 2>/dev/null | wc -l
npm ls --all --json 2>/dev/null | jq '[.. | .version? // empty] | length'

# Go
go mod graph 2>/dev/null | wc -l

# Vendored code attribution check
find vendor/ third_party/ external/ -name 'LICENSE*' -o -name 'NOTICE*' 2>/dev/null | \
  xargs -I{} dirname {} | sort -u
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Diamond conflict on a security-relevant package (crypto, TLS, auth) | **Critical** |
| Vendored code with no LICENSE file present | **Major** |
| Vendored code not listed in NOTICE/ATTRIBUTION file | **Major** |
| Vendored code with no documented update/CVE-monitoring strategy | **Major** |
| Diamond conflict causing duplicate in binary (not just resolution) | **Minor** |
| Build-time code-executing dep with no pinned version | **Major** |
| Total transitive dep count >500 | **Observation** — document; not a blocker |
| Single dep pulling in >50 transitive deps | **Observation** |

---

## Phase 7 — Report

Compile all phase outputs into `output/YYYY-MM-DD_{project_name}/DT{n}-dependency.md` (see `qualitoscope/config.yaml` for `project_name`) using the report template.

The report must include:

1. **Executive summary** — total deps across all ecosystems, overall verdict, count by severity
2. **Ecosystem inventory** — Phase 1 table
3. **Usage gaps** — Phase 2 findings: unused deps, undeclared imports
4. **Licence risk register** — Phase 3: every non-permissive dep with its obligation, propagation analysis, and required action
5. **Health register** — Phase 4: unmaintained, yanked, git-sourced deps
6. **Pinning assessment** — Phase 5: missing lockfiles, wildcard constraints, semver lag
7. **Transitive surface** — Phase 6: tree size, diamond conflicts, vendored code
8. **Action register** — all findings with severity, owner, and recommended action

---

## Severity & Verdict

| Verdict | Condition |
|---------|-----------|
| **PASS** | 0 Critical, 0 Major |
| **CONDITIONAL** | 0 Critical, ≤2 Major with documented tracking issues |
| **FAIL** | ≥1 Critical, OR untracked Major |

**Critical findings that demand immediate action:**
- Any AGPL/GPL/SSPL dep in a distributed or networked product
- Any Unknown/no-licence dep
- Any BUSL/Commons Clause dep in commercial production
- Any licence incompatibility pair in the same binary
- Missing lockfile for an application manifest

---

## Configuration

This instrument reads project-specific paths from `project-profile.yaml` in the target project root. If a profile field is absent, the default from the profile schema applies. Instrument-specific thresholds remain in this instrument's `config.yaml`.

---

## Run History

| Run | Date | Trigger | Report |
|-----|------|---------|--------|
| DT1 | _pending_ | Initial baseline | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
