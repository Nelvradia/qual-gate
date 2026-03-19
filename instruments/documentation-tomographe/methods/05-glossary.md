# Phase 5 — Glossary Compliance (K2)

**Goal:** Verify the codebase uses canonical terminology consistently. Bare ambiguous terms
(words that have multiple meanings and should always be qualified with a prefix or context)
are flagged for resolution.

## Methodology

### Step 1: Load glossary terms

Terms come from one of two sources:

1. **Project-specific terms file** — pointed to by `profile.conventions.glossary_script` or
   passed via `--terms-file` to the accelerator. Format: YAML with term name, regex pattern,
   and qualified forms (see `accelerators/glossary-terms.example.yaml`).
2. **Built-in defaults** — the accelerator ships with common overloaded terms (`domain`,
   `context`, `trigger`, `session`, `template`, `thread`) for backward compatibility.

### Step 2: Scan source files

The accelerator (`accelerators/glossary-linter.sh`) uses ripgrep to scan source files for
bare term usage. It applies three layers of filtering:

1. **Qualified forms** — terms used with a qualifying prefix (e.g., `conversation_context`,
   `domain_label`) are suppressed.
2. **Framework patterns** — language constructs that coincidentally match term names (e.g.,
   `std::thread`, `tokio::task`, `anyhow::Context`) are suppressed.
3. **Allowlist** — project-specific patterns that are known false positives, loaded from
   `accelerators/glossary-allowlist.txt` or a custom path via `--allowlist`.

### Step 3: Report violations

Each bare term usage is reported with file path and line number. Violations are grouped by
term for readability.

## Running the accelerator

```bash
# Basic scan with example terms
bash instruments/documentation-tomographe/accelerators/glossary-linter.sh \
  --terms-file instruments/documentation-tomographe/accelerators/glossary-terms.example.yaml \
  src/

# Strict mode (exit 1 on violations — use in CI)
bash instruments/documentation-tomographe/accelerators/glossary-linter.sh \
  --strict \
  --terms-file path/to/terms.yaml \
  --allowlist path/to/allowlist.txt \
  --type rust,python \
  src/ lib/
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `--strict` | Exit 1 on any violation | Advisory mode (exit 0) |
| `--terms-file F` | Load terms from YAML file | Built-in terms |
| `--allowlist F` | Path to allowlist file | `accelerators/glossary-allowlist.txt` |
| `--type LANGS` | Comma-separated ripgrep language types | All files |
| `--glossary-doc F` | Doc reference for remediation output | None |

## Severity Rules

| Finding | Severity |
|---------|----------|
| Bare ambiguous term in API surface (public function, struct, endpoint) | **Minor** |
| Bare ambiguous term in internal code | **Observation** |
| No glossary terms file configured | **Observation** |

## LLM Steps (when accelerator unavailable)

If the accelerator cannot be run (ripgrep not installed, etc.), the LLM performs a manual
review:

1. Read the project's glossary documentation (if it exists).
2. Identify overloaded terms from the domain.
3. Search source files for bare usage of each term.
4. Filter out qualified forms and framework constructs.
5. Report remaining violations with suggested qualified alternatives.
