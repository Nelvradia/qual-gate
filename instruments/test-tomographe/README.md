# test-tomographe

**Test health scanner for the target project.** Audits test coverage, quality, alignment with test mandates, CI health, regression risk, and AI/ML test readiness. Produces TR{n} reports that track test suite evolution over time.

**Covers DR Sections:** S4 (Testing & Verification)

---

## Quick Start

```bash
"Read instruments/test-tomographe/README.md and execute a full test health scan."
"Read instruments/test-tomographe/README.md and execute Phase 4 (Alignment) only."
```

---

## Scan Phases

| Phase | Name | What It Does | Tools |
|-------|------|-------------|-------|
| **1** | Inventory | Enumerate all tests by language, module, and type | LLM file reading, ecosystem-specific collect commands |
| **2** | Coverage | Line coverage heuristics, module-level gap detection | LLM structural analysis, ecosystem coverage tools |
| **3** | Quality | Assertion density, happy-path ratio, error-case ratio | LLM analysis, assertion keyword search |
| **4** | Alignment | Test mandate compliance, golden path validation | LLM checklist-driven analysis |
| **5** | Health | CI pass rate, flaky test detection, suite timing | LLM CI config reading, skip-pattern search |
| **6** | Regression Risk | High-churn files with low test density | git log, LLM correlation analysis |
| **7** | AI Quality | Golden dataset coverage, LLM stub completeness, error stubs | LLM fixture analysis |
| **8** | Report | Compile TR{n} report with scoring | Template filling |

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

> **Prerequisite:** This phase requires test directories or colocated test
> files. When absent, emit `Observation: "test-tomographe Phase 1 skipped —
> no test files found"` and proceed to Phase 2.

**Goal:** Build a complete inventory of all tests by language, module, and type.

### LLM steps

1. Discover test files by reading the project structure. Test files are identified by convention across ecosystems:
   - Files named `test_*.py`, `*_test.py` (Python)
   - Files named `*_test.go`, `*_test` packages (Go)
   - Files named `*.test.ts`, `*.spec.ts`, `*.test.js` (Node/TypeScript)
   - Files named `*Test.java`, `*Test.kt`, `*Spec.kt` (Java/Kotlin)
   - Files with `#[cfg(test)] mod tests` blocks (Rust)
   - Files under `tests/`, `spec/`, `__tests__/`, `test/` directories
   - Files with `describe(`, `it(`, `test(` calls (JavaScript frameworks)
2. Categorise tests by layer: unit (isolated, no I/O), integration (multiple components, real interfaces), e2e (full system)
3. Count tests per layer and per source module being tested

### Accelerator tools (optional)

```bash
# Rust
cargo test --workspace -- --list 2>/dev/null

# Python
pytest --collect-only -q 2>/dev/null

# Go
go test ./... -list '.*' 2>/dev/null

# Node / TypeScript (Jest)
jest --listTests 2>/dev/null

# Node / TypeScript (Vitest)
vitest list 2>/dev/null
```

### Deliverables

- Test inventory table (language, module, count, type)
- Total test count and breakdown by category

---

## Phase 2 — Coverage

**Goal:** Estimate test coverage and identify module-level gaps.

### LLM steps

1. Read the source module list from Phase 1 alongside the test inventory
2. For each public function, method, or class in source: check whether at least one test file imports or references it
3. Note modules with zero test coverage (no test file references any symbol from them)
4. Note modules with only happy-path tests (no error case, boundary, or negative tests visible)
5. This is an approximation — exact line coverage requires tools — but it gives a meaningful structural coverage picture

### Accelerator tools (optional)

```bash
# Rust (requires cargo-llvm-cov)
cargo llvm-cov --workspace 2>/dev/null

# Python
pytest --cov=src --cov-report=term-missing 2>/dev/null

# Go
go test ./... -cover 2>/dev/null

# Node / TypeScript (Jest)
jest --coverage 2>/dev/null

# Node / TypeScript (Vitest)
vitest run --coverage 2>/dev/null
```

