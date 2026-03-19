---
title: "Project Profile Reference"
status: current
last-updated: 2026-03-19
---

# Project Profile Reference

Complete field-by-field reference for `project-profile.yaml` — the single source of
project-specific configuration consumed by all qual-gate instruments.

Place this file in the root of the target project. Only `name` and `stack.languages`
are required; everything else has convention-based defaults.

Schema definition: `qual-gate/project-profile.schema.yaml`
Annotated example: `qual-gate/project-profile.example.yaml`

---

## Minimal Viable Profile

```yaml
name: my-project
stack:
  languages: [python]
```

This is sufficient to run all instruments. Paths default to conventions (`src/`, `tests/`,
`docs/`), toggles default to `false`, and optional fields are `null`.

---

## Inheritance

Profiles support single-parent inheritance via the `extends` field. A child profile
inherits all fields from the parent and overrides selectively.

| Field | Type | Required | Default | Consumed By |
|-------|------|----------|---------|-------------|
| `extends` | string | no | null | qualitoscope |

### Merge Semantics

| Value Type | Behaviour | Example |
|------------|-----------|---------|
| **Scalar** (string, number, bool) | Child overrides parent | `name: child-project` replaces parent's name |
| **List** | Child **replaces** parent entirely | `languages: [rust]` replaces parent's `[python, go]` |
| **Object** | Deep merge — child keys override, parent keys preserved | Child adds `paths.db_dir` without losing parent's `paths.source_dirs` |
| **Toggles** | Child can only **enable**, never disable | Parent `permission_system: true` cannot be set to `false` by child |

### Toggle Safety Rule

A parent profile that enables a toggle establishes a quality floor. Child profiles
can enable additional toggles but cannot disable inherited ones. Attempting to set
a parent-enabled toggle to `false` is a validation error.

### Depth Limit

Inheritance chains are limited to **3 levels** (child → parent → grandparent). A
4th level triggers a validation error. This prevents fragile deep chains and keeps
profiles easy to reason about.

### Circular Reference Detection

The resolver tracks all visited profile paths. If a path appears twice in the
resolution chain, it raises a validation error with the full cycle path.

### Examples

**Single-level inheritance:**

```yaml
# profiles/base.yaml
name: base-project
stack:
  languages: [python, rust]
toggles:
  permission_system: true

# project-profile.yaml
extends: ./profiles/base.yaml
name: my-project                  # overrides base name
stack:
  languages: [python]             # replaces base languages list
toggles:
  gdpr_scope: true                # enables additional toggle
  # permission_system: inherited as true from parent
```

**Multi-level inheritance:**

```yaml
# profiles/org-base.yaml
name: org-default
stack:
  languages: [python]
toggles:
  permission_system: true

# profiles/team-base.yaml
extends: ./profiles/org-base.yaml
stack:
  languages: [python, typescript]
toggles:
  gdpr_scope: true

# project-profile.yaml
extends: ./profiles/team-base.yaml
name: my-project
# Inherits: permission_system=true, gdpr_scope=true, languages=[python, typescript]
# Can override name, paths, etc.
```

---

## identity

Project metadata used in output naming and report headers.

| Field | Type | Required | Default | Consumed By |
|-------|------|----------|---------|-------------|
| `name` | string | **yes** | — | qualitoscope |
| `version` | string | no | null | deployment, documentation |
| `repo_url` | string | no | null | qualitoscope, compliance |

### name

Human-readable project name. Used in the output folder path:
`output/YYYY-MM-DD_{name}/`.

### version

Current project version (SemVer). When present, instruments check version consistency
across `VERSION` files, `Cargo.toml`, `package.json`, and documentation references.
When absent, version-related checks are skipped.

### repo_url

Repository URL. Used in report links and licence attribution output. No default — if
absent, reports omit repository links.

---

## stack

Technology stack declaration. Drives language-specific behaviour across all instruments.

