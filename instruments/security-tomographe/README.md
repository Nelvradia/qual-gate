# security-tomographe

**Security posture scanner for the target project.** Scans dependencies, secrets, attack surface, encryption, container hardening, and AI-specific threats (prompt injection, data exfiltration). Produces a severity-rated report with drift tracking and auto-fixable recommendations.

**Covers DR Sections:** S5 (Security — Authentication, Secrets, Data Protection, Input Validation, Supply Chain)

---

## Quick Start

```bash
# Full scan (all phases)
"Read instruments/security-tomographe/README.md and execute a full security scan."

# Targeted scan
"Read instruments/security-tomographe/README.md and execute Phase 3 (Attack Surface) only."

# Delta scan
"Read instruments/security-tomographe/README.md and execute a delta scan vs the last run."
```

---

## Scan Phases

| Phase | Name | What It Does | Key Tools |
|-------|------|-------------|-----------|
| **1** | Supply Chain | Scan all dependencies for known CVEs | `cargo audit`, `pip audit`, `npm audit`, `trivy` |
| **2** | Secrets | Detect leaked credentials in code, config, and git history | `gitleaks`, `grep` patterns, `.env` audit |
| **3** | Attack Surface | Map all network endpoints, auth mechanisms, and input vectors | Endpoint enumeration, auth model review |
| **4** | Encryption | Verify data-at-rest and data-in-transit encryption | Cipher verification, TLS config, E2E checks |
| **5** | Container Hardening | Audit Docker configuration for security best practices | Dockerfile review, compose security settings |
| **6** | AI Threat Model | Evaluate prompt injection defenses, data exfiltration risks, access control bypass surface | Pattern testing, defense layer audit |
| **7** | Access Control | Verify permission tiers, token lifecycle, device management | Config review, boundary analysis |
| **8** | Report | Compile findings into structured security report | Template filling, delta computation |

---

## Phase 1 — Supply Chain

**Goal:** Identify known vulnerabilities in all project dependencies.

### LLM steps

1. Discover which package managers are present in the project by reading manifest files: `Cargo.toml`, `package.json`, `pyproject.toml`, `go.mod`, `pom.xml`, `build.gradle`, `Gemfile`, `composer.json`, and any others present at the project root or in subdirectories.
2. For each ecosystem found, note what advisory database applies: RustSec for Rust, npm advisories for Node, PyPA advisory DB for Python, OSV for Go/Java, and so on.
3. Read the relevant lockfiles (`Cargo.lock`, `package-lock.json`, `yarn.lock`, `poetry.lock`, `go.sum`, etc.) and identify any dependency versions flagged as vulnerable in publicly known advisories — if you have knowledge of the dependency and version, reason about known CVEs.
4. Note any Docker images referenced in `docker-compose.yml` or Dockerfiles — check whether they are pinned by digest (`sha256:...`) or only by tag.

> **Note:** For full dependency lifecycle analysis (unused deps, licence risk, health), see the dependency-tomographe. This phase focuses on known CVEs only.

### Accelerator tools (optional)

```bash
# Rust
cargo audit 2>&1 | tee output/YYYY-MM-DD_{project_name}/scratch/security/cargo-audit-raw.txt
cargo audit --json 2>/dev/null | jq '.vulnerabilities.count, .warnings | length'

# Python
pip audit --format=json 2>/dev/null > output/YYYY-MM-DD_{project_name}/scratch/security/pip-audit-raw.json
# Fallback if pip-audit not installed:
pip list --outdated --format=json 2>/dev/null

# Node.js
cd apps/desktop && npm audit --json 2>/dev/null > ../../output/YYYY-MM-DD_{project_name}/scratch/security/npm-audit-raw.json
cd ../..

# Docker images (trivy)
grep 'image:' docker-compose.yml | awk '{print $2}' | while read img; do
  echo "--- Scanning $img ---"
  trivy image --format json "$img" 2>/dev/null
done > output/YYYY-MM-DD_{project_name}/scratch/security/trivy-raw.json

# If trivy unavailable, check image pinning:
grep 'image:' docker-compose.yml | grep -v 'sha256' | head -20
# Images without digest pinning = finding
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Critical CVE in direct dependency | **Critical** |
| High CVE in direct dependency | **Major** |
| Medium CVE in direct dependency | **Minor** |
| Low CVE / CVE in transitive dep only | **Observation** |
| Unmaintained crate/package with no CVE | **Observation** |
| Docker image pinned to tag not digest | **Minor** (SEC-03) |

### Output: `output/YYYY-MM-DD_{project_name}/scratch/security/phase1-supply-chain.json`

```json
{
  "timestamp": "ISO-8601",
  "rust": { "advisories": 0, "warnings": 0, "unmaintained": 0, "details": [] },
  "python": { "vulnerabilities": 0, "details": [] },
  "node": { "advisories": 0, "details": [] },
  "docker": { "images_scanned": 0, "critical": 0, "high": 0, "medium": 0, "low": 0, "unpinned_images": [] }
}
```

---

## Phase 2 — Secrets

**Goal:** Detect credentials, keys, tokens, and other secrets in the codebase and git history.

### Steps

```bash
# Gitleaks scan (if available)
gitleaks detect --source . --report-format json \
  --report-path output/YYYY-MM-DD_{project_name}/scratch/security/gitleaks-raw.json 2>/dev/null

