# compliance-tomographe

**Compliance and legal scanner for the target project.** Audits license compatibility, configuration management, access control completeness, GDPR readiness, and AI Act preparedness. Covers the broadest DR scope alongside the Documentation Tomographe, unifying three DR sections plus the critical access control coverage appendix.

**Covers DR Sections:** S6 (Configuration & Environment Management), S12 (Licensing & Legal), AC1 (Access Control Coverage)

---

## Quick Start

```bash
"Read instruments/compliance-tomographe/README.md and execute a full compliance scan."
"Read instruments/compliance-tomographe/README.md and execute Phase 3 (Access Control Coverage) only."
"Read instruments/compliance-tomographe/README.md and execute Phase 5 (AI Act Readiness) for production planning."
```

---

## Scan Phases

| Phase | Name | What It Does | Tools |
|-------|------|-------------|-------|
| **1** | License Audit | Check all dependency licenses for compatibility | `cargo license`, npm analysis |
| **2** | Configuration Management | Verify config externalization, .env handling, validation | Config file review |
| **3** | Access Control Coverage (AC1) | Full AC1 checklist — tier declarations, boundary tests, manifests | permission/access control configuration, boundary tests |
| **4** | GDPR Readiness | Data classification tiers, data subject rights, retention, DPIA readiness | Design doc + code review |
| **5** | AI Act Readiness | Risk classification, documentation, transparency, logging | Business case docs |
| **6** | Export Control | Cryptographic export classification for EU | Crypto usage audit |
| **7** | Report | Compile findings | Template filling |

---

## Phase 1 — License Audit (S12)

**Goal:** Verify all dependency licenses are compatible with the project.

```bash
# Rust dependency licenses
cargo license 2>/dev/null | tee output/YYYY-MM-DD/CL1-compliance-cargo-licenses.txt
# Count by license type
cargo license 2>/dev/null | awk '{print $NF}' | sort | uniq -c | sort -rn

# Check for copyleft contamination (GPL, AGPL, LGPL — may have restrictions)
cargo license 2>/dev/null | grep -i 'GPL\|AGPL\|LGPL\|copyleft'

# Node dependency licenses
cd apps/desktop && npx license-checker --summary 2>/dev/null && cd ../..

# Android dependencies (Kotlin/Gradle)
grep 'implementation\|api(' apps/android/app/build.gradle* 2>/dev/null | head -20
# Would need manual license verification for Kotlin deps

# Attribution file existence
[ -f NOTICE ] || [ -f NOTICE.md ] || [ -f ATTRIBUTION.md ] && \
  echo "OK: Attribution file exists" || echo "MISSING: No NOTICE/ATTRIBUTION file"

# Vendored dependency licenses
ls vendor/rust/*/LICENSE* 2>/dev/null | wc -l
```

### License Checklist (S12)

- [ ] All Rust dependencies have permissive licenses (MIT, Apache-2.0, BSD)
- [ ] No GPL contamination in binary-linked dependencies
- [ ] Node dependencies have permissive licenses
- [ ] NOTICE/ATTRIBUTION file exists listing all third-party licenses
- [ ] Vendored dependencies include their LICENSE files
- [ ] License field set in Cargo.toml for the project itself

### Severity Rules

| Finding | Severity |
|---------|----------|
| GPL dependency linked into binary | **Major** |
| LGPL dependency (may need dynamic linking) | **Minor** |
| Missing attribution file | **Minor** |
| Unknown license on dependency | **Minor** |
| All permissive, everything clean | **OK** |

---

## Phase 2 — Configuration Management (S6)

**Goal:** Verify configuration is externalized, validated, and properly managed.

```bash
# Config externalization (code should not contain hardcoded config values)
grep -rn 'localhost\|127\.0\.0\.1\|:8080\|:3000' src/ --include='*.rs' | \
  grep -v 'test\|#\[test\]\|///\|//' | head -10
# Hardcoded addresses outside tests = finding

# Config file structure
find config/ -type f 2>/dev/null | sort

# Environment-specific configs
ls docker-compose*.yml 2>/dev/null
# Should have: base + CI overlay minimum

# .env handling
[ -f .env.example ] && echo "OK: .env.example exists" || echo "MISSING: .env.example"
git ls-files | grep -q '\.env$' && echo "BAD: .env tracked in git" || echo "OK: .env not in git"

# Config validation at startup
grep -rn 'validate.*config\|config.*valid\|parse.*config\|Config::load' src/ --include='*.rs' | head -10
# Should fail fast on invalid config

# Sensitive config values
grep -rn 'password\|secret\|token\|key' config/ --include='*.yaml' --include='*.toml' 2>/dev/null | \
  grep -v '#\|example\|placeholder' | head -10
```

### Configuration Checklist (S6)

