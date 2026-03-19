---
title: "Instrument Authoring Guide"
status: current
last-updated: 2026-03-19
---

# Instrument Authoring Guide

This guide covers how to create a new qual-gate instrument (tomographe) and wire it into
the orchestrator. It is intended for contributors and power users who want to extend
qual-gate with custom quality dimensions.

---

## Required Directory Structure

Every instrument lives under `instruments/` and follows this structure:

```
instruments/{name}-tomographe/
├── README.md              # Instrument overview, phases, quick start
├── config.yaml            # Thresholds, severity weights, exclude patterns
├── methods/               # Scanning methodology (one file per phase)
│   ├── 01-{phase-name}.md
│   ├── 02-{phase-name}.md
│   └── ...
├── checklists/            # Structured checklists for manual/LLM checks
│   └── {topic}.md
├── templates/             # Output report templates
│   └── {ID}-{name}.md
└── fixes/                 # Remediation guides
    ├── README.md          # Index of all fix guides
    └── {finding-category}.md
```

### File purposes

| File/Dir | Purpose |
|----------|---------|
| `README.md` | Entry point. The AI assistant reads this first. Contains instrument scope, phases, severity rules, and delegation instructions. |
| `config.yaml` | Instrument-specific thresholds and configuration. Does NOT contain project paths — those come from `project-profile.yaml`. |
| `methods/` | Step-by-step scanning methodology. Each file is one phase. Numbered for execution order. |
| `checklists/` | Structured checklist items. Referenced by method files. |
| `templates/` | Output report templates with placeholders. The assistant fills these in. |
| `fixes/` | Remediation guidance. One file per finding category. See [fixes content standard](../instruments/fixes-content-standard.md). |

---

## Writing Method Files

Method files are the core of an instrument. They tell the AI assistant what to check
and how to check it.

### Structure

```markdown
# Phase N — {Phase Name}

## Goal
{One sentence describing what this phase accomplishes.}

## Steps

### Step 1 — {Step Name}

**LLM step** (or **Accelerator command**)

{Instructions for what to examine, what to look for, and how to evaluate findings.}

### Step 2 — {Step Name}
...

## Severity Rules

| Finding | Severity |
|---------|----------|
| {description} | Critical / Major / Minor / Observation |
```

### LLM Steps vs Accelerator Commands

**LLM steps** are instructions the AI assistant follows using its reasoning and code
reading capabilities:

```markdown
### Step 3 — Check for circular dependencies

**LLM step**

Trace import/use statements across all modules in `${profile.paths.source_dirs}`.
Build a dependency graph. Report any cycles as findings.

For each cycle found:
- List the modules involved in the cycle
- Identify the dependency that should be inverted or extracted
- Rate severity based on cycle length (2 modules = Major, 3+ = Critical)
```

**Accelerator commands** are shell commands the assistant can run for faster, deterministic
results:

```markdown
### Step 2 — Measure test coverage

**Accelerator command** (Python)

```bash
pytest tests/ --cov=src --cov-report=json --cov-report=term-missing 2>/dev/null
```

**Accelerator command** (Rust)

```bash
cargo llvm-cov --workspace --json 2>/dev/null
```

Parse the coverage output. Flag any file below the threshold in `config.yaml`.
```

### Guidelines

1. **Be specific.** "Check for security issues" is too vague. "Search for API endpoints
   that accept user input without validation middleware" is actionable.

2. **Reference profile fields.** Use `${profile.paths.source_dirs}`, `${profile.stack.languages}`,
   etc. to make steps project-agnostic.

3. **Include severity rules.** Every phase must define what severity each type of finding
   receives. Use the unified scale: Critical, Major, Minor, Observation, OK.

4. **Provide examples.** Show what a finding looks like in real code so the assistant
   knows what to flag.

5. **Make phases independent where possible.** Each phase should produce findings that
   don't depend on other phases completing first.

---

## Severity Scale

All instruments use a unified severity scale. Apply it consistently:

| Severity | When to use | Examples |
|----------|------------|---------|
| **Critical** | Blocks release. Active vulnerability, data loss risk, or fundamental design flaw. | Hardcoded secrets, SQL injection, no backups for production DB |
| **Major** | Significant risk. Should fix before next release. | Missing auth on endpoint, no integration tests, container as root |
| **Minor** | Low risk. Track and fix when convenient. | Code style violations, missing docstrings, minor duplication |
| **Observation** | Informational. No action required but worth noting. | Unusual but valid pattern, potential future concern |
| **OK** | Check passed. Nothing to do. | Coverage above threshold, all deps up to date |

