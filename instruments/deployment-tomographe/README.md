# deployment-tomographe/

**CI/CD and deployment health scanner.** Audits pipeline structure, build reproducibility, artifact generation, update mechanisms, rollback capability, and environment parity.

**Covers Sections:** S9 (Deployment & Release)

---

## Quick Start

```bash
"Read instruments/deployment-tomographe/README.md and execute a full deployment scan."
"Read instruments/deployment-tomographe/README.md and execute Phase 3 (Artifact & Distribution) only."
```

---

## Scan Phases

| Phase | Name | What It Does | Tools |
|-------|------|-------------|-------|
| **1** | Pipeline Structure | Audit CI stages, job coverage, blocking gates, parallelism | CI config analysis |
| **2** | Build Reproducibility | Verify locked deps, pinned images, deterministic builds | Lockfiles, docker-compose, Dockerfile |
| **3** | Artifact & Distribution | Validate artifact generation, signing, distribution channels, updater config | CI output, config |
| **4** | Rollback & Recovery | Verify rollback procedures, backup integration, blue-green readiness | Runbooks, Docker config |
| **5** | Environment Parity | Compare dev ↔ CI ↔ prod configurations for drift | Config diff |
| **6** | Release Process | Validate versioning, tagging, changelog, quality gate integration | Git tags, VERSION files, CI |
| **7** | Report | Compile findings | Template filling |

---

## Phase 1 — Pipeline Structure

**Goal:** Verify CI pipeline is complete, correct, and properly gates releases.

```bash
# Pipeline stages
grep '^stages:' -A 20 .gitlab-ci.yml 2>/dev/null | head -25
# Expected: validate → test → build → integration → release → deploy

# Total job count
grep -c '^\S.*:$' .gitlab-ci.yml 2>/dev/null | head -1

# Jobs per stage
for stage in validate test build integration release deploy; do
  count=$(grep -B5 "stage: $stage" .gitlab-ci.yml 2>/dev/null | grep -c '^\S.*:$')
  echo "$stage: $count jobs"
done

# Merge-blocking jobs (should NOT have allow_failure: true)
grep -B5 'allow_failure: true' .gitlab-ci.yml 2>/dev/null
# These are advisory-only and don't gate merges

# Test jobs that SHOULD be blocking
for job in 'test' 'fmt' 'lint' 'clippy' 'pytest'; do
  grep -A10 "$job" .gitlab-ci.yml 2>/dev/null | grep -q 'allow_failure' && \
    echo "WARNING: $job is allow_failure" || echo "OK: $job is blocking"
done

# Quality gate job
grep -A10 'quality-gate\|dr-gate' .gitlab-ci.yml 2>/dev/null
# Should exist, trigger on tags, validate quality report

# Pipeline triggers
grep 'only:\|rules:\|except:' .gitlab-ci.yml 2>/dev/null | head -20

# Timeout configuration
grep 'timeout:' .gitlab-ci.yml 2>/dev/null | head -10
```

### Pipeline Checklist

- [ ] All expected stages present (e.g., validate, test, build, integration, release, deploy)
- [ ] Format/lint check is merge-blocking
- [ ] Static analysis is merge-blocking
- [ ] Test suite is merge-blocking
- [ ] Integration tests run on merge to main
- [ ] Quality gate job exists and validates reports on tags
- [ ] Build jobs produce artifacts (packages, Docker images)
- [ ] No critical job has `allow_failure: true`
- [ ] Timeouts configured (prevent hung jobs)

### Severity Rules

| Finding | Severity |
|---------|----------|
| Test job has `allow_failure: true` | **Major** |
| Missing test stage entirely | **Critical** |
| Quality gate not configured | **Minor** |
| No timeout on build/integration jobs | **Minor** |
| Missing stage (e.g., no integration tests) | **Minor** |

---

## Phase 2 — Build Reproducibility

**Goal:** Verify that builds are deterministic and dependencies locked.

```bash
# Lockfiles committed?
for lockfile in Cargo.lock package-lock.json yarn.lock poetry.lock Pipfile.lock; do
  git ls-files | grep -q "$lockfile" && echo "OK: $lockfile tracked" || echo "CHECK: $lockfile not tracked"
done

# Docker images pinned to digest?
grep 'image:' docker-compose.yml 2>/dev/null | while read line; do
  echo "$line" | grep -q 'sha256' && echo "PINNED: $line" || echo "UNPINNED: $line"
done

# Dockerfile FROM uses pinned digest?
find . -name 'Dockerfile' -not -path '*/target/*' | while read df; do
  grep '^FROM' "$df" | while read from; do
    echo "$from" | grep -q 'sha256\|@' && echo "PINNED: $df → $from" || echo "UNPINNED: $df → $from"
  done
done

# Toolchain pinned?
cat rust-toolchain.toml 2>/dev/null || cat rust-toolchain 2>/dev/null || echo "INFO: No rust-toolchain file"
cat .python-version 2>/dev/null || echo "INFO: No .python-version file"
cat .node-version 2>/dev/null || cat .nvmrc 2>/dev/null || echo "INFO: No node version file"

# Build cache configuration
grep -A5 'cache:' .gitlab-ci.yml 2>/dev/null | head -15

# Vendor directory exists?
[ -d vendor/ ] && echo "OK: Vendor dir exists" || echo "INFO: No vendor directory"
```

### Checklist

- [ ] Lockfiles committed and not gitignored
- [ ] Docker base images pinned to digest (not just tag)
- [ ] Language toolchain version pinned
- [ ] CI build cache configured (faster builds)
- [ ] Vendored dependencies if offline builds required

---

## Phase 3 — Artifact & Distribution