| Field | Type | Required | Default | Consumed By |
|-------|------|----------|---------|-------------|
| `languages` | list[string] | **yes** | — | code, test, security, dependency |
| `build_systems` | list[string] | no | [] | deployment, code |
| `ci_platform` | string | no | `gitlab-ci` | deployment, security |
| `package_managers` | list[string] | no | [] | dependency, security |

### languages

Programming languages used in the project. Determines which linters, formatters, and
language-specific checks each instrument applies. Minimum one entry.

**Recognised values:** `python`, `rust`, `typescript`, `javascript`, `go`, `java`,
`kotlin`, `cpp`, `c`, `csharp`, `ruby`, `swift`, `dart`

### build_systems

Build systems in use. Used by deployment-tomographe for build reproducibility checks and
code-tomographe for build configuration analysis.

**Examples:** `cargo`, `cmake`, `setuptools`, `poetry`, `vite`, `webpack`, `gradle`,
`maven`, `bazel`, `make`

### ci_platform

CI platform identifier. Determines which CI configuration files to look for and which
CI-specific checks to run.

**Allowed values:** `gitlab-ci`, `github-actions`, `azure-pipelines`, `jenkins`, `circleci`

### package_managers

Package managers in use. Used for dependency and lockfile analysis.

**Examples:** `cargo`, `npm`, `pnpm`, `yarn`, `pip`, `poetry`, `pipenv`, `go`

---

## paths

Project layout consumed by instruments for file discovery. All paths are relative to
the project root.

| Field | Type | Required | Default | Consumed By |
|-------|------|----------|---------|-------------|
| `source_dirs` | list[string] | no | `["src/"]` | code, test, architecture, security, observability, ai-ml |
| `test_dirs` | list[string] | no | `["tests/"]` | test |
| `docs_dir` | string | no | `"docs/"` | documentation |
| `config_dir` | string | no | `"config/"` | compliance, data |
| `ci_config` | string | no | `".gitlab-ci.yml"` | deployment, security |
| `compose_files` | list[string] | no | `["docker-compose.yml"]` | deployment, security, performance |
| `version_files` | list[string] | no | `["VERSION"]` | deployment, documentation |
| `operations_docs` | string | no | `"docs/operations/"` | deployment, documentation |
| `db_dir` | string | no | null | data |
| `backup_scripts` | string | no | null | data |
| `ui_source_dirs` | list[string] | no | `[]` | ux |

### Key behaviours

- **null fields** cause consuming instruments to skip related checks entirely. For example,
  `db_dir: null` means data-tomographe skips migration integrity checks.
- **Empty lists** (`[]`) are treated as "not applicable," not "use default." If you set
  `ui_source_dirs: []`, UX checks for frontend code are skipped.
- **Globs** are supported in list fields: `test_dirs: [tests/, apps/*/tests/]`.

---

## conventions

Instrument-specific paths that only apply if the project uses them. Every field defaults
to `null`, meaning the related checks are skipped.

| Field | Type | Default | Consumed By |
|-------|------|---------|-------------|
| `access_control_config` | string | null | compliance, security |
| `component_manifest` | string | null | compliance |
| `boundary_tests` | string | null | compliance |
| `business_docs` | string | null | compliance |
| `glossary_script` | string | null | documentation |
| `schema_map` | string | null | documentation, data |
| `metrics_doc` | string | null | documentation, observability |
| `design_docs` | string | null | documentation |
| `adrs` | string | null | documentation, architecture |
| `gap_docs` | string | null | documentation |
| `dr_runbook` | string | null | data |
| `alert_rules` | string | null | observability |
| `dashboards` | string | null | observability |
| `metrics_source_dirs` | list[string] | [] | observability |
| `personality_files` | list[string] | [] | ux, ai-ml |
| `golden_dir` | string | null | ai-ml |
| `rag_eval_dir` | string | null | ai-ml |
| `routing_dataset` | string | null | ai-ml |
| `eval_script` | string | null | ai-ml |
| `ux_spec` | string | null | ux |

