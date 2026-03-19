# documentation-tomographe/

**Documentation health scanner.** Audits doc coverage, staleness, cross-reference integrity, glossary compliance, design-to-implementation delta, and cross-document coherence. Covers the widest scope of any single instrument (S2 + K2 + K3 + K4).

**Covers Sections:** S2 (Documentation), K2 (Glossary Compliance), K3 (Design-to-Impl Delta), K4 (Cross-Doc Coherence)

---

## Quick Start

```bash
"Read instruments/documentation-tomographe/README.md and execute a full documentation scan."
"Read instruments/documentation-tomographe/README.md and execute Phase 4 (Design-to-Impl Delta) only."
```

---

## Scan Phases

| Phase | Name | What It Does | Tools |
|-------|------|-------------|-------|
| **1** | Inventory | Catalog all docs, READMEs, runbooks, inline comments | `find`, `wc`, frontmatter parsing |
| **2** | Staleness | Detect outdated docs by comparing git timestamps to code changes | `git log`, age analysis |
| **3** | Cross-Reference Integrity | Verify all doc links point to real files, no broken refs | `grep`, link validation |
| **4** | Design-to-Impl Delta (K3) | Compare design specs to actual implementation | Code audit vs design docs |
| **5** | Glossary Compliance (K2) | Verify terminology consistency, no bare/ambiguous terms | Glossary linter, `grep` |
| **6** | Cross-Doc Coherence (K4) | Verify schema docs ↔ migrations, metrics docs ↔ code, config ↔ implementation | Cross-reference checks |
| **7** | Report | Compile findings | Template filling |

---

## Path Resolution

Before running any phase, resolve these paths from the target project's
`project-profile.yaml`. Use defaults when profile fields are absent.

| Variable | Profile Field | Default |
|----------|--------------|---------|
| `SOURCE_DIRS` | `paths.source_dirs` | `src/` |
| `TEST_DIRS` | `paths.test_dirs` | `tests/` |
| `DOCS_DIR` | `paths.docs_dir` | `docs/` |

Replace all `src/` references in accelerator commands below with
`${SOURCE_DIRS}`.

---

## Phase 1 — Inventory

**Goal:** Complete map of all documentation.

```bash
# All markdown files
find docs/ -name '*.md' | wc -l
find docs/ -name '*.md' | sed 's|/[^/]*$||' | sort | uniq -c | sort -rn

# READMEs across the project
find . -name 'README.md' -not -path '*/node_modules/*' -not -path '*/target/*' | sort

# Inline doc coverage
grep -rn '///\|"""\|#\s' ${SOURCE_DIRS} --include='*.rs' --include='*.py' | wc -l
# vs public items:
grep -rn 'pub fn \|pub struct \|pub enum \|pub trait \|def \|class ' ${SOURCE_DIRS} --include='*.rs' --include='*.py' | wc -l

# ADR count
find .claude/decisions/ -name '*.md' 2>/dev/null | wc -l

# Runbook count
find docs/operations/ -name '*.md' 2>/dev/null | wc -l

# Frontmatter check (docs should have structured frontmatter)
for f in $(find docs/ -name '*.md'); do
  head -1 "$f" 2>/dev/null | grep -q '^---' || echo "NO_FRONTMATTER: $f"
done 2>/dev/null
```

### Output

```json
{
  "total_docs": 0,
  "by_directory": {},
  "readmes": [],
  "adrs": 0,
  "runbooks": 0,
  "inline_doc_ratio": 0.0,
  "missing_frontmatter": []
}
```

---

## Phase 2 — Staleness

**Goal:** Identify docs that haven't been updated since the code they describe changed significantly.

