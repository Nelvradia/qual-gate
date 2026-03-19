# Instrument Readiness Checklist

Master checklist verifying all 13 instruments are present, configured, and runnable. Used by Phase 1 (Instrument Inventory).

## Instruments (all under `instruments/`)

- [ ] `instruments/architecture-tomographe/` — directory exists, README.md present, config valid
- [ ] `instruments/test-tomographe/` — directory exists, README.md present, config valid
- [ ] `instruments/ai-ml-tomographe/` — directory exists, README.md present, config.yaml valid
- [ ] `instruments/code-tomographe/` — directory exists, README.md present, config.yaml valid
- [ ] `instruments/compliance-tomographe/` — directory exists, README.md present, config.yaml valid
- [ ] `instruments/data-tomographe/` — directory exists, README.md present, config.yaml valid
- [ ] `instruments/deployment-tomographe/` — directory exists, README.md present, config.yaml valid
- [ ] `instruments/documentation-tomographe/` — directory exists, README.md present, config.yaml valid
- [ ] `instruments/observability-tomographe/` — directory exists, README.md present, config.yaml valid
- [ ] `instruments/performance-tomographe/` — directory exists, README.md present, config.yaml valid
- [ ] `instruments/security-tomographe/` — directory exists, README.md present, config.yaml valid
- [ ] `instruments/ux-tomographe/` — directory exists, README.md present, config.yaml valid
- [ ] `instruments/dependency-tomographe/` — directory exists, README.md present, config.yaml valid

## Structure Validation (per instrument)

- [ ] `README.md` exists and is non-empty
- [ ] `config.yaml` exists and parses as valid YAML
- [ ] `output/` directory exists with `.gitignore`
- [ ] `templates/report-template.md` exists
- [ ] `checklists/` directory exists with at least one checklist

## DR Section Coverage

- [ ] S1 covered by at least one instrument
- [ ] S2 covered by at least one instrument
- [ ] S3 covered by at least one instrument
- [ ] S4 covered by at least one instrument
- [ ] S5 covered by at least one instrument
- [ ] S6 covered by at least one instrument
- [ ] S7 covered by at least one instrument
- [ ] S8 covered by at least one instrument
- [ ] S9 covered by at least one instrument
- [ ] S10 covered by at least one instrument
- [ ] S11 covered by at least one instrument
- [ ] S12 covered by at least one instrument
- [ ] S13 covered by at least one instrument
- [ ] K1 covered by at least one instrument
- [ ] K2 covered by at least one instrument
- [ ] K3 covered by at least one instrument
- [ ] K4 covered by at least one instrument
- [ ] AI/ML Quality covered by at least one instrument