Coverage output shows line/branch percentages per module. Cross-reference with the source module list to identify gaps.

### Thresholds

| Metric | Phase 1B Target | Phase 2 Target |
|--------|----------------|----------------|
| Line coverage (heuristic) | 60% | 75% |
| Module-level gap count | <10 | <5 |
| Access Control Coverage | 100% | 100% |

### Severity Rules

| Finding | Severity |
|---------|----------|
| Service module with zero tests | **Critical** |
| Access Control Coverage <100% | **Critical** |
| Module coverage <30% (heuristic) | **Major** |
| Module coverage 30-60% | **Minor** |

---

## Phase 3 — Quality

**Goal:** Assess test quality beyond mere count — are tests meaningful?

### LLM steps

1. Read a sample of test files (at minimum: one per test layer, one per major module)
2. For each test: check that it has a meaningful name describing behaviour and condition, not just the function name
3. Check assertion density: does each test assert something, or does it just execute code?
4. Check for tests that assert nothing (pass unconditionally) — these are false confidence
5. Check for tests that test implementation details rather than behaviour (brittle tests)
6. These quality indicators are language-agnostic

### Accelerator tools (optional)

```bash
# Rust — assertion keywords
grep -rn 'assert!\|assert_eq!\|assert_ne!\|assert_matches!' tests/ src/ 2>/dev/null | grep -v '^\s*//'

# Python — assertion keywords
grep -rn 'assert \|assertEqual\|assertRaises\|pytest.raises' tests/ 2>/dev/null | grep -v '^\s*#'

# Go — assertion keywords
grep -rn 't\.Error\|t\.Fatal\|require\.\|assert\.' . --include='*_test.go' 2>/dev/null

# Node / TypeScript — assertion keywords (Jest/Vitest)
grep -rn 'expect(\|toBe(\|toEqual(\|toThrow(\|should\.' . --include='*.test.*' --include='*.spec.*' 2>/dev/null
```

### Thresholds

| Metric | Target | Warning |
|--------|--------|---------|
| Assertion density | >2.0 per test | <1.5 |
| Happy-path ratio | <70% | >80% |
| Error-case ratio | >20% | <10% |

### Severity Rules

| Finding | Severity |
|---------|----------|
| Assertion density <1.0 | **Major** |
| Happy-path ratio >85% | **Major** |
| Happy-path ratio 70-85% | **Minor** |
| Zero error-case tests in a service module | **Major** |

---

## Phase 4 — Alignment

**Goal:** Verify test suite aligns with test mandates and service test manifests.

### LLM steps

1. Read source modules and test modules together
2. For each source module, verify a corresponding test module exists (naming convention varies: `foo.rs` → `tests/test_foo.rs` or inline `#[cfg(test)]`; `foo.py` → `test_foo.py`; `foo.go` → `foo_test.go`)
3. Flag source modules with no corresponding test module
4. Flag test modules that test a module which no longer exists (orphan tests)
5. Work through the Test Mandate Checklist below, marking each item pass/fail with evidence

### Accelerator tools (optional)

```bash
# List all source files alongside test files to check naming alignment
# Rust
find ${SOURCE_DIRS} -name '*.rs' ! -name 'mod.rs' | sort
find ${TEST_DIRS} -name '*.rs' | sort

# Python
find ${SOURCE_DIRS} -name '*.py' ! -name '__init__.py' | sort
find ${TEST_DIRS} -name 'test_*.py' | sort

# Go
find . -name '*.go' ! -name '*_test.go' | sort
find . -name '*_test.go' | sort
```

### Test Mandate Checklist Items

- [ ] All services have >=3 unit tests per action
- [ ] CRUD functional tests exist for every service with a db module
- [ ] Standard column assertions (id, tenant_id, created_at) in db tests
- [ ] API contract tests for exposed HTTP endpoints
- [ ] Permission tier declaration in parametrized boundary tests
- [ ] Golden path tests exist for cross-service E2E chains
- [ ] Regression tests never deleted (monotonically growing)

