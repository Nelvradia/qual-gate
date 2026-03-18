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

Qual-gate instruments are designed to be run by an AI coding assistant (Claude Code, etc.) against a target codebase. Each instrument's `README.md` contains the full scanning methodology — the assistant reads it and executes the prescribed checks against your project.

```bash
# Example: run the code quality instrument
"Read instruments/code-tomographe/README.md and execute a full code quality scan."

# Example: run all instruments via the orchestrator
"Read qualitoscope/README.md and execute a full Qualitoscope scan."
```

Reports are written to `output/YYYY-MM-DD_{project_name}/` with instrument-prefixed filenames (e.g., `CQ1-code.md`, `SS1-security.md`). Set `project_name` in `qualitoscope/config.yaml` before running.

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

1. **Target paths** — Each instrument scans the project it's pointed at. Paths in `config.yaml` and method files use relative references to the target project.
2. **Checklists** — Found in each instrument's `checklists/` directory. Add, remove, or modify checklist items to match your project's architecture and standards.
3. **Severity thresholds** — Configurable in `config.yaml` per instrument and in `qualitoscope/config.yaml` for the orchestrator.

## Severity Scale

All instruments use a unified severity scale:

| Severity | Meaning |
|----------|---------|
| **Critical** | Blocks release. Must fix before proceeding. |
| **Major** | Significant risk. Should fix in current phase. |
| **Minor** | Low risk. Track and fix when convenient. |
| **Observation** | Informational. No action required. |
| **OK** | Check passed. |

## License

Licensed under the [Apache License, Version 2.0](LICENSE).

Copyright 2026 Nelvradia.
