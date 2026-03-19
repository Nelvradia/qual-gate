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
| **1** | License Audit | Fast licence gate on direct dependencies; delegates transitive analysis to dependency-tomographe | Manifest reading, attribution file check |
| **2** | Configuration Management | Verify config externalization, .env handling, validation | Config file review |
| **3** | Access Control Coverage (AC1) | Full AC1 checklist — tier declarations, boundary tests, manifests | permission/access control configuration, boundary tests |
| **4** | GDPR Readiness | Data classification tiers, data subject rights, retention, DPIA readiness | Design doc + code review |
| **5** | AI Act Readiness | Risk classification, documentation, transparency, logging | Business case docs |
| **6** | Export Control | Cryptographic export classification for EU | Crypto usage audit |
| **7** | Report | Compile findings | Template filling |

---

## Phase 1 — License Audit (S12)

**Goal:** Perform a rapid licence compliance check on direct dependencies and verify the attribution file exists. For full transitive licence analysis, licence risk matrix, and royalty obligation assessment, run `dependency-tomographe` Phase 3.

### LLM steps

1. Read all manifest files in the project (Cargo.toml, package.json, pyproject.toml, go.mod, pom.xml, Gemfile, etc. — discover them by reading the project structure).
2. For each direct dependency, read its declared licence field in the manifest.
3. Flag any licence in the critical tier: AGPL-3.0, GPL-2.0, GPL-3.0, SSPL-1.0, BUSL-1.1, or any unknown/missing licence.
4. Verify that an attribution file exists (NOTICE, NOTICE.md, or ATTRIBUTION.md) if any permissive deps are present.
5. For a comprehensive analysis including transitive deps, licence propagation, and royalty triggers, run the dependency-tomographe.

### Accelerator tools (optional)

```bash
# Rust — cargo-license
cargo license 2>/dev/null | tee output/YYYY-MM-DD_{project_name}/scratch/compliance/cargo-licenses.txt
cargo license 2>/dev/null | awk '{print $NF}' | sort | uniq -c | sort -rn
cargo license 2>/dev/null | grep -i 'GPL\|AGPL\|LGPL\|copyleft'

# Node.js — license-checker
cd apps/desktop && npx license-checker --summary 2>/dev/null && cd ../..

# Python — pip-licenses
pip-licenses --order=license 2>/dev/null

# Attribution file existence (all ecosystems)
[ -f NOTICE ] || [ -f NOTICE.md ] || [ -f ATTRIBUTION.md ] && \
  echo "OK: Attribution file exists" || echo "MISSING: No NOTICE/ATTRIBUTION file"
```

### License Checklist (S12)

- [ ] All direct dependencies have permissive licenses (MIT, Apache-2.0, BSD, ISC, or equivalent)
- [ ] No GPL/AGPL/SSPL/BUSL contamination in binary-linked dependencies
- [ ] NOTICE/ATTRIBUTION file exists listing all third-party licenses
- [ ] Vendored dependencies include their LICENSE files
- [ ] Licence field set in the project's own manifest

### Severity Rules

| Finding | Severity |
|---------|----------|
| GPL/AGPL dependency linked into binary | **Major** |
| LGPL dependency (may need dynamic linking) | **Minor** |
| Missing attribution file | **Minor** |
| Unknown license on dependency | **Minor** |
| All permissive, everything clean | **OK** |

---

## Phase 2 — Configuration Management (S6)

**Goal:** Verify configuration is externalized, validated, and properly managed.

### LLM steps

1. Read all configuration files in the project (YAML, TOML, JSON, .env.example, docker-compose.yml, etc.).
2. Check for hardcoded addresses, ports, or credentials in source code files.
3. Verify .gitignore covers sensitive file patterns.
4. Check for a .env.example with placeholder (not real) values.

### Accelerator tools (optional)