### Severity Rules

| Finding | Severity |
|---------|----------|
| Service with zero tests | **Critical** |
| Service missing CRUD functional tests | **Major** |
| Missing standard column assertions | **Minor** |
| Missing API contract tests for exposed endpoint | **Major** |
| Missing access control boundary test for new domain | **Critical** |

---

## Phase 5 — Health

> **Prerequisite:** This phase requires a CI configuration file. When absent,
> emit `Observation: "test-tomographe Phase 5 skipped — no CI configuration
> found"` and proceed to Phase 6.

**Goal:** Assess CI reliability and test suite operational health.

### LLM steps

1. Read CI configuration (`.gitlab-ci.yml`, `.github/workflows/`, `Jenkinsfile`, etc.) and verify tests run in CI
2. Check for tests marked as skipped, ignored, or pending — count them and check whether each has an explanation
3. Check for tests with no timeout on I/O operations — in any language, a test touching the network or filesystem should have a timeout
4. Check that test fixtures and test data files are present and not empty

### Accelerator tools (optional)

```bash
# Rust — ignored tests
grep -rn '#\[ignore\]' tests/ src/ 2>/dev/null

# Python — skipped tests
grep -rn 'pytest.mark.skip\|pytest.mark.xfail\|@skip' tests/ 2>/dev/null

# Go — skipped tests
grep -rn 't\.Skip(' . --include='*_test.go' 2>/dev/null

# Node / TypeScript — skipped tests (Jest/Vitest)
grep -rn 'xit(\|xtest(\|xdescribe(\|test\.skip(\|it\.skip(' . --include='*.test.*' --include='*.spec.*' 2>/dev/null

# CI pass/fail counts (GitLab)
glab api "projects/:id/pipelines?per_page=20&status=success" 2>/dev/null | jq length
glab api "projects/:id/pipelines?per_page=20&status=failed" 2>/dev/null | jq length
```

### Thresholds

| Metric | Target |
|--------|--------|
| CI pass rate (last 20 runs) | >90% |
| Max suite duration | 180s |
| Flaky test count | 0 |
| allow_failure jobs without tracking issue | 0 |

### Severity Rules

| Finding | Severity |
|---------|----------|
| CI pass rate <80% | **Major** |
| Suite duration >300s | **Major** |
| Suite duration 180-300s | **Minor** |
| Flaky test (fails >2x in 20 runs) | **Minor** |
| allow_failure without tracking issue | **Minor** |

---

## Phase 6 — Regression Risk

> **Prerequisite:** This phase requires git history with ≥2 commits. When
> absent, emit `Observation: "test-tomographe Phase 6 skipped — insufficient
> git history"` and proceed to Phase 7.

**Goal:** Identify high-churn files with low test density — the riskiest code.

### LLM steps

1. Obtain the list of high-churn files from git log (see accelerators below)
2. For each high-churn file, check whether a corresponding test file exists and whether that test file contains error-case or boundary tests
3. Cross-reference bug-fix commits (commits whose message matches `fix(`) with the files they touched — flag any bug-fixed file that has no accompanying test addition in the same commit
4. Rank findings by churn × test gap severity

### Accelerator tools (optional)