These fields are only relevant if your project has the corresponding feature. A Python
REST API with no AI/ML components would leave all `golden_dir`, `rag_eval_dir`,
`routing_dataset`, and `eval_script` fields at null.

---

## platforms

Platform-specific checks and service endpoints.

| Field | Type | Required | Default | Consumed By |
|-------|------|----------|---------|-------------|
| `targets` | list[string] | no | [] | security, ux |
| `service_url` | string | no | null | performance |
| `vector_store_url` | string | no | null | ai-ml, data |

### targets

Deployment targets. Enables platform-specific security and UX checks.

**Recognised values:** `web`, `mobile`, `desktop`, `embedded`, `cli`

- `web` — enables TLS checks, CSP headers, CORS, secure cookies
- `mobile` — enables Android Keystore / iOS Keychain checks
- `desktop` — enables desktop keyring, auto-update, code signing checks
- `embedded` — enables resource constraint and real-time checks
- `cli` — enables argument validation, help text, exit code checks

### service_url

URL of a running service instance. Used by performance-tomographe for live latency and
health checks. Only relevant for services with an HTTP/gRPC interface.

### vector_store_url

URL of the vector store. Used for RAG evaluation by ai-ml-tomographe and data integrity
checks by data-tomographe.

---

## toggles

Enable or disable conditional instrument phases. All default to `false`.

| Field | Type | Default | Consumed By |
|-------|------|---------|-------------|
| `permission_system` | boolean | false | compliance, security |
| `ai_ml_components` | boolean | false | ai-ml, security |
| `gdpr_scope` | boolean | false | data, compliance |
| `ai_act_scope` | boolean | false | compliance, ai-ml |

### permission_system

Set `true` if the project has a permission/RBAC system. Enables:
- Compliance: access control coverage checks (AC1 checklist)
- Security: access control boundary testing (Phase 7)
- Cross-correlation: XC-02 (component without auth entry)

### ai_ml_components

Set `true` if the project includes AI/ML components (LLM integration, prompt engineering,
RAG pipelines, etc.). Enables the full ai-ml-tomographe and AI-specific security checks.

### gdpr_scope

Set `true` if the project processes personal data under GDPR. Enables:
- Data: privacy tier classification checks
- Compliance: data export/deletion endpoint verification, DPIA references

### ai_act_scope

Set `true` if the project falls under EU AI Act scope. Enables:
- Compliance: risk tier classification, conformity assessment documentation
- AI/ML: human oversight verification, transparency requirements

---

## architecture

Structure for architecture-tomographe layer analysis.

| Field | Type | Required | Default | Consumed By |
|-------|------|----------|---------|-------------|
| `boundary_marker` | string | no | null | architecture |
| `layers` | list[string] | no | [] | architecture |
| `entry_points` | list[string] | no | [] | architecture |
| `doc_sources` | list[string] | no | [] | architecture |

### boundary_marker

What constitutes an architectural boundary in your project.

