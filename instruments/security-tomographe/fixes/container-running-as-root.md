---
title: "Fix: Container Running as Root"
status: current
last-updated: 2026-03-19
instrument: security-tomographe
severity-range: "Major"
---

# Fix: Container Running as Root

## What this means

Your container is running processes as the root user (UID 0). If an attacker exploits a
vulnerability in your application, they gain root-level access inside the container. Combined with
misconfigured mounts, missing seccomp profiles, or kernel vulnerabilities, this can escalate to
host-level compromise. Running as a non-root user is a fundamental container security control that
limits the blast radius of any in-container exploit.

## How to fix

### Python

```dockerfile
# ---- Build stage ----
FROM python:3.12-slim AS builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

COPY . .

# ---- Runtime stage ----
FROM python:3.12-slim

# Create non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --shell /bin/false --create-home appuser

COPY --from=builder /install /usr/local
COPY --from=builder /app /app

WORKDIR /app

# Drop to non-root before CMD
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]

CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--user", "appuser", "--group", "appuser", "app:create_app()"]
```

For Django/Flask apps using gunicorn, ensure the gunicorn worker also drops privileges:

```ini
# gunicorn.conf.py
bind = "0.0.0.0:8000"
user = "appuser"
group = "appuser"
workers = 4
```

### Rust

```dockerfile
# ---- Build stage ----
FROM rust:1.85-bookworm AS builder

WORKDIR /app
COPY Cargo.toml Cargo.lock ./
# Cache dependencies
RUN mkdir src && echo "fn main() {}" > src/main.rs \
    && cargo build --release \
    && rm -rf src

COPY src/ src/
RUN touch src/main.rs && cargo build --release

# ---- Runtime stage (minimal) ----
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid 1000 --shell /bin/false --create-home appuser

COPY --from=builder /app/target/release/myapp /usr/local/bin/myapp

USER appuser

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD ["/usr/local/bin/myapp", "--healthcheck"]

CMD ["/usr/local/bin/myapp"]
```

For fully static Rust binaries (musl target), use `scratch` or `distroless` as the final stage
(see Go section below for the pattern).

### TypeScript

```dockerfile
FROM node:22-alpine AS builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --production=false
COPY . .
RUN npm run build && npm prune --production

# ---- Runtime stage ----
FROM node:22-alpine

# dumb-init handles PID 1 responsibilities (signal forwarding, zombie reaping)
RUN apk add --no-cache dumb-init

# node:alpine already has user 'node' (UID 1000)
ENV NODE_ENV=production
WORKDIR /app

COPY --from=builder --chown=node:node /app/dist ./dist
COPY --from=builder --chown=node:node /app/node_modules ./node_modules
COPY --from=builder --chown=node:node /app/package.json ./

USER node

EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s CMD ["node", "-e", \
    "require('http').get('http://localhost:3000/health', r => process.exit(r.statusCode === 200 ? 0 : 1))"]

ENTRYPOINT ["dumb-init", "--"]
CMD ["node", "dist/server.js"]
```

### Go

Go produces static binaries, enabling the smallest possible final images:

```dockerfile
# ---- Build stage ----
FROM golang:1.23-bookworm AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /app/server ./cmd/server

# ---- Option A: scratch (smallest, no shell, no debug tools) ----
FROM scratch

COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/
COPY --from=builder /app/server /server

# scratch has no user database — set UID directly
USER 65534:65534

EXPOSE 8080
ENTRYPOINT ["/server"]

# ---- Option B: distroless (small, has some debug support) ----
# FROM gcr.io/distroless/static-debian12:nonroot
# COPY --from=builder /app/server /server
# EXPOSE 8080
# ENTRYPOINT ["/server"]
```

### General

**Docker security best practices:**

1. **Read-only root filesystem** — prevents attackers from writing to the container filesystem:
   ```yaml
   # docker-compose.yml
   services:
     app:
       image: myapp:latest
       read_only: true
       tmpfs:
         - /tmp
         - /var/run
   ```

2. **Drop all capabilities, add back only what's needed:**
   ```yaml
   services:
     app:
       cap_drop:
         - ALL
       cap_add:
         - NET_BIND_SERVICE  # only if binding to ports < 1024
   ```

3. **Resource limits** — prevent resource exhaustion attacks:
   ```yaml
   services:
     app:
       deploy:
         resources:
           limits:
             cpus: "2.0"
             memory: 512M
           reservations:
             cpus: "0.5"
             memory: 128M
   ```

4. **Kubernetes securityContext:**
   ```yaml
   apiVersion: v1
   kind: Pod
   spec:
     securityContext:
       runAsNonRoot: true
       runAsUser: 1000
       runAsGroup: 1000
       fsGroup: 1000
     containers:
       - name: app
         securityContext:
           allowPrivilegeEscalation: false
           readOnlyRootFilesystem: true
           capabilities:
             drop: ["ALL"]
         resources:
           limits:
             cpu: "2"
             memory: "512Mi"
   ```

5. **No new privileges flag:**
   ```bash
   docker run --security-opt=no-new-privileges:true myapp
   ```

## Prevention

- **Dockerfile linting:** Run `hadolint` in CI. It flags missing `USER` directives:
  ```yaml
  # .gitlab-ci.yml
  hadolint:
    stage: lint
    image: hadolint/hadolint:v2.12.0
    script:
      - hadolint Dockerfile
  ```
- **Image scanning:** Use `trivy image --severity HIGH,CRITICAL myapp:latest` in CI to detect
  containers running as root and known CVEs.
- **Policy enforcement:** Use OPA/Gatekeeper or Kyverno in Kubernetes to reject pods that
  run as root (`runAsNonRoot: true` policy).
- **Compose validation:** Add a CI step that parses `docker-compose.yml` and verifies every
  service has `user:` or the image defines a non-root `USER`.
- **Base image policy:** Maintain an approved base image list. Prefer `-slim` or `-alpine`
  variants. Never use `:latest` tags.