### Calibration rules

- A finding is **Critical** only if it represents an active, exploitable risk or would
  cause data loss / system failure.
- Don't inflate severity. If in doubt between two levels, choose the lower one. Users
  lose trust in instruments that cry wolf.
- **OK** findings are valuable — they confirm that the codebase is healthy in that
  dimension. Include them in the report.

---

## Config Schema Conventions

`config.yaml` should contain only instrument-specific thresholds and behaviour flags.
Project paths belong in `project-profile.yaml`.

```yaml
# instruments/example-tomographe/config.yaml

thresholds:
  coverage_minimum: 80        # percent
  complexity_max: 15           # cyclomatic complexity
  duplication_max_lines: 6     # consecutive duplicated lines

severity_weights:
  critical: 10
  major: 5
  minor: 1
  observation: 0

exclude:
  - "*.generated.*"
  - "vendor/"
```

### Rules

1. **Thresholds must have sensible defaults.** A project running with default config
   should get useful results, not noise.

2. **Document each field** with an inline comment explaining units and valid range.

3. **Don't duplicate profile fields.** If the information belongs to the project
   (paths, languages, toggles), it goes in the profile, not the instrument config.

4. **Exclude patterns extend the profile.** Instrument-level excludes are additive
   to `profile.exclude`.

---

## Wiring into the Orchestrator

To register a new instrument with the qualitoscope orchestrator:

### 1. Add to `qualitoscope/config.yaml`

```yaml
instruments:
  # ... existing instruments ...
  - id: I14                    # Next sequential ID
    name: example-tomographe
    sections: [S15]            # DR section(s) this instrument covers
```

### 2. Update `qualitoscope/README.md`

- Phase 1: add the instrument to the inventory table
- Phase 2: add delegation instructions
- Phase 5: add aggregation weight

### 3. Update overlap resolution

If the new instrument shares concerns with existing instruments, add ownership rules
to `qualitoscope/methods/03-overlap-resolution.md`.

### 4. Add cross-correlation rules (if applicable)

If the new instrument's findings should be correlated with other instruments, add
rules to `qualitoscope/methods/04-cross-correlation.md` and `qualitoscope/config.yaml`
(cross-correlation section).

---

## Fix Guide Authoring

Every instrument must have a populated `fixes/` directory. Follow the
[fixes content standard](../instruments/fixes-content-standard.md).

Minimum requirements:
- `fixes/README.md` — index table of all fix guides
- At least 2 fix guides covering the most common finding categories

Each fix guide must include:
- Frontmatter with title, status, last-updated, instrument, severity-range
- "What this means" section (one paragraph)
- "How to fix" with per-language subsections and code examples
- "Prevention" with CI-enforceable checks

---

## Testing Your Instrument

Before submitting a new instrument:

### 1. Dry run against a sample project

Pick an open-source project matching the instrument's domain and run a full scan:

```
Read instruments/example-tomographe/README.md and execute a full scan against
/path/to/sample-project.
```

Verify:
- All phases execute without errors
- Findings are correctly severity-rated
- Output matches the template format
- Fix guide links resolve

### 2. Edge cases to test

- **Empty project** — minimal profile, no source code. Instrument should report
  Observations, not crash.
- **Large project** — 100+ files. Verify the instrument doesn't timeout or produce
  excessive output.
- **Multi-language project** — languages the instrument doesn't specifically support.
  Verify graceful fallback to General guidance.
- **All toggles false** — conditional phases should be skipped cleanly with an
  Observation noting why.

### 3. Orchestrator integration

Run a full qualitoscope scan with the new instrument registered. Verify:
- Phase 1 detects the instrument
- Phase 2 delegates to it
- Phase 3 handles any overlaps correctly
- Phase 5 includes it in aggregation

---

## Checklist — New Instrument Readiness

- [ ] `README.md` with scope, phases, quick start, and severity rules
- [ ] `config.yaml` with documented thresholds and sensible defaults
- [ ] At least 2 method files covering core scanning phases
- [ ] At least 1 checklist file
- [ ] Output template in `templates/`
- [ ] `fixes/README.md` index with at least 2 fix guides
- [ ] Registered in `qualitoscope/config.yaml`
- [ ] Overlap resolution rules defined (if applicable)
- [ ] Dry-run tested against a sample project
- [ ] Full qualitoscope scan passes with instrument included