```bash
# Last modification date per doc
for f in $(find docs/ -name '*.md'); do
  mod=$(git log -1 --format="%ai" -- "$f" 2>/dev/null | cut -d' ' -f1)
  echo "$mod $f"
done | sort

# Docs not touched in >90 days
CUTOFF=$(date -d '90 days ago' +%s 2>/dev/null || date -v-90d +%s)
for f in $(find docs/ -name '*.md'); do
  mod=$(git log -1 --format="%at" -- "$f" 2>/dev/null)
  if [ -n "$mod" ] && [ "$mod" -lt "$CUTOFF" ]; then
    echo "STALE: $f (last modified $(git log -1 --format='%ar' -- "$f"))"
  fi
done

# Frontmatter last-updated field vs git timestamp
for f in $(find docs/ -name '*.md'); do
  declared=$(grep 'last-updated:' "$f" 2>/dev/null | head -1 | awk '{print $2}')
  actual=$(git log -1 --format="%ai" -- "$f" 2>/dev/null | cut -d' ' -f1)
  if [ -n "$declared" ] && [ "$declared" != "$actual" ]; then
    echo "MISMATCH: $f — frontmatter says $declared, git says $actual"
  fi
done 2>/dev/null

# Docs referencing files that have changed since doc was last updated
# (indicates the doc may be describing stale behavior)
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Architecture doc not updated in >180 days + code changed | **Major** |
| Operational runbook not updated in >90 days | **Minor** |
| Frontmatter date mismatch | **Observation** |
| Design doc for shipped feature never updated post-impl | **Minor** |
| Superseded doc not marked as such | **Minor** |

---

## Phase 3 — Cross-Reference Integrity

**Goal:** Verify that links between docs actually point to real files.

```bash
# Extract all markdown links from docs
grep -rn '\[.*\](.*\.md' docs/ --include='*.md' | \
  sed 's/.*(\(.*\.md[^)]*\)).*/\1/' | sort -u | while read link; do
  # Resolve relative path
  # Check if file exists
  if [ ! -f "docs/$link" ] && [ ! -f "$link" ]; then
    echo "BROKEN: $link"
  fi
done

# Check cross-references in frontmatter
grep -rn 'related:\|not-here:\|parent:' docs/ --include='*.md' | \
  grep '\.md' | sed 's/.*→ \(.*\.md\).*/\1/' | sort -u | while read ref; do
  find docs/ -name "$(basename "$ref")" | grep -q . || echo "BROKEN_REF: $ref"
done 2>/dev/null

# Orphan docs (not referenced from any other doc)
for f in $(find docs/ -name '*.md' -not -name '00-index.md'); do
  base=$(basename "$f")
  refs=$(grep -rl "$base" docs/ --include='*.md' | wc -l)
  if [ "$refs" -eq 0 ]; then
    echo "ORPHAN: $f (not referenced from any other doc)"
  fi
done 2>/dev/null | head -20
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Broken link in architecture or operations doc | **Minor** |
| Orphan doc (not referenced anywhere) | **Observation** |
| Broken frontmatter cross-reference | **Observation** |

---

## Phase 4 — Design-to-Impl Delta (K3)

> **Prerequisite:** This phase requires `profile.conventions.design_docs`.
> When absent, emit `Observation: "documentation-tomographe Phase 4 skipped —
> no design docs path configured"` and proceed to Phase 5.

**Goal:** For each implemented feature, compare design spec to actual code.

```bash
# List all design docs and their implementation status
for f in docs/design/[0-9]*.md; do
  feature=$(basename "$f" .md | sed 's/^[0-9]*-//')
  # Check if corresponding module exists in code
  found=$(find src/ -name "*${feature}*" 2>/dev/null | head -1)
  if [ -n "$found" ]; then
    echo "IMPLEMENTED: $f → $found"
  else
    echo "NOT_IMPLEMENTED: $f"
  fi
done 2>/dev/null

# For implemented features, extract MVP section
for f in docs/design/[0-9]*.md; do
  grep -q 'MVP\|Ship First\|Milestone 1' "$f" 2>/dev/null && echo "HAS_MVP_SPEC: $f" || echo "NO_MVP_SPEC: $f"
done 2>/dev/null

# Check if implementation matches spec (LLM-assisted)
# For each implemented feature:
#   1. Read MVP section from design doc
#   2. Read actual code
#   3. Compare: are all MVP deliverables present?
#   4. Flag missing deliverables
```

### Checklist per Implemented Feature

- [ ] MVP / design spec section exists in design doc
- [ ] All MVP deliverables have corresponding code
- [ ] DB tables match schema documentation
- [ ] Service actions match design doc tier specifications
- [ ] Test manifest exists and matches test mandates

---

## Phase 5 — Glossary Compliance (K2)

> **Prerequisite:** This phase requires glossary terms file or source
> directories. When absent, emit `Observation: "documentation-tomographe
> Phase 5 skipped — no glossary terms or source directories found"` and
> proceed to Phase 6.

**Goal:** Verify the codebase uses canonical terminology consistently.