**Values:** `crate` (Rust), `package` (Python/Go/Java), `module` (TypeScript/JS),
`namespace` (C++/C#)

### layers

Ordered list of architectural layers, top to bottom. Used for dependency direction
validation — dependencies should only point downward.

**Example:** `[api, service, domain, infrastructure]`

When empty, architecture-tomographe skips layer violation checks and focuses on
general structural analysis (circular dependencies, god modules).

### entry_points

Application entry point files. Used to trace dependency graphs and validate that
all code is reachable.

### doc_sources

Directories containing architecture documentation. Cross-referenced with actual
code structure for architectural drift detection.

---

## exclude

Glob patterns excluded from all instrument scans.

| Field | Type | Required | Default |
|-------|------|----------|---------|
| (list) | list[string] | no | `["vendor/", "target/", "node_modules/", "build/", "dist/", "__pycache__/", ".git/"]` |

Individual instruments may extend this list via their own `config.yaml` exclude fields
but cannot override (remove) entries from the profile-level list.

Add project-specific exclusions for generated code, vendored dependencies, or large
binary directories.

---

## Stack Example Profiles

### Python / Django

```yaml
name: django-api
stack:
  languages: [python]
  build_systems: [setuptools]
  ci_platform: gitlab-ci
  package_managers: [pip]
paths:
  source_dirs: [myapp/]
  test_dirs: [tests/]
  db_dir: myapp/migrations/
toggles:
  gdpr_scope: true
```

### Rust / Axum

```yaml
name: axum-service
stack:
  languages: [rust]
  build_systems: [cargo]
  ci_platform: gitlab-ci
  package_managers: [cargo]
paths:
  source_dirs: [src/]
  test_dirs: [tests/]
  compose_files: [docker-compose.yml]
architecture:
  boundary_marker: crate
  layers: [api, service, domain, infrastructure]
  entry_points: [src/main.rs]
```

### TypeScript / React

```yaml
name: react-dashboard
stack:
  languages: [typescript]
  build_systems: [vite]
  ci_platform: github-actions
  package_managers: [npm]
paths:
  source_dirs: [src/]
  test_dirs: [src/__tests__/, tests/]
  ci_config: .github/workflows/ci.yml
  ui_source_dirs: [src/]
platforms:
  targets: [web]
```

### Go / gRPC

```yaml
name: grpc-gateway
stack:
  languages: [go]
  build_systems: [make]
  ci_platform: gitlab-ci
  package_managers: [go]
paths:
  source_dirs: [cmd/, internal/, pkg/]
  test_dirs: [internal/, pkg/]
  db_dir: migrations/
architecture:
  boundary_marker: package
  layers: [cmd, internal, pkg]
  entry_points: [cmd/server/main.go]
```

### Multi-language Monorepo

```yaml
name: platform-monorepo
stack:
  languages: [rust, typescript, python]
  build_systems: [cargo, vite, setuptools]
  ci_platform: gitlab-ci
  package_managers: [cargo, npm, pip]
paths:
  source_dirs: [services/api/src/, apps/web/src/, scripts/]
  test_dirs: [services/api/tests/, apps/web/tests/, scripts/tests/]
  ui_source_dirs: [apps/web/src/]
  compose_files: [docker-compose.yml, docker-compose.dev.yml]
platforms:
  targets: [web, cli]
toggles:
  permission_system: true
  ai_ml_components: true
architecture:
  boundary_marker: crate
  layers: [api, service, domain, infrastructure]
```

---

## How Phase 0 Auto-Discovery Populates the Profile

Phase 0 uses heuristics to detect your project's configuration:

| Profile Field | Detection Method |
|---|---|
| `name` | Directory name or `name` from build manifest |
| `languages` | File extensions (`.py`, `.rs`, `.ts`, `.go`, etc.) |
| `build_systems` | Presence of `Cargo.toml`, `pyproject.toml`, `package.json`, etc. |
| `ci_platform` | Presence of `.gitlab-ci.yml`, `.github/workflows/`, etc. |
| `package_managers` | Lockfile presence (`Cargo.lock`, `poetry.lock`, etc.) |
| `source_dirs` | Convention-based (`src/`, `lib/`, `app/`, `cmd/`) + build file refs |
| `test_dirs` | Convention-based (`tests/`, `test/`, `spec/`, `__tests__/`) |
| `docs_dir` | Presence of `docs/`, `doc/`, `documentation/` |
| `platforms.targets` | Android manifests, `ios/`, Electron/Tauri configs, `Dockerfile` |
| `toggles` | Inferred from file patterns (e.g., RBAC config files → `permission_system`) |

Each detected value is tagged with a confidence level:
- `[strict]` — high confidence, derived from explicit manifest data
- `[heuristic]` — medium confidence, derived from conventions and patterns
- `[guessed]` — low confidence, user should verify

See `qualitoscope/methods/00-auto-discovery.md` for full heuristic details.
