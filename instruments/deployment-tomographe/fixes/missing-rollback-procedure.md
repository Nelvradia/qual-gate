---
title: "Fix: Missing Rollback Procedure"
status: current
last-updated: 2026-03-19
instrument: deployment-tomographe
severity-range: "Major–Critical"
---

# Fix: Missing Rollback Procedure

## What this means

Your project can deploy new versions but has no documented or automated way to revert to a
previous known-good state when a deployment goes wrong. Without a rollback procedure, a bad
deployment becomes an emergency requiring manual intervention under pressure — exactly the
conditions where mistakes happen. The severity ranges from Major (no documented rollback
for non-critical services) to Critical (no rollback capability for systems handling production
traffic, financial data, or safety-critical operations). A deployment pipeline without rollback
is a one-way door that you may need to back through in a hurry.

## How to fix

### Python

**Docker-based rollback with tagged images:**

```python
# scripts/rollback.py
"""Roll back a service to a previous Docker image tag."""
from __future__ import annotations

import subprocess
import sys
import logging

logger = logging.getLogger(__name__)


def get_previous_tag(service: str, registry: str) -> str:
    """Fetch the second-most-recent tag from the registry."""
    result = subprocess.run(
        ["docker", "image", "ls", "--format", "{{.Tag}}",
         f"{registry}/{service}"],
        capture_output=True, text=True, check=True,
    )
    tags = [t for t in result.stdout.strip().split("\n") if t != "latest"]
    tags.sort(reverse=True)
    if len(tags) < 2:
        raise RuntimeError(f"No previous tag available for {service}")
    return tags[1]


def rollback_service(
    service: str,
    target_tag: str | None = None,
    compose_file: str = "docker-compose.yml",
) -> None:
    """Roll back a service to a specific or previous tag."""
    if target_tag is None:
        target_tag = get_previous_tag(service, registry="registry.example.com")

    image = f"registry.example.com/{service}:{target_tag}"
    logger.info("Rolling back %s to %s", service, image)

    subprocess.run(
        ["docker", "compose", "-f", compose_file, "pull", service],
        env={**dict(__import__("os").environ), f"{service.upper()}_IMAGE": image},
        check=True,
    )
    subprocess.run(
        ["docker", "compose", "-f", compose_file, "up", "-d", service],
        check=True,
    )
    logger.info("Rollback of %s to %s complete", service, target_tag)
```

After rollback, poll the service's `/health` endpoint with a timeout to verify the
rolled-back version is serving correctly before declaring the rollback complete.

### Rust

The same pattern applies: shell out to `docker compose pull` + `docker compose up -d` with
the target image tag set via environment variable. Use `anyhow` for error propagation and
`tracing` to log rollback events.

### TypeScript

```typescript
// scripts/rollback.ts
import { execSync } from "child_process";

function rollback(service: string, tag: string, composeFile = "docker-compose.yml"): void {
  const image = `registry.example.com/${service}:${tag}`;
  console.log(`Rolling back ${service} to ${image}`);

  execSync(`docker compose -f ${composeFile} pull ${service}`, {
    env: { ...process.env, [`${service.toUpperCase()}_IMAGE`]: image },
  });
  execSync(`docker compose -f ${composeFile} up -d --no-deps ${service}`);
  console.log(`Rollback complete`);
}
```

### Go

```go
package deploy

import (
    "fmt"
    "os"
    "os/exec"
)

// Rollback reverts a service to a specific tag using docker compose.
func Rollback(service, tag, composeFile string) error {
    image := fmt.Sprintf("registry.example.com/%s:%s", service, tag)

    pull := exec.Command("docker", "compose", "-f", composeFile, "pull", service)
    pull.Env = append(os.Environ(), fmt.Sprintf("%s_IMAGE=%s", service, image))
    if out, err := pull.CombinedOutput(); err != nil {
        return fmt.Errorf("pull %s: %w\n%s", image, err, out)
    }

    up := exec.Command("docker", "compose", "-f", composeFile,
        "up", "-d", "--no-deps", service)
    if out, err := up.CombinedOutput(); err != nil {
        return fmt.Errorf("restart %s: %w\n%s", service, err, out)
    }
    return nil
}
```

Track every deployment in a history file (service, tag, timestamp, commit SHA) so the
rollback target is selectable from history, not guessed.

### General

**Blue-green deployment pattern:**

Run two identical environments (blue and green). At any time, one serves production traffic
and the other is idle. Deploy to the idle environment, verify it, then switch traffic.
Rollback is instant — switch traffic back to the previous environment.

```
                    ┌──────────────┐
    Traffic ───────►│ Load Balancer│
                    └──────┬───────┘
                           │
                ┌──────────┴──────────┐
                │                     │
         ┌──────▼──────┐       ┌──────▼──────┐
         │  Blue (v1)  │       │  Green (v2) │
         │  [active]   │       │  [standby]  │
         └─────────────┘       └─────────────┘
```

Implementation with Docker Compose:

Use Docker Compose profiles (`blue`/`green`) with a load balancer (Traefik, nginx). Deploy
to the idle profile, verify its health endpoint, then switch the active profile. Rollback
is instant — switch back to the previous profile.

**Canary release pattern:** Route a small percentage of traffic (e.g., 10%) to the new
version via weighted routing. Monitor error rates and latency. If metrics degrade, set
the canary weight to 0.

**Database migration rollback:**

Application rollback often requires database rollback too. This introduces a critical
ordering constraint:

1. **Deploy forward:** Run migration, then deploy new app version.
2. **Rollback:** Deploy old app version first, then revert migration.

If the migration is destructive (dropped a column the old version needs), rollback is
impossible without data restoration. To avoid this:

- Make migrations backward-compatible where possible (add columns before removing old ones).
- Use a two-phase migration strategy: Phase 1 adds the new schema alongside the old.
  Phase 2 removes the old schema only after the new version is confirmed stable.

**Rollback runbook:** Every deployable service must have a `docs/runbook/rollback.md`
covering: prerequisites (registry access, DB credentials), step-by-step procedure,
expected duration, maximum acceptable downtime, and escalation contacts.

## Prevention

**CI pipeline — rollback readiness check:**

```yaml
# GitLab CI
rollback-readiness:
  stage: test
  script:
    # Verify rollback documentation exists
    - test -f docs/runbook/rollback.md
        || (echo "Missing rollback runbook" && exit 1)
    # Verify previous image is still available in registry
    - PREV_TAG=$(git describe --tags --abbrev=0 HEAD~1 2>/dev/null || echo "none")
    - |
      if [ "$PREV_TAG" != "none" ]; then
        docker manifest inspect "$CI_REGISTRY_IMAGE:$PREV_TAG" > /dev/null
      fi
    # Verify health endpoint exists
    - docker compose up -d
    - curl --retry 5 --retry-delay 2 -f http://localhost:8080/health
    - docker compose down
  rules:
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH
```

**Image retention:** Keep at least the last 5 tagged images per service. Never
garbage-collect images deployed in the last 30 days. Tag releases with git tags
(`v1.2.3`), not just `latest`.

**Rollback testing:** Monthly planned rollback in staging, quarterly simulated production
rollback, and after every deployment pipeline change.
