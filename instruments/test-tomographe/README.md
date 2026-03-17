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
| **1** | Inventory | Enumerate all tests by language, crate, and module | grep, cargo test --list, pytest --collect-only |
| **2** | Coverage | Line coverage heuristics, module-level gap detection | cargo-tarpaulin (if available), heuristic grep |
| **3** | Quality | Assertion density, happy-path ratio, error-case ratio | grep, LLM analysis |
| **4** | Alignment | Test mandate compliance, golden path validation | Checklist-driven, grep |
| **5** | Health | CI pass rate, flaky test detection, suite timing | CI API, git log, timing data |
| **6** | Regression Risk | High-churn files with low test density | git log, grep correlation |
| **7** | AI Quality | Golden dataset coverage, LLM stub completeness, error stubs | grep, fixture analysis |
| **8** | Report | Compile TR{n} report with scoring | Template filling |

---

## Phase 1 — Inventory

**Goal:** Build a complete inventory of all tests by language, crate, module, and type.

### Steps

```bash
# Rust test count by crate
for crate_name in $(cargo metadata --no-deps --format-version=1 | jq -r '.packages[].name'); do
  count=$(cargo test -p "$crate_name" -- --list 2>/dev/null | grep -c ': test$')
  echo "$crate_name: $count tests"
done

# Rust test count by module (primary crate)
cargo test -p target_crate -- --list 2>/dev/null | \
  sed 's/::.*//' | sort | uniq -c | sort -rn | head -20

# Python test count
find tests/ -name 'test_*.py' -exec grep -c 'def test_' {} + 2>/dev/null | \
  awk -F: '{sum+=$2; print} END{print "TOTAL: " sum}'

# TypeScript/React test count
find desktop/src -name '*.test.tsx' -o -name '*.test.ts' 2>/dev/null | \
  xargs grep -c 'it(\|test(' 2>/dev/null | \
  awk -F: '{sum+=$2; print} END{print "TOTAL: " sum}'

# Test type classification (unit vs functional vs integration)
echo "=== Unit tests (no DB, no I/O) ==="
grep -rn '#\[test\]' src/ --include='*.rs' | wc -l

echo "=== Functional tests (in-memory SQLite) ==="
grep -rn 'setup_test_db\|create_test_pool\|in_memory' src/ --include='*.rs' | wc -l

echo "=== Integration tests ==="
find tests/ -name '*.rs' -exec grep -c '#\[test\]\|#\[tokio::test\]' {} + 2>/dev/null
```

### Deliverables

- Test inventory table (language, crate/module, count, type)
- Total test count and breakdown by category

---

## Phase 2 — Coverage

**Goal:** Estimate test coverage and identify module-level gaps.

### Steps

```bash
# Heuristic: modules with code but no tests
for dir in src/services src/db src/api; do
  for file in "$dir"/*.rs; do
    [ "$(basename "$file")" = "mod.rs" ] && continue
    module=$(basename "$file" .rs)
    test_count=$(grep -c '#\[test\]' "$file" 2>/dev/null || echo 0)
    if [ "$test_count" -eq 0 ]; then
      echo "NO TESTS: $file"
    fi
  done
done

# Coverage tool (if available)
# cargo tarpaulin --workspace --out json 2>/dev/null

# Access control action coverage check
total_actions=$(grep -c 'sub_task:' config/services/access-control-config.yaml 2>/dev/null || echo 0)
tested_actions=$(grep -c 'sub_task' tests/boundary_tests.rs 2>/dev/null || echo 0)
echo "Access control: $tested_actions / $total_actions actions tested"
```

### Thresholds

| Metric | Phase 1B Target | Phase 2 Target |
|--------|----------------|----------------|
| Rust line coverage (heuristic) | 60% | 75% |
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

### Steps

