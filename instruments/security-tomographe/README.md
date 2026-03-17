# .security-tomographe/

**Security posture scanner for the target project.** Scans dependencies, secrets, attack surface, encryption, container hardening, and AI-specific threats (prompt injection, data exfiltration). Produces a severity-rated report with drift tracking and auto-fixable recommendations.

**Covers DR Sections:** S5 (Security — Authentication, Secrets, Data Protection, Input Validation, Supply Chain)

---

## Quick Start

```bash
# Full scan (all phases)
"Read .security-tomographe/README.md and execute a full security scan."

# Targeted scan
"Read .security-tomographe/README.md and execute Phase 3 (Attack Surface) only."

# Delta scan
"Read .security-tomographe/README.md and execute a delta scan vs the last run."
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

### Steps

```bash
# Rust dependencies
cargo audit 2>&1 | tee .security-tomographe/output/cargo-audit-raw.txt
# Count: advisories, warnings, unmaintained crates
cargo audit --json 2>/dev/null | jq '.vulnerabilities.count, .warnings | length'

# Python dependencies
pip audit --format=json 2>/dev/null > .security-tomographe/output/pip-audit-raw.json
# Fallback if pip-audit not installed:
pip list --outdated --format=json 2>/dev/null

# Node.js / React frontend
cd apps/desktop && npm audit --json 2>/dev/null > ../../.security-tomographe/output/npm-audit-raw.json
cd ../..

# Docker images
# For each image in docker-compose.yml:
grep 'image:' docker-compose.yml | awk '{print $2}' | while read img; do
  echo "--- Scanning $img ---"
  trivy image --format json "$img" 2>/dev/null
done > .security-tomographe/output/trivy-raw.json

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

### Output: `output/phase1-supply-chain.json`

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
  --report-path .security-tomographe/output/gitleaks-raw.json 2>/dev/null

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

### Steps

```bash
# List all network ports in docker-compose.yml
grep -E 'ports:|expose:' -A2 docker-compose.yml

# Find all route registrations (service endpoints)
grep -rn 'Router::new\|\.route\|\.nest' src/api/ --include='*.rs'

# Find all WebSocket handlers
grep -rn 'WebSocket\|ws::\|upgrade' src/ --include='*.rs'

# Find all external HTTP calls (outbound attack surface)
grep -rn 'reqwest\|hyper::Client\|HttpClient' src/ --include='*.rs'
grep -rn 'requests\.\|httpx\.\|urllib' src/ --include='*.py'

# Check localhost binding (should not bind 0.0.0.0 unless intended)
grep -rn '0\.0\.0\.0\|INADDR_ANY\|[::]' src/ config/ --include='*.rs' --include='*.yaml'

# Auth model audit
grep -rn 'bearer\|jwt\|token\|auth' src/api/ --include='*.rs' | head -30

# Rate limiting check
grep -rn 'rate_limit\|throttle\|RateLimit\|slowapi' src/ --include='*.rs' --include='*.py'
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

### Steps

```bash
# Data at rest: encrypted storage
# Check which databases use encryption (based on data sensitivity tiers)
grep -rn 'sqlcipher\|cipher\|PRAGMA key\|PRAGMA cipher' src/ config/ --include='*.rs' --include='*.yaml'

# Check databases are NOT plaintext for sensitive data
# (requires examining config to see which DBs hold what sensitivity tier)

# Data in transit: TLS
grep -rn 'tls\|rustls\|native_tls\|wss://' src/ apps/ --include='*.rs' --include='*.ts' --include='*.kt'

# E2E encryption
grep -rn 'x25519\|aes_gcm\|chacha20\|XChaCha\|encrypt\|decrypt' src/ apps/ --include='*.rs' --include='*.kt' --include='*.ts'

# Key storage
# Android: should use Android Keystore
grep -rn 'KeyStore\|keystore\|AndroidKeyStore' apps/android/ --include='*.kt'
# Desktop: should use OS keyring (secret-service D-Bus)
grep -rn 'keyring\|secret.service\|SecretService' apps/desktop/src-tauri/ --include='*.rs'

# Key exchange
grep -rn 'fingerprint\|X3DH\|key_exchange' src/ apps/ --include='*.rs' --include='*.kt'
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

**Goal:** Evaluate defenses against AI-specific attack vectors.

### Steps

```bash
# Input sanitization
grep -rn 'sanitiz\|clean_input\|strip_injection\|input_validator' src/ --include='*.rs' --include='*.py'

# Output validation (Layer 4 defense)
grep -rn 'output_validat\|validate_response\|check_output' src/ --include='*.rs'

# Content isolation between RAG scopes
grep -rn 'scope\|domain_filter\|collection_name' src/ --include='*.rs' | head -20

# System prompt exposure risk
grep -rn 'system_prompt\|personality' src/ --include='*.rs' | head -10

# Tool call validation (access control checks tool calls, not just actions)
grep -rn 'validate_tool\|tool_auth\|per_agent' src/ --include='*.rs'
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

**Goal:** Verify the permission/access control configuration, token lifecycle, and device management.

### Steps

```bash
# Access control config completeness
# Count declared domains and actions
yq '.domains | length' config/services/access-control-config.yaml 2>/dev/null
yq '.domains[].actions | length' config/services/access-control-config.yaml 2>/dev/null | paste -sd+ | bc

# Check for hard-locks on financial/destructive actions
yq '.domains[].actions[] | select(.tier == "T0")' config/services/access-control-config.yaml 2>/dev/null

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

Compile all phase outputs into `output/YYYY-MM-DD/SS{n}-security-tomographe.md` using the report template.

Apply severity ratings per finding, compute overall verdict, generate action register.

---

## Output Directory Structure

```
.security-tomographe/
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
├── output/
│   └── .gitignore
└── fixes/
    └── README.md
```

---

## Configuration (config.yaml)

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
  rust_dirs: [src/]
  python_dirs: [src/]
  node_dirs: [apps/desktop/]
  android_dirs: [apps/android/]
  compose_file: docker-compose.yml
  access_control_config: config/services/access-control-config.yaml
  env_files: [.env, .env.example]
  ci_config: .gitlab-ci.yml

delta:
  output_dir: output/
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
