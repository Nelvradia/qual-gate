---
title: "Remediation Library Content Standard"
status: current
last-updated: 2026-03-19
---

# Remediation Library Content Standard

This document defines the canonical structure for all fix guides in qual-gate's `fixes/`
directories. Every instrument must follow this standard to ensure consistency and
actionability across the remediation library.

---

## Fix Guide Structure

Each fix guide is a standalone Markdown file in `instruments/<instrument>/fixes/` named
after the finding category it addresses, using kebab-case (e.g., `hardcoded-secrets.md`).

### Required Sections

```markdown
---
title: "Fix: {Finding Category}"
status: current
last-updated: YYYY-MM-DD
instrument: {instrument-name}
severity-range: "{min}–{max}"
---

# Fix: {Finding Category}

## What this means

One paragraph explaining what this finding is, why it matters, and the risk it
represents if left unaddressed. Write for a developer who has just seen this
finding in their scan report.

## How to fix

### Python
{Language-specific remediation steps with code examples.}

### Rust
{Language-specific remediation steps with code examples.}

### TypeScript
{Language-specific remediation steps with code examples.}

### Go
{Language-specific remediation steps with code examples.}

### General
{Language-agnostic guidance for stacks not covered above.}

## Prevention

How to prevent this finding from recurring. Focus on:
- CI-enforceable checks (linters, pre-commit hooks, pipeline gates)
- Configuration changes (editor settings, project defaults)
- Process changes (review checklists, templates)
```

### Rules

1. **Language subsection order:** Python → Rust → TypeScript → Go → General. General is
   always last and always present. Omit a language subsection only if the finding is
   genuinely inapplicable to that language.

2. **Code examples are mandatory.** Every "How to fix" subsection must include at least one
   concrete code example showing the before/after transformation, or a command sequence
   that resolves the finding.

3. **Frontmatter is mandatory.** The `severity-range` field uses the project's unified
   severity scale: Critical, Major, Minor, Observation.

4. **Keep guides self-contained.** A developer should be able to resolve the finding using
   only the fix guide, without reading the instrument's scanning methodology. Cross-reference
   other fix guides by relative path if related.

5. **Prevention section must be actionable.** "Be careful" is not prevention. Cite specific
   tools, config flags, or CI job snippets.

---

## Per-Instrument fixes/README.md Format

Each instrument's `fixes/README.md` serves as an index of all fix guides in that directory.

```markdown
---
title: "{Instrument} — Fix Guide Index"
status: current
last-updated: YYYY-MM-DD
---

# {Instrument} — Fix Guide Index

| Finding Category | File | Severity Range |
|---|---|---|
| {Category name} | [{filename}](./{filename}) | {severity-range} |
| ... | ... | ... |
```

### Rules

1. Table rows are sorted by severity (Critical first, then Major, Minor, Observation).
2. Every `.md` file in `fixes/` (except `README.md`) must appear in the index.
3. The "Finding Category" column uses the human-readable title from the fix guide's
   frontmatter, not the filename.

---

## Reference Implementation

See `instruments/dependency-tomographe/fixes/README.md` for the first populated fix
directory. While it predates this standard and uses a different format, it demonstrates
the principle of actionable, language-specific remediation guidance.

---

## Severity Scale Reference

| Severity | Meaning |
|---|---|
| **Critical** | Blocks release. Must fix before proceeding. |
| **Major** | Significant risk. Should fix in current phase. |
| **Minor** | Low risk. Track and fix when convenient. |
| **Observation** | Informational. No action required. |