- [ ] Configuration externalized from code (YAML/TOML/env vars)
- [ ] Environment-specific configs separated (dev/CI/prod)
- [ ] `.env` files gitignored
- [ ] `.env.example` provided with placeholder values
- [ ] Config validated at startup (fail-fast on bad config)
- [ ] Default values documented and sensible
- [ ] No sensitive values in committed config files

---

## Phase 3 — Access Control Coverage (AC1)

**Goal:** Full AC1 checklist execution — verifies the project's permission system covers all component actions.

```bash
# AC1-1: Every component action has a tier declaration
TOTAL_ACTIONS=$(yq '.domains[].actions | length' config/services/access-control.yaml 2>/dev/null | paste -sd+ | bc 2>/dev/null)
echo "Total access control actions: ${TOTAL_ACTIONS:-unknown}"

# List all domains
yq '.domains[].name' config/services/access-control.yaml 2>/dev/null | sort

# AC1-2: Frozen-shape boundary tests match current config
DOMAIN_COUNT=$(yq '.domains | length' config/services/access-control.yaml 2>/dev/null)
echo "Domains in config: $DOMAIN_COUNT"

# Check boundary tests exist and are up to date
find <service>/tests/ -name 'boundary*' 2>/dev/null
grep -rn 'domain_count\|action_count' <service>/tests/ --include='*.rs' 2>/dev/null | head -5

# AC1-3: Blocked-tier actions (unconditional block)
echo "=== Blocked Actions (hard blocked) ==="
yq '.domains[].actions[] | select(.tier == "blocked" or .tier == 0)' config/services/access-control.yaml 2>/dev/null | head -20
# Should include: financial transactions, sending communications, destructive operations

# AC1-4: Approval-required actions have approval flows in clients
echo "=== Approval-Required Actions ==="
yq '.domains[].actions[] | select(.tier == "approval" or .tier == 1)' config/services/access-control.yaml 2>/dev/null | head -20
# Verify corresponding approval UI exists in client apps

# AC1-5: Component-permission manifest
[ -f config/services/component-permission-manifest.yaml ] && \
  echo "OK: Manifest exists" || echo "MISSING: component-permission-manifest.yaml"
MANIFEST_ENTRIES=$(yq '. | length' config/services/component-permission-manifest.yaml 2>/dev/null)
echo "Manifest entries: ${MANIFEST_ENTRIES:-unknown}"

# AC1-6: Orphan actions (in code but not in access control config)
grep -rn 'AccessAction\|access.*action\|validate_action' src/ --include='*.rs' | \
  grep -oP '"[a-z_]+"' | sort -u > /tmp/code_actions.txt
echo "Actions referenced in code: $(wc -l < /tmp/code_actions.txt)"

# AC1-7: Fail-closed behavior
grep -rn 'fail_closed\|unreachable\|access.*unavailable\|default.*block\|None.*=>' src/ --include='*.rs' | head -10
```

### AC1 Checklist

- [ ] AC1-1: Every component action has a tier declaration in the access control configuration
- [ ] AC1-2: Frozen-shape boundary tests match current domain/action counts
- [ ] AC1-3: Blocked-tier actions cover financial, communication, and destructive operations
- [ ] AC1-4: Approval-required actions have approval flows in all client applications
- [ ] AC1-5: Component-permission manifest maps every registered component to its domain
- [ ] AC1-6: No orphan actions (actions in code but not in access control config)
- [ ] AC1-7: Fail-closed verified (access control service unreachable → all actions blocked)

### Severity Rules

