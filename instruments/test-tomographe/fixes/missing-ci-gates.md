---
title: "Fix: Missing CI Gates"
status: current
last-updated: 2026-03-19
instrument: test-tomographe
severity-range: "Major–Critical"
---

# Fix: Missing CI Gates

## What this means

Your project lacks CI pipeline enforcement that blocks merges when tests fail or coverage drops.
Without CI gates, test failures become advisory — developers can merge broken code when under
pressure, and coverage silently erodes. A test suite that does not run automatically on every
merge request is functionally the same as having no tests at all. The test-tomographe flags this
when it detects: no CI configuration, tests not running in the pipeline, pipeline results not
required for merge, or missing coverage thresholds.

## How to fix

### Python

**GitLab CI pipeline with test gates:**

```yaml
# .gitlab-ci.yml
stages:
  - lint
  - test

lint:
  stage: lint
  image: python:3.12-slim
  script:
    - pip install ruff
    - ruff check src/ tests/
    - ruff format --check src/ tests/

unit-tests:
  stage: test
  image: python:3.12-slim
  script:
    - pip install -r requirements.txt -r requirements-test.txt
    - pytest tests/unit/ -v --cov=src --cov-report=term-missing --cov-fail-under=80
  coverage: '/(?i)total.*? (\d+(?:\.\d+)?\%)/'
```

**GitHub Actions equivalent:**

```yaml
# .github/workflows/test.yml
name: Tests
on:
  pull_request:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt -r requirements-test.txt
      - run: pytest tests/ -v --cov=src --cov-fail-under=80
```

### Rust

**GitLab CI pipeline:**

```yaml
stages:
  - lint
  - test

fmt-check:
  stage: lint
  image: rust:1.85-bookworm
  script:
    - rustup component add rustfmt
    - cargo fmt --all --check

clippy:
  stage: lint
  image: rust:1.85-bookworm
  script:
    - rustup component add clippy
    - cargo clippy --all-targets --all-features -- -D warnings

tests:
  stage: test
  image: rust:1.85-bookworm
  script:
    - cargo test --workspace
```

**GitHub Actions equivalent:**

```yaml
name: Tests
on:
  pull_request:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: dtolnay/rust-toolchain@stable
        with: { components: "rustfmt, clippy" }
      - run: cargo fmt --all --check
      - run: cargo clippy --all-targets -- -D warnings
      - run: cargo test --workspace
```

### TypeScript

**GitLab CI pipeline:**

```yaml
stages:
  - lint
  - test

lint:
  stage: lint
  image: node:20-slim
  script:
    - npm ci
    - npx eslint src/ tests/
    - npx tsc --noEmit

unit-tests:
  stage: test
  image: node:20-slim
  script:
    - npm ci
    - npx vitest run --coverage --coverage.thresholds.lines=80
  coverage: '/All files[^|]*\|[^|]*\s+([\d\.]+)/'
```

### Go

**GitLab CI pipeline:**

```yaml
stages:
  - lint
  - test

lint:
  stage: lint
  image: golangci/golangci-lint:v1.62
  script:
    - golangci-lint run ./...

unit-tests:
  stage: test
  image: golang:1.23-bookworm
  script:
    - go test -v -race -coverprofile=coverage.out ./...
    - go tool cover -func=coverage.out
    - |
      TOTAL=$(go tool cover -func=coverage.out | grep total | awk '{print $3}' | tr -d '%')
      if [ "$(echo "$TOTAL < 80" | bc)" -eq 1 ]; then
        echo "Coverage ${TOTAL}% is below 80% threshold" && exit 1
      fi
  coverage: '/total:\s+\(statements\)\s+(\d+\.\d+)%/'
```

### General

**Azure Pipelines example:**

```yaml
trigger:
  branches: { include: [main] }
pr:
  branches: { include: [main] }
pool:
  vmImage: ubuntu-latest
steps:
  - script: |
      pip install -r requirements.txt -r requirements-test.txt
      pytest tests/ -v --cov=src --cov-fail-under=80 --junitxml=test-results.xml
    displayName: "Run tests"
  - task: PublishTestResults@2
    inputs: { testResultsFormat: JUnit, testResultsFiles: test-results.xml }
    condition: always()
```

**Enforcing merge blocking:**

- **GitLab:** Settings > Merge Requests > "Pipelines must succeed" (Free tier). Also set "All
  threads must be resolved."
- **GitHub:** Settings > Branches > Branch protection rules > "Require status checks to pass
  before merging."
- **Azure DevOps:** Branch policies > "Build validation." Add the pipeline as a required policy.

**Essential CI gates checklist:**

1. **Lint/format check** — catches style issues before tests run. Fail fast.
2. **Unit tests** — all must pass. No exceptions.
3. **Integration tests** — run against real dependencies (test containers or CI services).
4. **Coverage threshold** — fail if coverage drops below the project baseline.
5. **Security audit** — dependency vulnerability scan on every MR.

## Prevention

**Pipeline-as-code review:**

- CI configuration changes go in their own commit with `ci(scope): description` prefix.
- Review CI changes with the same rigour as application code.
- Test pipeline changes on a branch before merging to main.

**Monitor pipeline health:**

- Track pipeline pass rate. Below 95% indicates systemic issues.
- Alert when main has been failing for more than 1 hour.
- Track pipeline duration. Over 15 minutes for small projects causes developers to skip CI.
  Optimise with caching and parallelism.