# Fallback: pattern-based scanning
# API keys, tokens, passwords in source code
grep -rn --include='*.rs' --include='*.py' --include='*.ts' --include='*.kt' \
  -E '(password|secret|token|api_key|apikey|private_key)\s*=\s*["\x27][^"\x27]{8,}' \
  src/ apps/ config/ 2>/dev/null

# Hardcoded URLs with credentials
grep -rn --include='*.rs' --include='*.py' --include='*.yaml' --include='*.toml' \
  -E 'https?://[^:]+:[^@]+@' . 2>/dev/null

# .env files tracked in git
git ls-files | grep -E '\.env$|\.env\.' | grep -v '.env.example'

# Check .env.example for real-looking values (not placeholders)
grep -E '=.{16,}' .env.example 2>/dev/null | grep -v -E '(changeme|placeholder|xxx|your_|REPLACE)'

# Check git history for accidentally committed secrets
git log --all --diff-filter=D --name-only -- '*.env' '*.pem' '*.key' '*.p12' 2>/dev/null

# Verify .gitignore covers sensitive files
for pattern in '.env' '*.pem' '*.key' '*.p12' 'data/' '*.db'; do
  grep -q "$pattern" .gitignore && echo "OK: $pattern" || echo "MISSING: $pattern"
done
```

### Severity Rules

| Finding | Severity |
|---------|----------|
| Active credential in source code | **Critical** |
| Credential in git history (deleted but recoverable) | **Major** |
| .env file tracked in git | **Major** |
| .env.example with real-looking values | **Minor** |
| Missing .gitignore pattern for sensitive file type | **Minor** |
| No gitleaks/secrets scanning in CI | **Minor** (GAP-S8) |

---

## Phase 3 — Attack Surface

**Goal:** Map all network-accessible endpoints, authentication mechanisms, and input vectors.

### LLM steps

1. Read all source files handling inbound network traffic — look for route registrations, handler function patterns, WebSocket upgrade handlers, and RPC service definitions. The patterns vary by framework (e.g. `Router::new` / `.route` in Axum, `@app.route` in Flask, `app.get` in Express, `@Controller` in Spring) but the intent is universal: find every point where the application accepts external input.
2. For each endpoint found, verify that authentication is required — look for auth middleware, token validation, or guard patterns attached to the handler. Flag any endpoint that is unauthenticated and not an intentional public route (e.g. health check).
3. Read `docker-compose.yml` and any Dockerfiles: list all exposed ports. Verify that internal-only services (databases, message brokers, internal APIs) are not exposed to the host network.
4. Look for rate limiting or throttling middleware attached to public endpoints — the implementation varies by framework but the intent is to prevent abuse.
5. Check for hardcoded bind addresses: `0.0.0.0` bindings should be intentional and documented; flag any that are not.

### Accelerator tools (optional)

```bash
# List all network ports in docker-compose.yml
grep -E 'ports:|expose:' -A2 docker-compose.yml

# Find route registrations — Rust (Axum/Actix)
grep -rn 'Router::new\|\.route\|\.nest' src/api/ --include='*.rs'

# Find route registrations — Python (Flask/FastAPI)
grep -rn '@app\.route\|@router\.\|add_api_route' src/ --include='*.py'

# Find route registrations — Node.js/TypeScript (Express)
grep -rn 'app\.get\|app\.post\|router\.get\|router\.post' src/ apps/ --include='*.ts' --include='*.js'