```bash
# Hardcoded addresses in source — adjust extensions to match the project language
grep -rn 'localhost\|127\.0\.0\.1\|:8080\|:3000' src/ --include='*.rs' | \
  grep -v 'test\|#\[test\]\|///\|//' | head -10
# Hardcoded addresses outside tests = finding

# Config file structure
find config/ -type f 2>/dev/null | sort

# Environment-specific configs
ls docker-compose*.yml 2>/dev/null

# .env handling
[ -f .env.example ] && echo "OK: .env.example exists" || echo "MISSING: .env.example"
git ls-files | grep -q '\.env$' && echo "BAD: .env tracked in git" || echo "OK: .env not in git"

# Config validation at startup — adjust pattern to match the project language
grep -rn 'validate.*config\|config.*valid\|parse.*config\|Config::load' src/ --include='*.rs' | head -10

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

> **Prerequisite:** This phase runs only when `profile.toggles.permission_system` is `true`.
> When false, log `Observation: "No permission system configured — AC checks skipped"`
> and skip to Phase 4.

**Goal:** Full AC1 checklist execution — verifies the project's permission system covers all component actions.

### LLM steps

1. Read the access control configuration file specified in config (`scope.access_control_config`).
2. Count domains and actions.
3. Read boundary test files (`scope.boundary_tests`) and verify counts match the configuration.
4. The rest is checklist-driven — apply the AC1 checklist below.

### Accelerator tools (optional)

```bash
# AC1-1: Every component action has a tier declaration
ACCESS_CONTROL_CONFIG="${ACCESS_CONTROL_CONFIG:-config/access-control.yaml}"
TOTAL_ACTIONS=$(yq '.domains[].actions | length' "$ACCESS_CONTROL_CONFIG" 2>/dev/null | paste -sd+ | bc 2>/dev/null)
echo "Total access control actions: ${TOTAL_ACTIONS:-unknown}"

# List all domains
yq '.domains[].name' "$ACCESS_CONTROL_CONFIG" 2>/dev/null | sort

# AC1-2: Frozen-shape boundary tests match current config
DOMAIN_COUNT=$(yq '.domains | length' "$ACCESS_CONTROL_CONFIG" 2>/dev/null)
echo "Domains in config: $DOMAIN_COUNT"

# Check boundary tests exist and are up to date
find <service>/tests/ -name 'boundary*' 2>/dev/null
grep -rn 'domain_count\|action_count' <service>/tests/ --include='*.rs' 2>/dev/null | head -5

# AC1-3: Blocked-tier actions (unconditional block)
echo "=== Blocked Actions (hard blocked) ==="
yq '.domains[].actions[] | select(.tier == "blocked" or .tier == 0)' "$ACCESS_CONTROL_CONFIG" 2>/dev/null | head -20

# AC1-4: Approval-required actions have approval flows in clients
echo "=== Approval-Required Actions ==="
yq '.domains[].actions[] | select(.tier == "approval" or .tier == 1)' "$ACCESS_CONTROL_CONFIG" 2>/dev/null | head -20

# AC1-5: Component-permission manifest
[ -f config/component-permission-manifest.yaml ] && \
  echo "OK: Manifest exists" || echo "MISSING: component-permission-manifest.yaml"
MANIFEST_ENTRIES=$(yq '. | length' config/component-permission-manifest.yaml 2>/dev/null)
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

> **Prerequisite:** This phase runs only when `profile.toggles.gdpr_scope` is `true`.
> When false, log `Observation: "GDPR scope not configured — GDPR checks skipped"`
> and skip to Phase 5.

**Goal:** Assess GDPR compliance posture for personal data processing.

### LLM steps

1. Read source files to identify where personal data is stored, processed, or transmitted.
2. Check for data classification markers, privacy tiers, or data handling annotations in the codebase.
3. Look for data export, deletion, and access mechanisms.
4. Apply the GDPR checklist below.

### Accelerator tools (optional)

```bash
# Data classification tier implementation
grep -rn 'privacy\|data_class\|classification' src/ config/ --include='*.rs' --include='*.yaml' | head -20

# Data subject rights implementation
echo "=== Right to Access ==="
grep -rn 'export\|data_export\|download.*data' src/ --include='*.rs' | head -5
echo "=== Right to Erasure ==="
grep -rn 'delete.*user\|erase\|purge\|gdpr.*delete' src/ --include='*.rs' | head -5
echo "=== Right to Portability ==="
grep -rn 'export.*json\|export.*csv\|portable' src/ --include='*.rs' | head -5

# Python / TypeScript equivalents
grep -rn 'privacy\|data_class\|classification' src/ --include='*.py' --include='*.tsx' | head -20

# Consent mechanism
grep -rn 'consent\|opt_in\|opt_out\|accept\|agree' src/ apps/ --include='*.rs' --include='*.kt' --include='*.tsx' | head -10
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

> **Prerequisite:** This phase runs only when `profile.toggles.ai_act_scope` is `true`.
> When false, log `Observation: "AI Act scope not configured — AI Act checks skipped"`
> and skip to Phase 6.

**Goal:** Assess preparedness for EU AI Act compliance.

### LLM steps

1. Read business documentation and architecture docs specified in config (`scope.business_docs`).
2. Assess risk classification documentation.
3. Check for logging of AI decisions (required by Article 12).
4. Apply the AI Act readiness assessment table below.

### Accelerator tools (optional)

```bash
# Risk classification documentation
find docs/ -name '*comply*' -o -name '*ai-act*' -o -name '*risk*' 2>/dev/null

