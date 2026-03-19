---
title: "Getting Started with qual-gate"
status: current
last-updated: 2026-03-19
---

# Getting Started with qual-gate

qual-gate is a suite of quality diagnostic instruments designed to be run by an AI coding
assistant (Claude Code, Cursor, etc.) against any software project. This guide walks you
through your first scan.

---

## Prerequisites

- An AI coding assistant with file read/write access to your terminal and project files
- Git (to clone qual-gate)
- Your target project checked out locally

qual-gate has no runtime dependencies — it is a methodology library, not executable software.
The AI assistant reads the instrument instructions and executes the prescribed checks against
your codebase.

---

## Step 1 — Clone qual-gate

```bash
git clone https://gitlab.example.com/nelvradia/qual-gate.git
cd qual-gate
```

Place qual-gate alongside your project or in any accessible location. The instruments
reference your project by path.

---

## Step 2 — Point qual-gate at your project

Open `qualitoscope/config.yaml` and set the `project_name` field as a fallback:

```yaml
project_name: "my-project"
```

This is only needed if you skip auto-discovery. When a `project-profile.yaml` exists in
your target project, the name is read from there instead.

---

## Step 3 — Run Auto-Discovery (Phase 0)

If your project does not yet have a `project-profile.yaml`, ask your AI assistant:

```
Read qual-gate/qualitoscope/methods/00-auto-discovery.md and run Phase 0 against
/path/to/my-project.
```

Phase 0 scans your project for:
- **Languages** — file extensions, build manifests (`Cargo.toml`, `pyproject.toml`, etc.)
- **Build systems** — Cargo, CMake, setuptools, Vite, Webpack, etc.
- **CI platform** — GitLab CI, GitHub Actions, Azure Pipelines, Jenkins
- **Directory layout** — source dirs, test dirs, docs, config
- **Platforms** — web, mobile, desktop, CLI, embedded
- **Toggles** — permission system, AI/ML components, GDPR scope, AI Act scope

**Output:** A draft `project-profile.yaml` in your project root, annotated with confidence
tags and `# VERIFY:` comments.

---

## Step 4 — Review and confirm the profile

Open the generated `project-profile.yaml` and verify:

1. **Required fields** — `name` and `stack.languages` must be correct
2. **Paths** — confirm `source_dirs`, `test_dirs`, `docs_dir` match your layout
3. **Toggles** — enable `permission_system`, `ai_ml_components`, `gdpr_scope`, or
   `ai_act_scope` if they apply to your project
4. **Architecture** — set `layers` and `boundary_marker` if you want layer violation checks

A minimal viable profile is just:

```yaml
name: my-project
stack:
  languages: [python]
```

Everything else defaults to sensible conventions. See
[Project Profile Reference](./project-profile-reference.md) for field-by-field documentation.

---

## Step 5 — Run a single instrument scan

Start with one instrument to see how qual-gate works before running the full suite.
The code quality instrument is a good first choice:

```
Read qual-gate/instruments/code-tomographe/README.md and execute a full code quality
scan against /path/to/my-project.
```

The assistant will:
1. Read the instrument's methodology (`methods/` directory)
2. Load your project profile for path and stack configuration
3. Execute each scanning phase against your codebase
4. Produce a structured report with severity-rated findings

**Output location:** `qual-gate/output/YYYY-MM-DD_my-project/CQ1-code.md`

---

## Step 6 — Run a full qualitoscope scan

Once you're comfortable with single-instrument output, run the full orchestrator:

```
Read qual-gate/qualitoscope/README.md and execute a full Qualitoscope scan against
/path/to/my-project.
```

The orchestrator runs all 13 instruments in sequence:

| Phase | What happens |
|-------|-------------|
| 0 | Auto-discovery (skipped if profile exists) |
| 1 | Profile validation and instrument inventory |
| 2 | Delegation — each instrument scans your project |
| 3 | Overlap resolution — deduplicates shared findings |
| 4 | Cross-correlation — detects multi-instrument patterns |
| 5 | S14 aggregation — composite score and verdict |
| 6 | DR synthesis (DR Mode only) |
| 7 | Delta analysis (if previous runs exist) |
| 8 | Final report compilation |

**Output:** A full set of instrument reports plus the unified `QS-qualitoscope.md` in
`output/YYYY-MM-DD_my-project/`.

---

## Step 7 — Reading the output report

Each instrument report follows a consistent structure:

### Severity levels

| Severity | Meaning | Action |
|----------|---------|--------|
| **Critical** | Blocks release | Must fix before proceeding |
| **Major** | Significant risk | Should fix in current phase |
| **Minor** | Low risk | Track and fix when convenient |
| **Observation** | Informational | No action required |
| **OK** | Check passed | Nothing to do |

### Report sections

- **Executive Summary** — overall verdict and finding counts by severity
- **Findings** — each finding includes: ID, title, severity, evidence, and remediation link
- **Action Register** — prioritised list of findings requiring action

### Verdict

The qualitoscope report includes an overall verdict:
- **PASS** — no Critical or Major findings
- **CONDITIONAL PASS** — Major findings exist but are manageable
- **FAIL** — Critical findings exist that block release

---

## Step 8 — Using fix guides

Every finding links to a fix guide in the instrument's `fixes/` directory. Fix guides
provide:

1. **What this means** — why the finding matters
2. **How to fix** — language-specific remediation with code examples
3. **Prevention** — CI checks and tooling to prevent recurrence

Example: if the security instrument reports "Hardcoded Secrets," read:

```
qual-gate/instruments/security-tomographe/fixes/hardcoded-secrets.md
```

---

## Worked Example — Python/FastAPI Project

Imagine you have a FastAPI project at `/home/user/projects/my-api/`:

```
my-api/
├── src/
│   ├── main.py
│   ├── routes/
│   ├── services/
│   └── models/
├── tests/
│   ├── unit/
│   └── integration/
├── docs/
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── .gitlab-ci.yml
```

### 1. Auto-discovery generates this profile:

```yaml
name: my-api
stack:
  languages: [python]
  build_systems: [setuptools]
  ci_platform: gitlab-ci
  package_managers: [pip]
paths:
  source_dirs: [src/]
  test_dirs: [tests/]
  docs_dir: docs/
  ci_config: .gitlab-ci.yml
  compose_files: [docker-compose.yml]
toggles:
  permission_system: false
  ai_ml_components: false
  gdpr_scope: false    # VERIFY: check if your API handles personal data
  ai_act_scope: false
```

### 2. You review it, enable `gdpr_scope: true` since the API handles user data.

### 3. Run a single scan:

```
Read qual-gate/instruments/security-tomographe/README.md and execute a security scan
against /home/user/projects/my-api.
```

### 4. The report finds:
- **Critical:** Hardcoded database password in `src/main.py`
- **Major:** Container running as root in `Dockerfile`
- **Minor:** Missing rate limiting on `/api/auth/login`

### 5. You use the fix guides to resolve each finding, starting with Critical.

### 6. Re-run to confirm findings are resolved.

---

## Next Steps

- **[Project Profile Reference](./project-profile-reference.md)** — full field-by-field
  documentation
- **[Instrument Authoring Guide](./instrument-authoring-guide.md)** — create custom
  instruments
- **Individual instrument READMEs** — deep-dive into any instrument's methodology