# Find all WebSocket handlers
grep -rn 'WebSocket\|ws::\|upgrade\|on_upgrade' src/ --include='*.rs'
grep -rn 'WebSocket\|ws\.on\|socket\.on' src/ apps/ --include='*.ts' --include='*.py'

# Find all external HTTP calls (outbound attack surface)
grep -rn 'reqwest\|hyper::Client\|HttpClient' src/ --include='*.rs'
grep -rn 'requests\.\|httpx\.\|urllib' src/ --include='*.py'

# Check bind addresses
grep -rn '0\.0\.0\.0\|INADDR_ANY\|[::]' src/ config/ --include='*.rs' --include='*.py' --include='*.yaml'

# Auth patterns
grep -rn 'bearer\|jwt\|token\|auth' src/api/ --include='*.rs' --include='*.py' | head -30

# Rate limiting
grep -rn 'rate_limit\|throttle\|RateLimit\|slowapi\|governor' src/ --include='*.rs' --include='*.py'
```

### Checklist

- [ ] All endpoints require authentication (except health check)
- [ ] Health check endpoint doesn't leak sensitive info
- [ ] WebSocket connections require JWT
- [ ] No endpoint binds to 0.0.0.0 unless explicitly intended
- [ ] Rate limiting exists on API and admin endpoints
- [ ] CORS configuration restricts origins
- [ ] CSP headers set on web-facing interfaces

---

## Phase 4 — Encryption

**Goal:** Verify all encryption implementations are correct and active.

### LLM steps

1. Read source files and identify where sensitive data is stored — look for database write operations, file writes, and cache sets that involve user data, credentials, or private content.
2. For each storage location, determine whether encryption is applied. The implementation varies: SQLCipher for SQLite, encrypted fields in ORMs, file-level encryption, encrypted volumes, etc. Flag any sensitive data stored in plaintext.
3. Read network communication code and verify TLS is used for all external connections — look for `https://`, `wss://`, and TLS configuration in server setup code. Flag any plaintext (`http://`, `ws://`) connections to external services.
4. Identify key storage: verify that cryptographic keys are stored in hardware-backed keystores or OS keychains where available (Android Keystore, iOS Secure Enclave, OS secret-service on Linux/macOS), not in plaintext config files or environment variables.
5. Identify any use of deprecated or weak algorithms: MD5 or SHA1 used for security purposes, DES, 3DES, RC4, RSA with key sizes below 2048 bits, or AES in ECB mode.

### Accelerator tools (optional)

```bash
# Data at rest — Rust
grep -rn 'sqlcipher\|cipher\|PRAGMA key\|PRAGMA cipher' src/ config/ --include='*.rs' --include='*.yaml'

# Data at rest — Python
grep -rn 'sqlcipher\|cryptography\|Fernet\|encrypt' src/ --include='*.py'

# Data in transit — Rust
grep -rn 'tls\|rustls\|native_tls\|wss://' src/ --include='*.rs'

# Data in transit — TypeScript/Node
grep -rn 'https\|wss://\|tls\.' src/ apps/ --include='*.ts' --include='*.js'

# Data in transit — Kotlin/Android
grep -rn 'HttpsURLConnection\|OkHttp\|SSLContext' apps/android/ --include='*.kt'

# Key storage — Android Keystore
grep -rn 'KeyStore\|keystore\|AndroidKeyStore' apps/android/ --include='*.kt'

# Key storage — Desktop (OS keyring)
grep -rn 'keyring\|secret.service\|SecretService' apps/desktop/src-tauri/ --include='*.rs'

# Weak algorithm patterns
grep -rn 'MD5\|SHA1\|DES\|RC4\|ECB\|md5\|sha1' src/ apps/ \
  --include='*.rs' --include='*.py' --include='*.ts' --include='*.kt'
```

### Checklist

- [ ] Sensitive databases use encryption (not plaintext SQLite)
- [ ] Non-sensitive databases are plaintext (appropriate — no over-encryption)
- [ ] WebSocket connections use WSS (TLS)
- [ ] E2E encryption is mandatory (no fallback to unencrypted)
- [ ] Keys stored in hardware-backed keystore (Android) / OS keyring (Desktop)
- [ ] Key exchange uses a secure protocol
- [ ] Fingerprint verification is enforced (not bypassable)

---

## Phase 5 — Container Hardening