```bash
# Run the bundled glossary linter accelerator
bash instruments/documentation-tomographe/accelerators/glossary-linter.sh \
  --terms-file instruments/documentation-tomographe/accelerators/glossary-terms.example.yaml \
  --allowlist instruments/documentation-tomographe/accelerators/glossary-allowlist.txt \
  ${SOURCE_DIRS}

# Or with custom terms and strict mode (fails on violations)
bash instruments/documentation-tomographe/accelerators/glossary-linter.sh \
  --strict \
  --terms-file path/to/your-terms.yaml \
  ${SOURCE_DIRS}

# Manual check for ambiguous bare-term violations
# Adapt these terms to the project's glossary
for term in '"domain"' '"context"' '"template"' '"trigger"' '"session"'; do
  count=$(grep -rn "\\b${term}\\b" src/ --include='*.rs' --include='*.py' 2>/dev/null | \
    grep -v '_domain\|_context\|_template\|_trigger\|_session\|//\|///\|#\[' | wc -l)
  echo "Bare $term: $count violations"
done
```

---

## Phase 6 — Cross-Doc Coherence (K4)

> **Prerequisite:** This phase requires schema_map, metrics_doc, or
> access_control_config. When all are absent, emit `Observation:
> "documentation-tomographe Phase 6 skipped — no cross-reference targets
> configured"` and proceed to Phase 7.

**Goal:** Verify that documentation artifacts stay synchronized with code artifacts.

```bash
# K4-1: Schema documentation vs actual migration tables
# Extract table names from schema docs
grep -E 'CREATE TABLE|table name' docs/schema-map.md 2>/dev/null | head -30
# Extract tables from migration code
grep -rn 'CREATE TABLE' ${SOURCE_DIRS} --include='*.rs' --include='*.py' --include='*.sql' | \
  sed 's/.*CREATE TABLE \([a-z_]*\).*/\1/' | sort -u
# Diff the two lists

# K4-2: Metrics registry docs vs actual metrics code
grep -oP '[a-z]+_[a-z_]+' docs/metrics-registry.md 2>/dev/null | sort -u | wc -l
grep -c 'register\|counter!\|histogram!\|gauge!' ${SOURCE_DIRS}/metrics.rs 2>/dev/null
# Compare: documented count vs registered count

# K4-3: Permission/access control config domains vs code implementation
# Extract domains from config
ACCESS_CONTROL_CONFIG="${ACCESS_CONTROL_CONFIG:-config/access-control.yaml}"
yq '.domains[].name' "$ACCESS_CONTROL_CONFIG" 2>/dev/null | sort
# Extract domains from code
grep -rn 'domain.*=.*"' ${SOURCE_DIRS} --include='*.rs' --include='*.py' | \
  sed 's/.*"\([^"]*\)".*/\1/' | sort -u
# Diff the two lists

# K4-4: COMPATIBILITY.yaml vs VERSION files (if multi-component)
cat COMPATIBILITY.yaml 2>/dev/null
find . -name 'VERSION' -not -path '*/node_modules/*' -not -path '*/target/*' | while read v; do
  echo "$v: $(cat "$v" 2>/dev/null)"
done

# K4-5: 00-index.md references all doc files
total_docs=$(find docs/ -name '*.md' | wc -l)
indexed_docs=$(grep -c '\.md' docs/00-index.md 2>/dev/null)
echo "Total docs: $total_docs, Indexed in 00-index.md: $indexed_docs"
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Schema documentation missing tables that exist in migrations | **Major** |
| Access control config domain doesn't match code | **Major** |
| Metrics registry count significantly diverges from code | **Minor** |
| VERSION files don't match COMPATIBILITY.yaml | **Minor** |
| Docs not indexed in 00-index.md | **Observation** |

---

## Output

Reports are written to `output/YYYY-MM-DD_{project_name}/DOC{n}-documentation-tomographe.md` (see `qualitoscope/config.yaml` for `project_name`).

---

## Configuration

This instrument reads project-specific paths from `project-profile.yaml` in the target project root. If a profile field is absent, the default from the profile schema applies. Instrument-specific thresholds remain in this instrument's `config.yaml`.

```yaml
thresholds:
  max_stale_docs_90d: 10
  max_broken_links: 0
  max_orphan_docs: 5
  glossary_violations: 0
  schema_map_alignment: 100
  metrics_registry_alignment: 90
  frontmatter_coverage: 95

scope:
  docs_dir: docs/
  design_docs: docs/design/
  operations: docs/operations/
  adrs: .claude/decisions/
  glossary_script: instruments/documentation-tomographe/accelerators/glossary-linter.sh
  schema_map: docs/schema-map.md
  metrics_doc: docs/metrics-registry.md
  access_control_config: config/access-control.yaml  # adjust to project layout
```

---

## Run History

| Run | Date | Trigger | Report |
|-----|------|---------|--------|
| DOC1 | _pending_ | Initial baseline | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