```bash
# Top 20 most-changed source files (last 90 days)
git log --since="90 days ago" --name-only --pretty=format: | \
  grep -E '\.(rs|py|go|ts|js|java|kt)$' | \
  sort | uniq -c | sort -rn | head -20

# Bug-fix commits and the files they touched
git log --since="90 days ago" --grep='fix(' --name-only --pretty=format: | \
  grep -E '\.(rs|py|go|ts|js|java|kt)$' | sort -u | head -20
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| High-churn file (>10 changes) with zero tests | **Major** |
| Bug-fix commit without regression test | **Minor** |
| High-churn shared file without integration test | **Minor** |

---

## Phase 7 — AI Quality

**Goal:** Verify AI/ML-specific test quality — LLM stub coverage, golden datasets, and error handling.

### LLM steps

1. Read the source to identify all components that call an LLM or external AI service
2. For each such component, check whether a corresponding stub, mock, or fixture file exists under the test directories (naming conventions vary: `llm_stubs/`, `fixtures/`, `mocks/`, inline fake implementations)
3. Inspect stub files: are there error-scenario stubs (timeout, rate limit, malformed response) alongside success stubs? A fixture set with only success responses is incomplete.
4. Check for golden-path or end-to-end tests that exercise AI-driven workflows with realistic inputs and assert on outputs
5. Check for assertions on confidence scores, model outputs, or classification results — tests that only verify "no exception raised" are insufficient for AI components

### Accelerator tools (optional)

```bash
# Find stub / mock / fixture files for AI components (adjust paths to project layout)
find tests/ -type d \( -name '*stub*' -o -name '*mock*' -o -name '*fixture*' \) 2>/dev/null
find tests/ -type f | xargs grep -l 'stub\|mock\|fake' 2>/dev/null | head -20

# Search for error-scenario stubs across all languages
grep -rn 'error\|malformed\|timeout\|rate_limit' tests/ 2>/dev/null | grep -v '^\s*[#//]' | wc -l

# Golden-path / E2E test markers
grep -rn 'golden\|gold_path\|e2e_chain' tests/ src/ 2>/dev/null | wc -l
```

### Thresholds

| Metric | Target |
|--------|--------|
| StubLLM coverage (services with stubs / services using LLM) | 100% |
| Error stub ratio (error stubs / total stubs) | >30% |
| Golden path tests | >=5 |
| Confidence score assertions | >=1 per LLM-using service |

### Severity Rules

| Finding | Severity |
|---------|----------|
| Service uses LLM but has no StubLLM fixture | **Major** |
| Only success stubs exist (no error stubs) | **Major** |
| Zero golden path tests | **Major** |
| Missing confidence score assertions | **Minor** |

---

## Phase 8 — Report

Compile all findings into `output/YYYY-MM-DD_{project_name}/TR{n}-test-tomographe.md` (see `qualitoscope/config.yaml` for `project_name`) using the report template.

### Report Contents

1. **Summary table** — key metrics and scores at a glance
2. **Test inventory** — counts by language, module, type
3. **Coverage assessment** — module-level gaps, access control coverage
4. **Quality scores** — assertion density, happy-path ratio
5. **Test mandate alignment** — per-service manifest compliance
6. **CI health** — pass rate, flaky tests, timing
7. **Regression risk** — high-churn low-test files
8. **AI quality** — stub coverage, golden paths
9. **Composite score** — weighted aggregate
10. **Action register** — prioritized remediation items

### Composite Scoring

| Dimension | Weight | Green | Yellow | Red |
|-----------|--------|-------|--------|-----|
| Coverage | 0.25 | >75% | 60-75% | <60% |
| Quality | 0.20 | >2.0 density, <70% happy | 1.5-2.0 density | <1.5 density |
| Alignment | 0.20 | All mandate checks pass | <3 Critical gaps | >=3 Critical gaps |
| Health | 0.15 | >90% CI pass, <180s | 80-90% pass | <80% pass |
| AI/ML | 0.10 | 100% stub coverage | >80% coverage | <80% coverage |
| Regression | 0.10 | 0 high-risk files | <3 high-risk | >=3 high-risk |

**Composite = weighted sum of dimension scores (0.0 to 1.0)**

---

## Configuration

This instrument reads project-specific paths from `project-profile.yaml` in the target project root. If a profile field is absent, the default from the profile schema applies. Instrument-specific thresholds remain in this instrument's `config.yaml`.

---

## Run History

| Run | Date | Trigger | Verdict | Report |
|-----|------|---------|---------|--------|
| TR1 | _pending_ | Initial baseline | — | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