**Goal:** Audit Docker configuration for security best practices.

### Steps

```bash
# Read-only filesystem
grep -A5 'services:' docker-compose.yml | grep 'read_only'

# No privileged containers
grep 'privileged' docker-compose.yml

# Resource limits
grep -A10 'deploy:' docker-compose.yml | grep -E 'memory|cpus'

# Docker socket exposure
grep 'docker.sock' docker-compose.yml

# Non-root users
grep 'user:' docker-compose.yml
grep -rn 'USER' */Dockerfile 2>/dev/null

# Network isolation
grep 'networks:' docker-compose.yml | head -20

# Health checks defined
grep -c 'healthcheck:' docker-compose.yml

# Secrets in environment
grep -A20 'environment:' docker-compose.yml | grep -i 'password\|secret\|key\|token'
```

### Checklist

- [ ] Service containers with no write needs are read-only (`read_only: true`)
- [ ] No container runs as privileged
- [ ] Docker socket not mounted in production profiles
- [ ] Resource limits set (memory, CPU)
- [ ] Non-root user in Dockerfiles
- [ ] Health checks defined for all services
- [ ] Secrets passed via Docker secrets or env vars (not baked into images)
- [ ] Internal services use internal Docker network (not exposed to host)

---

## Phase 6 — AI Threat Model

> **Prerequisite:** This phase runs only when `profile.toggles.ai_ml_components` is `true`.
> When false, log `Observation: "No AI/ML components configured — AI threat model skipped"`
> and skip to Phase 7.

**Goal:** Evaluate defenses against AI-specific attack vectors.

### LLM steps

1. Read all code paths that accept user input and pass it to an LLM — look for prompt construction, message history assembly, and RAG query building. These patterns appear regardless of language or LLM provider.
2. For each input path, verify there is sanitization or validation before the content reaches the LLM — look for functions that strip or escape injected instructions, content filtering, or input length limits.
3. Look for output validation: code that checks LLM responses before acting on them — especially for structured outputs like tool calls, function calls, or JSON that drives application behaviour.
4. Check that different users' data cannot reach the same RAG or vector store scope — look for scope, collection, or namespace filtering applied to vector queries before results are returned.
5. These checks apply regardless of the LLM provider (OpenAI, Anthropic, local models, etc.) or the language the application is written in.

### Accelerator tools (optional)

```bash
# Input sanitization — Rust
grep -rn 'sanitiz\|clean_input\|strip_injection\|input_validator' src/ --include='*.rs'

# Input sanitization — Python
grep -rn 'sanitiz\|clean_input\|strip_injection\|input_validator' src/ --include='*.py'

# Output validation — Rust
grep -rn 'output_validat\|validate_response\|check_output' src/ --include='*.rs'

# Output validation — Python
grep -rn 'output_validat\|validate_response\|check_output' src/ --include='*.py'

# Content isolation between RAG scopes
grep -rn 'scope\|domain_filter\|collection_name\|namespace' src/ \
  --include='*.rs' --include='*.py' --include='*.ts' | head -20

# System prompt exposure risk
grep -rn 'system_prompt\|personality\|system_message' src/ \
  --include='*.rs' --include='*.py' --include='*.ts' | head -10

# Tool call validation
grep -rn 'validate_tool\|tool_auth\|per_agent\|function_call' src/ \
  --include='*.rs' --include='*.py' --include='*.ts'
```

### Defense Layers Audit

