# Phase 8 — Report

Compile all phase outputs into a unified Qualitoscope report.

## Inputs
- All phase JSON outputs (Phases 1-7)
- Report template from `templates/report-template.md`

## Report Variants

| Mode | Output File | Contents |
|------|------------|----------|
| Quick Scan | `output/QS{n}-{date}.md` | Phases 1-5, 7-8 |
| DR Mode | `output/QS{n}-{date}.md` + `output/DR{n}-{target}.md` | All 8 phases |
| Targeted | `output/QS{n}-{date}-targeted.md` | Subset of instruments |

## Steps
1. Merge all phase JSON outputs into unified data structure
2. Fill report template with computed values
3. Generate per-section breakdown table
4. Write action register with severity, priority, and GitLab issue references
5. Append run metadata
6. Write final report to output directory

## Output
- `output/QS{n}-{date}.md` (Qualitoscope report)
- Optionally: `output/DR{n}-{target}.md` (Design Review, DR Mode only)
