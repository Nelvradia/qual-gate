---
title: "Fix: Non-Reproducible Builds"
status: current
last-updated: 2026-03-19
instrument: deployment-tomographe
severity-range: "Major"
---

# Fix: Non-Reproducible Builds

## What this means

Your build process produces different outputs from the same source code depending on when or
where it runs. Common causes include unpinned dependencies (installing whatever version is
"latest" at build time), missing lockfiles, uncontrolled build environments, and timestamp or
host-dependent build steps. Non-reproducible builds are Major because they make it impossible
to reliably recreate a known-good artifact, complicate debugging ("it worked yesterday"), and
create security risk — you cannot verify that a deployed binary corresponds to audited source
code if the build is not deterministic.

## How to fix

### Python

**Lockfile enforcement:**

```toml
# pyproject.toml — define dependencies with compatible ranges
[project]
dependencies = [
    "httpx>=0.27,<1.0",
    "sqlalchemy>=2.0,<3.0",
    "pydantic>=2.5,<3.0",
]
```

```bash
# Generate a locked requirements file with exact versions
pip-compile --generate-hashes --output-file=requirements.lock pyproject.toml

# Install from lockfile only — fail if lockfile is stale
pip install --require-hashes -r requirements.lock

# With poetry
poetry lock
poetry install --no-root
```

**CI check — lockfile freshness:**

```bash
# Fail if lockfile doesn't match pyproject.toml
pip-compile --generate-hashes --output-file=/tmp/fresh.lock pyproject.toml
diff requirements.lock /tmp/fresh.lock \
  || (echo "Lockfile is stale. Run: pip-compile" && exit 1)
```

**Reproducible Docker build:**

```dockerfile
# Dockerfile
FROM python:3.11-slim AS builder

COPY requirements.lock .
RUN pip install --no-cache-dir --require-hashes -r requirements.lock

COPY src/ src/
RUN pip install --no-deps .

FROM python:3.11-slim
RUN useradd --create-home appuser
COPY --from=builder /usr/local/lib/python3.11/site-packages \
     /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/ /usr/local/bin/
USER appuser
ENTRYPOINT ["myapp"]
```

### Rust

**Cargo.lock must be committed for binaries:**

```bash
# For applications/binaries: always commit Cargo.lock
git add Cargo.lock

# For libraries: .gitignore Cargo.lock (consumers resolve their own)
```

**Pin the Rust toolchain:**

```toml
# rust-toolchain.toml — checked into the repository
[toolchain]
channel = "1.85.0"
components = ["rustfmt", "clippy"]
```

**Reproducible Docker build:**

```dockerfile
FROM rust:1.85-bookworm AS builder
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
# Cache dependency build
RUN mkdir src && echo "fn main(){}" > src/main.rs \
    && cargo build --release && rm -rf src

COPY src/ src/
RUN cargo build --release

FROM debian:bookworm-slim
RUN useradd --create-home appuser
COPY --from=builder /app/target/release/myapp /usr/local/bin/
USER appuser
ENTRYPOINT ["myapp"]
```

### TypeScript

**Lockfile enforcement:**

```bash
# npm: use ci (not install) in CI — fails if lockfile is out of sync
npm ci

# yarn: use --frozen-lockfile
yarn install --frozen-lockfile

# pnpm: use --frozen-lockfile
pnpm install --frozen-lockfile
```

**Pin Node.js version:**

```
# .nvmrc — checked into the repository
22.12.0
```

```json
// package.json — enforce engine version
{
  "engines": {
    "node": ">=22.12.0 <23.0.0",
    "npm": ">=10.0.0"
  }
}
```

**Reproducible Docker build:**

```dockerfile
FROM node:22.12-slim AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --ignore-scripts
COPY tsconfig.json ./
COPY src/ src/
RUN npm run build

FROM node:22.12-slim
RUN useradd --create-home appuser
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts
COPY --from=builder /app/dist/ dist/
USER appuser
CMD ["node", "dist/index.js"]
```

### Go

**Module verification:**

```bash
# Verify go.sum checksums match downloaded modules
go mod verify

# Tidy and check for drift
go mod tidy
git diff --exit-code go.mod go.sum \
  || (echo "go.mod/go.sum are not tidy. Run: go mod tidy" && exit 1)
```

**Pin the Go version:**

```
# go.mod — specifies the Go version
module example.com/myapp

go 1.23.0
```

```bash
# Build with CGO disabled for a fully static binary
CGO_ENABLED=0 go build -trimpath \
  -ldflags="-s -w -buildid=" \
  -o bin/myapp ./cmd/myapp
```

The flags above improve reproducibility:

- `-trimpath` removes local filesystem paths from the binary.
- `-ldflags="-s -w"` strips debug symbols (consistent across machines).
- `-buildid=` sets an empty build ID (otherwise it changes per build).

**Reproducible Docker build:**

```dockerfile
FROM golang:1.23-bookworm AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download && go mod verify
COPY . .
RUN CGO_ENABLED=0 go build -trimpath \
    -ldflags="-s -w -buildid=" \
    -o /app/bin/myapp ./cmd/myapp

FROM gcr.io/distroless/static-debian12:nonroot
COPY --from=builder /app/bin/myapp /usr/local/bin/
ENTRYPOINT ["myapp"]
```

### General

**Root causes of non-reproducible builds and their fixes:**

| Cause | Fix |
|-------|-----|
| No lockfile | Generate and commit a lockfile |
| `pip install` / `npm install` in CI | Use `pip install -r requirements.lock` / `npm ci` |
| `FROM python:3.11` (floating tag) | Pin: `FROM python:3.11.11-slim@sha256:abc...` |
| Build depends on current date/time | Remove timestamps or make them deterministic |
| Different OS/arch in dev vs CI | Use Docker for all builds, pin base image |
| Unpinned build tools (linters, formatters) | Pin in dev dependencies or pre-commit config |
| Floating `apt-get install` packages | Pin: `apt-get install curl=7.88.1-10+deb12u8` |

**Docker image pinning:**

```dockerfile
# BAD: floating tag — changes without notice
FROM python:3.11-slim

# BETTER: specific patch version
FROM python:3.11.11-slim

# BEST: pinned by digest — immutable
FROM python:3.11.11-slim@sha256:8f64a67710e8e09a5b6...
```

**Build artifact verification:**

After building, generate a checksum of the artifact and store it alongside the artifact.
Compare checksums across builds to detect non-determinism.

```bash
sha256sum dist/*.whl > dist/checksums.sha256
```

**Supply chain security:** Use `--require-hashes` (pip) to verify downloaded packages.
Enable Sigstore/cosign for container image signing. Run `cargo vet` (Rust) for dependency
review.

## Prevention

**CI pipeline — reproducibility gate:**

```yaml
# GitLab CI
lockfile-check:
  stage: lint
  script:
    # Python
    - pip-compile --generate-hashes pyproject.toml -o /tmp/fresh.lock
    - diff requirements.lock /tmp/fresh.lock
    # Node
    - npm ci  # fails if package-lock.json is stale
    # Go
    - go mod tidy && git diff --exit-code go.mod go.sum
    # Rust
    - cargo generate-lockfile && git diff --exit-code Cargo.lock
  allow_failure: false
```

**Dependency update workflow:** Use Renovate or Dependabot to open MRs when new versions
are available. Never update dependencies implicitly during a build — updates happen in
dedicated MRs that regenerate the lockfile and run the full test suite.