| Layer | Description | Status Check |
|-------|-------------|-------------|
| **L1** | Permission system gates all actions | Verify all actions have tier declarations |
| **L2** | Content isolation (RAG scopes don't cross domains) | Verify vector DB collection scoping |
| **L3** | Input sanitization on all external content | Verify sanitizer is wired into request pipeline |
| **L4** | Output validation (detect injected tool calls) | Verify output validator exists and is active |

### Severity Rules

| Finding | Severity |
|---------|----------|
| Action not declared in permission system (bypasses tier check) | **Critical** |
| Input sanitizer not wired into request pipeline | **Major** |
| RAG scope leakage (cross-domain query returns wrong scope) | **Major** |
| Output validation not implemented (Layer 4 absent) | **Major** (SEC-07) |
| System prompt leakable via crafted query | **Minor** |
| No adversarial test dataset | **Minor** (TEST-08) |

---

## Phase 7 — Access Control

> **Prerequisite:** This phase runs only when `profile.toggles.permission_system` is `true`.
> When false, log `Observation: "No permission system configured — AC checks skipped"`
> and skip to Phase 8.

**Goal:** Verify the permission/access control configuration, token lifecycle, and device management.

### Steps

```bash
# Access control config completeness
# Count declared domains and actions
yq '.domains | length' config/access-control.yaml 2>/dev/null
yq '.domains[].actions | length' config/access-control.yaml 2>/dev/null | paste -sd+ | bc

# Check for hard-locks on financial/destructive actions
yq '.domains[].actions[] | select(.tier == "T0")' config/access-control.yaml 2>/dev/null

# Token lifecycle
grep -rn 'expir\|rotation\|refresh\|renew' src/api/jwt.rs 2>/dev/null
grep -rn 'token_expiry\|session_timeout\|auto_revoc' config/ --include='*.yaml'

# Device management
grep -rn 'revoke\|unpair\|device_list\|max_devices' src/ --include='*.rs'

# Biometric gate for high-tier approvals (Android)
grep -rn 'biometric\|BiometricPrompt\|fingerprint' apps/android/ --include='*.kt'
```

### Checklist

- [ ] Every service action declared in permission/access control configuration
- [ ] Financial actions are hard-locked (unconditionally blocked)
- [ ] Communication actions are hard-locked (unconditionally blocked)
- [ ] Destructive actions (delete, format) are hard-locked or require explicit approval
- [ ] Bearer token has expiry (not permanent)
- [ ] Device auto-revocation after inactivity period
- [ ] Biometric required for high-tier approval on mobile
- [ ] Fail-closed: access control service unreachable -> all actions blocked

---

## Phase 8 — Report

Compile all phase outputs into `output/YYYY-MM-DD_{project_name}/SS{n}-security-tomographe.md` (see `qualitoscope/config.yaml` for `project_name`) using the report template.

Apply severity ratings per finding, compute overall verdict, generate action register.

---

## Output Directory Structure

```
security-tomographe/
├── README.md
├── config.yaml
├── methods/
│   ├── 01-supply-chain.md
│   ├── 02-secrets.md
│   ├── 03-attack-surface.md
│   ├── 04-encryption.md
│   ├── 05-container-hardening.md
│   ├── 06-ai-threat-model.md
│   ├── 07-access-control.md
│   └── 08-report.md
├── checklists/
│   ├── security-posture.md           # Master security checklist
│   ├── owasp-llm-top10.md            # AI-specific security checklist
│   └── container-hardening.md        # Docker security checklist
├── templates/
│   └── report-template.md
# output is now centralised — see output/YYYY-MM-DD_{project_name}/
└── fixes/
    └── README.md
```

---

## Configuration (config.yaml)

This instrument reads project-specific paths from `project-profile.yaml` in the target project root. If a profile field is absent, the default from the profile schema applies. Instrument-specific thresholds remain in this instrument's `config.yaml`.

```yaml
thresholds:
  max_critical_cves: 0          # Zero tolerance
  max_high_cves: 0              # Zero tolerance for direct deps
  max_medium_cves: 5            # Some acceptable in transitive deps
  max_secrets_in_code: 0        # Zero tolerance
  max_secrets_in_history: 0     # Zero tolerance (require git history rewrite)
  action_coverage: 100          # Every action must be declared
  defense_layers_active: 4      # All 4 prompt injection defense layers
  container_hardening_score: 80 # % of hardening checklist passed

scope:
  source_dirs: []               # adjust to project layout
  compose_file: docker-compose.yml
  access_control_config: config/access-control.yaml
  env_files: [.env, .env.example]
  ci_config: .gitlab-ci.yml

delta:
  # output goes to output/YYYY-MM-DD_{project_name}/ — set project_name in qualitoscope/config.yaml
  output_root: output/
  keep_runs: 10
```

---

## Severity & Verdict

Same severity scale as other instruments (OK / Observation / Minor / Major / Critical).

| Verdict | Rule |
|---------|------|
| **PASS** | 0 Critical, 0 Major |
| **CONDITIONAL** | 0 Critical, <=2 Major with tracking issues |
| **FAIL** | >=1 Critical, OR untracked Major |

---

## Run History

| Run | Date | Trigger | Findings | Report |
|-----|------|---------|----------|--------|
| SS1 | _pending_ | Initial baseline | — | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