# Existing compliance research
grep -rn 'AI Act\|Article\|risk.*class\|high.risk\|limited.risk' docs/ 2>/dev/null | head -10

# Transparency requirements
grep -rn 'transparency\|disclosure\|inform.*user\|ai.*system' src/ config/ --include='*.rs' --include='*.yaml' | head -5

# Logging for AI Act Article 12 compliance
grep -rn 'log.*decision\|log.*action\|trace.*llm\|audit.*inference' src/ --include='*.rs' | head -10

# Human oversight mechanism
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

### LLM steps

1. Read all source files across the project (`scope.source_dirs`) and identify cryptographic algorithm usage — look for references to: AES, ChaCha20, RSA, ECDSA, Ed25519, X25519, SHA, HMAC, TLS, SSL.
2. Look for cryptographic library imports and dependencies in all manifest files — the library names vary by language but the algorithm names are standardised.
3. For each algorithm found: note its use case (encryption at rest, key exchange, signing, hashing) and key size where determinable.
4. Build the export control documentation table from findings.

### Accelerator tools (optional)

```bash
# Rust — algorithm references in source
grep -rn 'aes\|AES\|chacha\|ChaCha\|x25519\|X25519\|ed25519\|sha256\|SHA\|hmac\|HMAC' \
  src/ --include='*.rs' 2>/dev/null | grep -v 'test\|///\|//' | head -20

# Python — algorithm references in source
grep -rn 'AES\|ChaCha\|RSA\|ECDSA\|Ed25519\|SHA\|HMAC\|TLS\|SSL' \
  src/ --include='*.py' 2>/dev/null | grep -v 'test\|#' | head -20

# TypeScript/JavaScript — algorithm references in source
grep -rn 'AES\|ChaCha\|RSA\|ECDSA\|SHA\|HMAC\|createCipher\|subtle\.encrypt' \
  src/ apps/ --include='*.ts' --include='*.tsx' --include='*.js' 2>/dev/null | head -20

# Rust — crypto library dependencies in manifests
grep -rn 'aes\|chacha20\|x25519\|ring\|rustls\|openssl' Cargo.toml 2>/dev/null

# Node.js — crypto library dependencies
grep -rn 'node-forge\|crypto-js\|noble\|tweetnacl\|libsodium' apps/*/package.json 2>/dev/null

# Python — crypto library dependencies
grep -rn 'cryptography\|pycryptodome\|pyOpenSSL\|nacl\|paramiko' pyproject.toml requirements*.txt 2>/dev/null
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

This instrument reads project-specific paths from `project-profile.yaml` in the target project root. If a profile field is absent, the default from the profile schema applies. Instrument-specific thresholds remain in this instrument's `config.yaml`.

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
  access_control_config: config/access-control.yaml       # adjust to project layout
  component_manifest: config/component-permission-manifest.yaml
  boundary_tests: <service>/tests/
  compose_file: docker-compose.yml
  config_dir: config/
  business_docs: docs/
  source_dirs: []                                          # directories to scan for source files (phases 1, 4, 6)
```

---

## Output

Reports are written to `output/YYYY-MM-DD_{project_name}/CL{n}-compliance.md` (see `qualitoscope/config.yaml` for `project_name`).

---

## Run History

| Run | Date | Trigger | Report |
|-----|------|---------|--------|
| CL1 | _pending_ | Initial baseline | — |

## License

Part of [qual-gate](https://github.com/Nelvradia/qual-gate). Licensed under [Apache 2.0](../../LICENSE).