```bash
# Assertion density (assertions per test)
total_tests=$(grep -rn '#\[test\]\|#\[tokio::test\]' src/ tests/ --include='*.rs' | wc -l)
total_asserts=$(grep -rn 'assert!\|assert_eq!\|assert_ne!\|assert_matches!' src/ tests/ --include='*.rs' | \
  grep -v '// ' | wc -l)
echo "Assertion density: $total_asserts / $total_tests = $(echo "scale=2; $total_asserts / $total_tests" | bc) per test"

# Happy-path ratio (tests without error/edge case indicators)
happy=$(grep -rn '#\[test\]\|#\[tokio::test\]' src/ tests/ --include='*.rs' -l | \
  xargs grep -L 'error\|err\|invalid\|reject\|fail\|empty\|missing\|overflow\|boundary' | wc -l)
total_files=$(grep -rn '#\[test\]\|#\[tokio::test\]' src/ tests/ --include='*.rs' -l | wc -l)
echo "Happy-path only files: $happy / $total_files"

# Error case coverage
error_tests=$(grep -rn 'error\|err(\|invalid\|reject\|should_fail\|expect_err' src/ tests/ --include='*.rs' | \
  grep -v '^\s*//' | wc -l)
echo "Error-case test lines: $error_tests"

# Boundary/edge case tests
edge_tests=$(grep -rn 'empty\|zero\|max\|min\|overflow\|boundary\|edge' src/ tests/ --include='*.rs' | \
  grep -v '^\s*//' | wc -l)
echo "Edge-case test lines: $edge_tests"
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

### Steps

Per-service manifest compliance check (minimum requirements):

```bash
for service_file in src/services/*.rs; do
  service=$(basename "$service_file" .rs)
  [ "$service" = "mod" ] && continue

  echo "=== $service ==="

  # 3 unit tests per action (minimum)
  unit_tests=$(grep -c '#\[test\]' "$service_file" 2>/dev/null || echo 0)
  echo "  Unit tests: $unit_tests"

  # CRUD functional tests in db layer
  db_file="src/db/${service}.rs"
  db_tests=$(grep -c '#\[test\]\|#\[tokio::test\]' "$db_file" 2>/dev/null || echo 0)
  echo "  DB tests: $db_tests"

  # API contract tests
  api_file="src/api/${service}.rs"
  api_tests=$(grep -c '#\[test\]\|#\[tokio::test\]' "$api_file" 2>/dev/null || echo 0)
  echo "  API tests: $api_tests"

  # Standard column assertions (id, tenant_id, created_at)
  col_checks=$(grep -c 'tenant_id\|created_at' "$db_file" 2>/dev/null || echo 0)
  echo "  Column assertions: $col_checks"
done
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

**Goal:** Assess CI reliability and test suite operational health.

### Steps

```bash
# CI pass rate (last 20 pipeline runs)
glab api "projects/:id/pipelines?per_page=20&status=success" 2>/dev/null | jq length
glab api "projects/:id/pipelines?per_page=20&status=failed" 2>/dev/null | jq length

# Flaky test detection (tests that fail intermittently)
# Check CI logs for tests that passed on retry
glab api "projects/:id/pipelines?per_page=50" 2>/dev/null | \
  jq -r '.[].id' | head -20 | while read pid; do
  glab api "projects/:id/pipelines/$pid/jobs" 2>/dev/null | \
    jq -r '.[] | select(.status=="failed") | .name'
done | sort | uniq -c | sort -rn | head -10

# Suite timing
time cargo test --workspace 2>/dev/null

# Tests that take >5s individually (slow tests)
cargo test --workspace -- --list 2>/dev/null | head -5
# Note: Rust test framework doesn't natively report per-test timing
# Use cargo-nextest for detailed timing if available
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

**Goal:** Identify high-churn files with low test density — the riskiest code.

### Steps

```bash
# Top 20 most-changed files (last 90 days)
git log --since="90 days ago" --name-only --pretty=format: -- '*.rs' '*.ts' '*.py' | \
  sort | uniq -c | sort -rn | head -20

# Cross-reference with test coverage
# For each high-churn file, check if corresponding test file exists
git log --since="90 days ago" --name-only --pretty=format: -- '*.rs' | \
  sort | uniq -c | sort -rn | head -20 | while read count file; do
  if echo "$file" | grep -q 'src/services/\|src/db/\|src/api/'; then
    test_count=$(grep -c '#\[test\]' "$file" 2>/dev/null || echo 0)
    if [ "$test_count" -eq 0 ]; then
      echo "HIGH RISK: $file ($count changes, 0 tests)"
    fi
  fi
done

# Files changed in bug-fix commits without corresponding test additions
git log --since="90 days ago" --grep='fix(' --name-only --pretty=format: | \
  sort -u | while read file; do
  echo "Bug-fixed without test: $file"
done | head -10
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

### Steps

```bash
# StubLLM fixture inventory
find tests/fixtures/llm_stubs/ -type f 2>/dev/null | wc -l
ls tests/fixtures/llm_stubs/ 2>/dev/null

# Services using LLM that have stubs
grep -rn 'StubLLM\|stub_llm\|mock_llm' src/ tests/ --include='*.rs' | \
  sed 's|/[^/]*$||' | sort -u

# Error stub coverage (not just success stubs)
grep -rn 'error\|malformed\|timeout\|rate_limit' tests/fixtures/llm_stubs/ 2>/dev/null | wc -l

# Golden dataset / golden path tests
grep -rn 'golden\|gold_path\|e2e_chain' src/ tests/ --include='*.rs' | wc -l

# Confidence score assertions
grep -rn 'confidence\|score' src/ tests/ --include='*.rs' | grep 'assert' | wc -l
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

Compile all findings into `output/YYYY-MM-DD/TR{n}-test-tomographe.md` using the report template.

### Report Contents

1. **Summary table** — key metrics and scores at a glance
2. **Test inventory** — counts by language, crate, type
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

See `config.yaml` for thresholds and scope.

---

## Run History

| Run | Date | Trigger | Verdict | Report |
|-----|------|---------|---------|--------|
| TR1 | _pending_ | Initial baseline | — | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