**Goal:** Verify that all deliverable artifacts are correctly built and distributed.

```bash
# Build jobs and artifact generation
grep -A20 'build' .gitlab-ci.yml 2>/dev/null | grep -E 'artifacts|package|bundle|dist'

# Docker image push
grep -A10 'docker' .gitlab-ci.yml 2>/dev/null | grep -E 'push|registry|tag'

# Signing configuration (should exist but key not in repo)
git ls-files | grep -E 'keystore|\.jks|\.p12|\.pem|signing' && \
  echo "WARNING: Signing key material in repo!" || echo "OK: No signing keys in repo"

# Artifact retention policy
grep -A5 'artifacts:' .gitlab-ci.yml 2>/dev/null | grep 'expire_in' | head -5
```

### Artifact Checklist

- [ ] Primary artifacts built in CI (release variant)
- [ ] Artifacts signed where applicable (signing config exists, key not in repo)
- [ ] Docker images pushed to `<registry>` with proper tags
- [ ] Artifact retention policy configured in CI

---

## Phase 4 — Rollback & Recovery

**Goal:** Verify that failed deployments can be safely reversed.

```bash
# Rollback runbook exists?
find docs/ -name '*rollback*' -o -name '*disaster*' -o -name '*recovery*' 2>/dev/null

# Docker Compose rollback capability
# Can we reference specific image versions?
grep 'image:' docker-compose.yml 2>/dev/null | head -10

# Database migration rollback
grep -rn 'down\|rollback\|revert' src/ --include='*.rs' --include='*.py' --include='*.sql' | head -10

# Backup integration
grep -rn 'backup' config/ docker-compose.yml docs/ --include='*.yaml' --include='*.yml' --include='*.md' 2>/dev/null | head -10

# Previous version retention
# Are old Docker images kept? Old packages?
grep 'expire\|retention\|keep' .gitlab-ci.yml 2>/dev/null | head -5
```

### Checklist

- [ ] Rollback runbook exists in documentation
- [ ] Docker images tagged with version (can pull previous version)
- [ ] Database migrations have down/rollback path
- [ ] Backup runs before deployment (or independently)
- [ ] Procedure for reverting permission/access control configuration changes
- [ ] Previous artifact versions retained

---

## Phase 5 — Environment Parity

**Goal:** Verify dev, CI, and prod environments are consistent.

```bash
# Docker Compose variants
ls docker-compose*.yml 2>/dev/null
# Expected: docker-compose.yml (prod) + docker-compose.ci.yml (CI overlay)

# Diff CI overlay vs prod
diff <(yq '.services | keys' docker-compose.yml 2>/dev/null) \
     <(yq '.services | keys' docker-compose.ci.yml 2>/dev/null) 2>/dev/null

# Environment variables in CI vs prod
grep -A5 'variables:' .gitlab-ci.yml 2>/dev/null | head -20
grep 'environment:' -A20 docker-compose.yml 2>/dev/null | head -30

# Toolchain versions: local vs CI
echo "Local Rust: $(rustc --version 2>/dev/null)"
echo "Local Python: $(python3 --version 2>/dev/null)"
echo "Local Node: $(node --version 2>/dev/null)"
grep -E 'rust|python|node' .gitlab-ci.yml 2>/dev/null | head -10
```

---

## Phase 6 — Release Process

**Goal:** Verify versioning and release workflow.

```bash
# VERSION files
find . -name 'VERSION' -not -path '*/node_modules/*' -not -path '*/target/*' | while read v; do
  echo "$v: $(cat "$v" 2>/dev/null || echo 'NOT_FOUND')"
done

# COMPATIBILITY.yaml (if multi-component)
cat COMPATIBILITY.yaml 2>/dev/null | head -20

# Git tags (recent)
git tag --sort=-creatordate 2>/dev/null | head -10

# Tag naming convention
git tag 2>/dev/null | head -10
# Expected: vX.Y.Z or component/vX.Y.Z

# CHANGELOG existence
[ -f CHANGELOG.md ] && echo "OK: CHANGELOG.md exists" || echo "MISSING: CHANGELOG.md"

# Versioning scripts
find . -name '*version*' -path '*/scripts/*' 2>/dev/null
```

### Checklist

- [ ] VERSION files exist for each component/service
- [ ] COMPATIBILITY.yaml tracks inter-component compatibility (if multi-component)
- [ ] Git tags follow `vX.Y.Z` or `component/vX.Y.Z` convention
- [ ] CHANGELOG.md exists (or squash commit messages serve as log)
- [ ] Version validation script validates version consistency
- [ ] Quality gate validates reports before release tag

---

## Output

Reports are written to `output/YYYY-MM-DD/DP<N>-deployment-tomographe.md`.

---

## Configuration

```yaml
thresholds:
  pipeline:
    min_stages: 4
    max_allow_failure_critical_jobs: 0
    required_blocking_jobs: [format_check, lint, test]
  reproducibility:
    lockfiles_committed: true
    docker_images_pinned: true
    toolchain_pinned: true
  artifacts:
    primary_built: true
    docker_pushed: true
  rollback:
    runbook_exists: true
    migration_reversible: true
    backup_before_deploy: true
  release:
    version_files_exist: true
    compatibility_yaml_exists: true
    changelog_exists: true

scope:
  ci_config: .gitlab-ci.yml
  compose_files: [docker-compose.yml, docker-compose.ci.yml]
  dockerfiles: ['**/Dockerfile']
  version_files: ['**/VERSION']
  operations_docs: docs/operations/
```

---

## Run History

| Run | Date | Trigger | Report |
|-----|------|---------|--------|
| DP1 | _pending_ | Initial baseline | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