| Finding | Severity |
|---------|----------|
| Component action not declared in access control config (orphan) | **Critical** |
| Fail-closed not verified | **Critical** |
| Blocked tier missing for financial/communication/destructive | **Major** |
| Boundary tests stale (counts don't match) | **Major** |
| Manifest entries missing for registered component | **Minor** |
| Approval flow missing on one platform | **Minor** |

---

## Phase 4 — GDPR Readiness

**Goal:** Assess GDPR compliance posture for personal data processing.

```bash
# Data classification tier implementation (from schema documentation)
grep -rn 'privacy\|data_class\|classification' src/ config/ --include='*.rs' --include='*.yaml' | head -20

# Data subject rights implementation
echo "=== Right to Access ==="
grep -rn 'export\|data_export\|download.*data' src/ --include='*.rs' | head -5
echo "=== Right to Erasure ==="
grep -rn 'delete.*user\|erase\|purge\|gdpr.*delete' src/ --include='*.rs' | head -5
echo "=== Right to Portability ==="
grep -rn 'export.*json\|export.*csv\|portable' src/ --include='*.rs' | head -5

# Consent mechanism
grep -rn 'consent\|opt_in\|opt_out\|accept\|agree' src/ apps/ --include='*.rs' --include='*.kt' --include='*.tsx' | head -10

# Data processing records
grep -rn 'processing\|purpose\|legal_basis' src/ config/ --include='*.rs' --include='*.yaml' | head -5
```

### GDPR Checklist

- [ ] Data classification tiers (e.g., Public, Internal, Confidential, Restricted) implemented and enforced
- [ ] Data encrypted at rest for Confidential/Restricted tiers
- [ ] Data subject access mechanism exists
- [ ] Data deletion mechanism exists
- [ ] Data portability (export to JSON/standard format)
- [ ] Processing purposes documented
- [ ] Data retention policies defined

**Note:** Full GDPR compliance becomes critical when processing customer data. Personal or internal use has softer requirements but establishing the patterns early prevents rework.

---

## Phase 5 — AI Act Readiness

**Goal:** Assess preparedness for EU AI Act compliance.

```bash
# Risk classification documentation
find docs/ -name '*comply*' -o -name '*ai-act*' -o -name '*risk*' 2>/dev/null

# Existing compliance research
grep -rn 'AI Act\|Article\|risk.*class\|high.risk\|limited.risk' docs/ 2>/dev/null | head -10

# Transparency requirements
grep -rn 'transparency\|disclosure\|inform.*user\|ai.*system' src/ config/ --include='*.rs' --include='*.yaml' | head -5

# Logging for AI Act Article 12 compliance
grep -rn 'log.*decision\|log.*action\|trace.*llm\|audit.*inference' src/ --include='*.rs' | head -10

# Human oversight mechanism (access control tiers = human oversight for AI actions)
echo "Access control tier system serves as human oversight mechanism"
grep -rn 'human.*oversight\|approval\|confirm' src/ --include='*.rs' | head -5
```

### AI Act Readiness Assessment

| Requirement | Article | Status | Notes |
|---|---|---|---|
| Risk classification performed | Art. 6-7 | | Check compliance docs |
| Technical documentation | Art. 11 | | Architecture docs serve as basis |
| Record-keeping (logging) | Art. 12 | | Access control audit trail |
| Transparency | Art. 52 | | AI system disclosure |
| Human oversight | Art. 14 | | Access control tier system |
| Accuracy & robustness | Art. 15 | | Testing framework |
| Post-market monitoring | Art. 72 | | Observability system |

**Note:** This phase produces a readiness assessment, not a compliance certification. Full compliance work is production scope.

---

## Phase 6 — Export Control

**Goal:** Document cryptographic usage for EU export compliance.

```bash
# Cryptographic algorithms used
grep -rn 'aes\|AES\|chacha\|ChaCha\|x25519\|X25519\|ed25519\|sha256\|SHA\|hmac\|HMAC' \
  src/ apps/ --include='*.rs' --include='*.kt' --include='*.ts' 2>/dev/null | \
  grep -v 'test\|///\|//' | head -20

# Crypto library dependencies
grep -rn 'aes\|chacha20\|x25519\|ring\|rustls\|openssl\|bouncycastle\|webcrypto' \
  Cargo.toml apps/*/build.gradle* apps/*/package.json 2>/dev/null

# Key sizes
grep -rn '256\|128\|384\|512' src/ --include='*.rs' | grep -i 'key\|cipher\|bit' | head -10
```

### Export Control Documentation

| Algorithm | Key Size | Use Case | EU Classification |
|---|---|---|---|
| AES-256-GCM | 256-bit | Data at rest, E2E messages | Category 5A2 |
| X25519 | 255-bit | Key exchange (device pairing, E2E) | Category 5A2 |
| Ed25519 | 255-bit | Digital signatures | Category 5A2 |
| SHA-256 | 256-bit | Hashing, integrity checks | Generally exempt |

**Note:** EU Regulation (EU) 2021/821 governs dual-use items including cryptography. Software using encryption above certain thresholds may require export notification. Personal use is generally exempt; commercial export may require filing.

---

## Configuration

```yaml
thresholds:
  licensing:
    copyleft_deps: 0
    unknown_license_deps: 0
    attribution_file_required: true
  configuration:
    hardcoded_addresses_max: 0
    env_example_required: true
    config_validation_at_startup: true
  access_control:
    action_coverage: 100
    boundary_tests_current: true
    fail_closed_verified: true
    blocked_categories: [financial, communication, destructive]
  gdpr:
    classification_tiers_implemented: true
    confidential_restricted_encrypted: true
    data_export_exists: true
    data_delete_exists: true
  ai_act:
    risk_classification_documented: true
    logging_for_art12: true
    human_oversight_mechanism: true

scope:
  access_control_config: config/services/access-control.yaml
  component_manifest: config/services/component-permission-manifest.yaml
  boundary_tests: <service>/tests/
  compose_file: docker-compose.yml
  config_dir: config/
  business_docs: docs/
  crypto_sources: [src/, apps/]
```

---

## Output

Reports are written to `output/YYYY-MM-DD/CL<N>-compliance.md` (e.g., `output/2026-03-17/CL1-compliance.md`).

---

## Run History

| Run | Date | Trigger | Report |
|-----|------|---------|--------|
| CL1 | _pending_ | Initial baseline | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
