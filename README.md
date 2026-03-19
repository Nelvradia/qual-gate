# qual-gate

An open-source suite of quality diagnostic instruments for auditing software projects. Each instrument ("tomographe") scans a specific quality dimension — architecture, security, testing, performance, and more — producing structured, severity-rated reports with actionable findings.

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

## Structure

```
qual-gate/
├── instruments/                  # All 13 domain scanning tomographes
│   ├── ai-ml-tomographe/         #   AI/ML readiness scanning
│   ├── architecture-tomographe/  #   Architectural health scanning
│   ├── code-tomographe/          #   Code quality scanning
│   ├── compliance-tomographe/    #   Regulatory/standard compliance
│   ├── data-tomographe/          #   Data quality and integrity
│   ├── dependency-tomographe/    #   Dependency inventory and licence risk
│   ├── deployment-tomographe/    #   Deployment readiness
│   ├── documentation-tomographe/ #   Documentation quality
│   ├── observability-tomographe/ #   Observability coverage
│   ├── performance-tomographe/   #   Performance profiling
│   ├── security-tomographe/      #   Security scanning
│   ├── test-tomographe/          #   Test health scanning
│   └── ux-tomographe/            #   UX quality scanning
├── qualitoscope/                 # Orchestrator — delegates to all instruments
├── output/                       # Generated scan reports (untracked)
│   └── YYYY-MM-DD_{project_name}/ #  One folder per run
├── LICENSE
├── README.md
└── VERSION
```

## How It Works

Qual-gate instruments are designed to be run by an AI coding assistant (Claude Code, Cursor, etc.) against a target codebase. Each instrument's `README.md` contains the full scanning methodology — the assistant reads it and executes the prescribed checks against your project.

Reports are written to `output/YYYY-MM-DD_{project_name}/` with instrument-prefixed filenames (e.g., `CQ1-code.md`, `SS1-security.md`).

## How to Run

### 1. Create a project profile

Place a `project-profile.yaml` in the root of your target project. Minimum required:

```yaml
name: my-project
stack:
  languages: [python]
```

Or let auto-discovery generate one — see step 2.

### 2. Run a scan

Tell your AI assistant:

```bash
# Auto-discover project profile (if none exists) + full scan
"Read qual-gate/qualitoscope/README.md and execute a full Qualitoscope scan
against /path/to/my-project."

# Single instrument scan
"Read qual-gate/instruments/code-tomographe/README.md and execute a code quality
scan against /path/to/my-project."

# Targeted scan (specific instruments)
"Read qual-gate/qualitoscope/README.md and execute a targeted scan for
security + compliance against /path/to/my-project."
```

### 3. Review findings

Each finding includes a severity rating, evidence, and a link to a fix guide with
per-language remediation steps. See [Getting Started](docs/getting-started.md) for
a full walkthrough.

## Instruments

Each instrument follows a standard structure:
`README.md`, `config.yaml`, `methods/`, `checklists/`, `templates/`, `fixes/`.

| Instrument | Scope |
|-----------|-------|
| `ai-ml-tomographe` | AI/ML readiness — model lifecycle, evaluation, prompt health |
| `architecture-tomographe` | Architectural health — pattern fitness, violations, drift |
| `code-tomographe` | Code quality — complexity, duplication, style, dead code |
| `compliance-tomographe` | Regulatory compliance — GDPR, AI Act, licensing |
| `data-tomographe` | Data quality — integrity, schema, migrations, backups |
| `dependency-tomographe` | Dependency inventory — SBOM, unused deps, licence risk, health |
| `deployment-tomographe` | Deployment readiness — Docker, CI/CD, rollback |
| `documentation-tomographe` | Documentation quality — coverage, accuracy, freshness |
| `observability-tomographe` | Observability — metrics, logging, tracing, alerting |
| `performance-tomographe` | Performance — latency, throughput, resource usage |
| `qualitoscope` | Orchestrator — delegates to all instruments, aggregates results |
| `security-tomographe` | Security — dependencies, secrets, auth, injection |
| `test-tomographe` | Test health — coverage, alignment, CI gates |
| `ux-tomographe` | UX quality — heuristics, accessibility, consistency |

## Customisation

Instruments are designed to be project-agnostic. To adapt them to your codebase:

1. **Project profile** — `project-profile.yaml` declares your stack, paths, and feature toggles. All instruments read from this single file. See the [profile reference](docs/project-profile-reference.md).
2. **Checklists** — Found in each instrument's `checklists/` directory. Add, remove, or modify checklist items to match your project's architecture and standards.
3. **Severity thresholds** — Configurable in `config.yaml` per instrument and in `qualitoscope/config.yaml` for the orchestrator.
4. **Conditional toggles** — Enable `permission_system`, `ai_ml_components`, `gdpr_scope`, or `ai_act_scope` in your profile to activate domain-specific checks.

## Severity Scale

All instruments use a unified severity scale:

| Severity | Meaning |
|----------|---------|
| **Critical** | Blocks release. Must fix before proceeding. |
| **Major** | Significant risk. Should fix in current phase. |
| **Minor** | Low risk. Track and fix when convenient. |
| **Observation** | Informational. No action required. |
| **OK** | Check passed. |

## Documentation

- **[Getting Started](docs/getting-started.md)** — first scan walkthrough with worked example
- **[Project Profile Reference](docs/project-profile-reference.md)** — field-by-field `project-profile.yaml` documentation
- **[Instrument Authoring Guide](docs/instrument-authoring-guide.md)** — create custom instruments
- **[Changelog](CHANGELOG.md)** — version history

## License

Licensed under the [Apache License, Version 2.0](LICENSE).

Copyright 2026 Nelvradia.
