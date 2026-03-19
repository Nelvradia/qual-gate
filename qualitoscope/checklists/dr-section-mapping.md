# DR Section → Instrument Mapping

Maps each Design Review section to its authoritative instrument. Used by Phase 6 (DR Synthesis) to populate the DR-TEMPLATE.

## Section Mapping

| DR Section | Primary Instrument | Secondary Instrument | Notes |
|---|---|---|---|
| S1 Architecture | `architecture-tomographe` (I01) | — | Pattern fitness, violations, drift |
| S2 Documentation | `documentation-tomographe` (I04) | — | Doc inventory, staleness, cross-refs |
| S3 Code Quality | `code-tomographe` (I03) | — | fmt, clippy, complexity, duplication |
| S4 Validation | `test-tomographe` (I02) | — | Test coverage, health, alignment |
| S5 Security | `security-tomographe` (I09) | `ai-ml-tomographe` (I12), `dependency-tomographe` (I13) | AI threats from I12, supply chain from I13 |
| S6 Configuration | `compliance-tomographe` (I05) | — | Config validation, env management |
| S7 Observability | `observability-tomographe` (I08) | — | Metrics, alerting, logging, dashboards |
| S8 Data Management | `data-tomographe` (I06) | — | Schema, migrations, privacy, backup |
| S9 Deployment | `deployment-tomographe` (I07) | — | CI, reproducibility, rollback, release |
| S10 Performance | `performance-tomographe` (I10) | — | Profiling, benchmarks, resource usage |
| S11 UX | `ux-tomographe` (I11) | — | Components, a11y, personality, flows |
| S12 Licensing | `compliance-tomographe` (I05) | `dependency-tomographe` (I13) | Dep licence matrix from I13, policy from I05 |
| S13 Maintainability | `code-tomographe` (I03) | — | Tech debt, complexity scoring |
| S14 AI/ML Quality | `ai-ml-tomographe` (I12) | — | Prompt quality, eval coverage, RAG accuracy. Conditional: `toggles.ai_ml_components` |
| Overall Summary | Qualitoscope Phase 5 | — | Aggregated from all instruments (not a numbered DR section) |
| K1 Permission System | `compliance-tomographe` (I05) | `security-tomographe` (I09) | Completeness from I05, correctness from I09. Conditional: requires `toggles.permission_system` |
| K2 Glossary | `documentation-tomographe` (I04) | — | lint_glossary.py results |
| K3 Design-to-Impl | `documentation-tomographe` (I04) | — | Phase 4 delta analysis |
| K4 Cross-Doc | `documentation-tomographe` (I04) | — | Schema/metrics documentation coherence |

## Multi-Section Instruments

Some instruments contribute to multiple DR sections:

| Instrument | Sections Covered |
|-----------|-----------------|
| `code-tomographe` | S3, S13 |
| `compliance-tomographe` | S6, S12, K1 |
| `documentation-tomographe` | S2, K2, K3, K4 |
| `dependency-tomographe` | S12, S5 |

## Section with No Direct Instrument

| Section | Source |
|---------|--------|
| S14 Overall Summary | Computed by Qualitoscope Phase 5 (not a delegated instrument) |

## Conditional Sections

Some DR sections or sub-checks are conditional on profile toggles:

| Section / Check | Required Toggle | When Disabled |
|---|---|---|
| K1 Permission System | `toggles.permission_system` | Section skipped, logged as Observation |
| S5 AI threat subset | `toggles.ai_ml_components` | AI threat model phase skipped |
| S14 AI/ML Quality | `toggles.ai_ml_components` | S14 omitted from DR reports |
| S6 GDPR subset | `toggles.gdpr_scope` | GDPR readiness phase skipped |
| S6 AI Act subset | `toggles.ai_act_scope` | AI Act readiness phase skipped |
