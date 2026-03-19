---
title: "Fix: Missing CI Stages"
status: current
last-updated: 2026-03-19
instrument: deployment-tomographe
severity-range: "Major"
---

# Fix: Missing CI Stages

## What this means

Your CI/CD pipeline is missing one or more standard stages that a production-grade project
should have. A complete pipeline typically includes lint, build, test, package, and deploy
stages. Missing stages mean that certain categories of defects — style violations, broken
builds, test failures, packaging errors, or deployment misconfigurations — can reach production
uncaught. The severity is Major because each missing stage is a gap in your automated quality
gate, increasing the risk that preventable issues escape to later (more expensive) phases.

## How to fix

### Python

**Complete GitLab CI pipeline for a Python project:**

```yaml
# .gitlab-ci.yml
stages:
  - lint
  - build
  - test
  - package
  - deploy

variables:
  PIP_CACHE_DIR: "$CI_PROJECT_DIR/.cache/pip"

cache:
  key:
    files:
      - requirements.lock
  paths:
    - .cache/pip

# --- LINT ---
lint:format:
  stage: lint
  image: python:3.11-slim
  script:
    - pip install ruff
    - ruff check src/ tests/
    - ruff format --check src/ tests/

lint:types:
  stage: lint
  image: python:3.11-slim
  script:
    - pip install mypy
    - mypy src/ --strict

# --- BUILD ---
build:wheel:
  stage: build
  image: python:3.11-slim
  script:
    - pip install build
    - python -m build
  artifacts:
    paths:
      - dist/
    expire_in: 1 week

# --- TEST ---
test:unit:
  stage: test
  image: python:3.11-slim
  needs: []
  script:
    - pip install -e ".[test]"
    - pytest tests/unit/ -v --cov=src --cov-report=term-missing
  coverage: '/TOTAL.*\s(\d+%)/'

test:integration:
  stage: test
  image: python:3.11-slim
  needs: []
  services:
    - postgres:16-alpine
  variables:
    POSTGRES_DB: test
    POSTGRES_USER: test
    POSTGRES_PASSWORD: test
  script:
    - pip install -e ".[test]"
    - pytest tests/integration/ -v --timeout=60

# --- PACKAGE ---
package:docker:
  stage: package
  image: docker:27
  services:
    - docker:27-dind
  needs:
    - build:wheel
  script:
    - docker build -t "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA" .
    - docker push "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA"
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

# --- DEPLOY ---
deploy:staging:
  stage: deploy
  image: alpine:3.20
  needs:
    - package:docker
    - test:unit
    - test:integration
  script:
    - echo "Deploy $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA to staging"
  environment:
    name: staging
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

### Rust

**Key GitLab CI jobs for a Rust project:**

```yaml
# .gitlab-ci.yml
stages: [lint, build, test, package]

cache:
  key: { files: [Cargo.lock] }
  paths: [.cargo/registry, target/]

lint:format:
  stage: lint
  image: rust:1.85-bookworm
  script: [cargo fmt --all --check]

lint:clippy:
  stage: lint
  image: rust:1.85-bookworm
  script: [cargo clippy --all-targets --all-features -- -D warnings]

build:release:
  stage: build
  image: rust:1.85-bookworm
  script: [cargo build --release]
  artifacts: { paths: [target/release/], expire_in: 1 week }

test:
  stage: test
  image: rust:1.85-bookworm
  needs: []
  script: [cargo test --workspace]

package:docker:
  stage: package
  image: docker:27
  services: [docker:27-dind]
  needs: [build:release]
  script:
    - docker build -t "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA" .
    - docker push "$CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA"
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

### TypeScript

**GitHub Actions workflow (key jobs):**

```yaml
# .github/workflows/ci.yml
name: CI
on: { push: { branches: [main] }, pull_request: {} }

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci
      - run: npx eslint "src/**/*.ts" && npx prettier --check "src/**/*.ts"
      - run: npx tsc --noEmit

  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci && npm test -- --coverage

  build:
    runs-on: ubuntu-latest
    needs: [lint, test]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: 22, cache: npm }
      - run: npm ci && npm run build

  package:
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    needs: [build]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/build-push-action@v5
        with:
          push: true
          tags: ghcr.io/${{ github.repository }}:${{ github.sha }}
```

### Go

**Key GitLab CI jobs for a Go project:**

```yaml
# .gitlab-ci.yml
stages: [lint, build, test, package]

cache:
  key: { files: [go.sum] }
  paths: [.go/pkg/mod]

lint:
  stage: lint
  image: golangci/golangci-lint:v1.62
  script: [golangci-lint run ./...]

build:
  stage: build
  image: golang:1.23
  script:
    - CGO_ENABLED=0 go build -ldflags="-s -w" -o bin/app ./cmd/app
  artifacts: { paths: [bin/], expire_in: 1 week }

test:
  stage: test
  image: golang:1.23
  needs: []
  script:
    - go test -v -race -coverprofile=coverage.out ./...
    - go tool cover -func=coverage.out
  coverage: '/total:\s+\(statements\)\s+(\d+\.\d+)%/'
```

### General

**The five essential CI stages:**

| Stage | Purpose | Fails when... |
|-------|---------|---------------|
| **lint** | Code style, static analysis, type checking | Formatting violations, lint errors, type errors |
| **build** | Compile source, produce artifacts | Syntax errors, missing dependencies, build config issues |
| **test** | Unit tests, integration tests | Functional regressions, broken contracts |
| **package** | Build Docker image, create release archive | Dockerfile errors, missing build artifacts |
| **deploy** | Push to staging/production environment | Infra misconfig, failed health checks |

**Stage ordering:** Lint first (cheapest to fail). Build and test in parallel when tests
don't need the build artifact. Package only on the default branch. Deploy to production
requires manual approval. Use `needs:` (GitLab) or job dependencies to maximise parallelism.

If you have nothing today, start with lint + build + test in a single CI job, then split
into separate stages as the project matures.

## Prevention

**Pipeline template library:**

Maintain a shared repository of CI templates per language stack. New projects include the
relevant template and customise as needed.

```yaml
# GitLab: include shared templates
include:
  - project: 'devops/ci-templates'
    file: '/templates/python.yml'
```

**Pipeline linting:** Validate CI config syntax in CI itself (`gitlab-ci-lint`,
`actionlint`) to catch YAML errors before they break the pipeline.

**MR checklist:** Require reviewers to verify that lint, build, and test stages exist and
pass. No `allow_failure: true` without documented justification.

**Stage coverage audit:** Periodically review each project's pipeline against the five-stage
standard. Track coverage in a project health dashboard.
