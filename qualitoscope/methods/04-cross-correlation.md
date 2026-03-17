# Phase 4 — Cross-Correlation

Detect findings that span multiple instruments — issues that no single instrument can catch because they require information from two or more domains.

## Inputs
- Deduplicated findings from Phase 3
- Cross-correlation rules from `config.yaml`

## Correlation Rules

| ID | Name | Instruments | Severity |
|----|------|------------|----------|
| XC-01 | High-churn file is enforcer module | test × security | Major |
| XC-02 | Skill without enforcer entry | code × compliance | Critical |
| XC-03 | Migration without schema documentation update | data × documentation | Minor |
| XC-04 | Metric without dashboard panel | observability × documentation | Observation |
| XC-05 | AI configuration change without eval | AI/ML × documentation | Minor |
| XC-06 | CI job not merge-blocking | deployment × test | Minor |
| XC-07 | Component without a11y test | UX × test | Minor |
| XC-08 | Dep update without security scan | code × security | Major |

## Steps
For each rule:
1. Extract relevant data from each instrument's findings
2. Compute the intersection or diff as specified by the rule
3. For each match: create a cross-correlation finding with evidence from both instruments
4. Assign severity per the rule's default

## Output
- `output/phase4-cross-correlation.json`

## Severity Rules
| Finding | Severity |
|---------|----------|
| Skill bypasses enforcer (XC-02) | Critical |
| High-churn enforcer file + low coverage (XC-01) | Major |
| Supply chain vulnerability window (XC-08) | Major |
| Schema map drift (XC-03) | Minor |
| Prompt regression risk (XC-05) | Minor |
| CI job not gating (XC-06) | Minor |
| Component without a11y (XC-07) | Minor |
| Metric without dashboard (XC-04) | Observation |
